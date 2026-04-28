import asyncio
import logging
import time
from typing import Any

import httpx

from src.services.transcription import (
    TranscriptionError,
    TranscriptionProvider,
    TranscriptionResult,
    TranscriptionSegmentResult,
)
from src.utils.audio_format import detect_audio_mime

logger = logging.getLogger("greffo.gladia")

_RETRY_DELAYS = (1.0, 4.0, 16.0)  # delays before attempts 2, 3, 4
_POLL_INTERVAL_START = 5.0
_POLL_INTERVAL_MAX = 30.0
_SHORT_AUDIO_THRESHOLD_S = 1800.0   # 30 min
_SHORT_AUDIO_TIMEOUT_S = 600.0      # 10 min polling timeout for < 30 min audio


def _normalize_speaker(raw: str | None, mapping: dict[str, str]) -> str:
    """Map arbitrary Gladia speaker IDs to zero-padded SPEAKER_NN labels."""
    if raw is None:
        return "SPEAKER_00"
    if raw not in mapping:
        idx = len(mapping)
        mapping[raw] = f"SPEAKER_{idx:02d}"
    return mapping[raw]


class GladiaProvider(TranscriptionProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.gladia.io",
        timeout_s: int = 1800,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    def _auth_headers(self) -> dict[str, str]:
        return {"x-gladia-key": self._api_key, "accept": "application/json"}

    async def _with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send an HTTP request with up to 3 retries (exponential 1/4/16s) on 429/5xx/network."""
        last_err: TranscriptionError | Exception | None = None

        for attempt in range(4):  # 1 initial + 3 retries
            if attempt > 0:
                delay = _RETRY_DELAYS[attempt - 1]
                logger.info("Gladia retry %d/%d — waiting %.0fs", attempt, 3, delay)
                await asyncio.sleep(delay)

            try:
                resp = await client.request(method, url, **kwargs)
            except httpx.NetworkError as exc:
                last_err = exc
                logger.warning("Gladia network error (attempt %d): %s", attempt + 1, exc)
                continue

            if resp.status_code in (401, 403):
                raise TranscriptionError(
                    "AUTH_ERROR",
                    f"Gladia authentication failed (HTTP {resp.status_code})",
                )

            if resp.status_code == 429:
                logger.warning("Gladia rate limit (attempt %d)", attempt + 1)
                last_err = TranscriptionError("RATE_LIMIT", "Rate limited by Gladia")
                continue

            if resp.status_code >= 500:
                logger.warning("Gladia 5xx (attempt %d): %d", attempt + 1, resp.status_code)
                last_err = TranscriptionError(
                    "UPSTREAM_ERROR", f"Gladia server error: {resp.status_code}"
                )
                continue

            return resp

        if isinstance(last_err, TranscriptionError):
            raise last_err
        raise TranscriptionError("NETWORK_ERROR", f"Max retries exceeded: {last_err}")

    async def _upload(self, client: httpx.AsyncClient, audio_bytes: bytes) -> tuple[str, float]:
        """Upload audio to Gladia. Returns (audio_url, duration_s)."""
        mime = detect_audio_mime(audio_bytes)
        resp = await self._with_retry(
            client,
            "POST",
            f"{self._base_url}/v2/upload",
            headers=self._auth_headers(),
            files={"audio": ("audio", audio_bytes, mime)},
        )
        data = resp.json()
        audio_url: str = data["audio_url"]
        duration_s = float(data.get("audio_metadata", {}).get("audio_duration") or 0)
        logger.info("Gladia upload done: duration=%.1fs", duration_s)
        return audio_url, duration_s

    async def _start_job(
        self, client: httpx.AsyncClient, audio_url: str, language: str
    ) -> str:
        """Submit transcription job. Returns job_id."""
        resp = await self._with_retry(
            client,
            "POST",
            f"{self._base_url}/v2/pre-recorded",
            headers={**self._auth_headers(), "content-type": "application/json"},
            json={
                "audio_url": audio_url,
                "diarization": True,
                "language_config": {"language": language},
            },
        )
        job_id: str = resp.json()["id"]
        logger.info("Gladia job started: id=%s", job_id)
        return job_id

    async def _poll(
        self, client: httpx.AsyncClient, job_id: str, timeout_s: float
    ) -> dict[str, Any]:
        """Poll until done or timeout. Returns the raw Gladia result dict."""
        deadline = time.monotonic() + timeout_s
        interval = _POLL_INTERVAL_START
        poll_count = 0

        while True:
            resp = await self._with_retry(
                client,
                "GET",
                f"{self._base_url}/v2/pre-recorded/{job_id}",
                headers=self._auth_headers(),
            )
            data: dict[str, Any] = resp.json()
            status = data.get("status")
            poll_count += 1

            logger.info("Gladia poll #%d: job=%s status=%s", poll_count, job_id, status)

            if status == "done":
                tr = data.get("result", {}).get("transcription", {})
                logger.debug(
                    "Gladia done raw shape: file=%s utterances=%d languages=%s",
                    data.get("file", {}),
                    len(tr.get("utterances", [])),
                    tr.get("languages", []),
                )
                return data

            if status == "error":
                raise TranscriptionError(
                    "AUDIO_INVALID",
                    f"Gladia processing error: {data.get('error_code', 'unknown')}",
                )

            # queued or processing — check deadline before sleeping
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TranscriptionError(
                    "TIMEOUT",
                    f"Gladia polling timed out after {timeout_s:.0f}s (job={job_id})",
                )

            await asyncio.sleep(min(interval, remaining))
            interval = min(interval * 1.5, _POLL_INTERVAL_MAX)

    def _map_result(self, raw: dict[str, Any], upload_duration_s: float) -> TranscriptionResult:
        """Map Gladia v2 response → TranscriptionResult."""
        transcription = raw.get("result", {}).get("transcription", {})
        utterances: list[dict[str, Any]] = transcription.get("utterances", [])
        languages: list[str] = transcription.get("languages", [])

        language_detected = languages[0] if languages else "fr"
        # Prefer file.duration from polling response; fall back to upload metadata
        duration_s = float(raw.get("file", {}).get("duration") or upload_duration_s)

        speaker_map: dict[str, str] = {}
        segments = [
            TranscriptionSegmentResult(
                start_s=float(u["start"]),
                end_s=float(u["end"]),
                speaker=_normalize_speaker(u.get("speaker"), speaker_map),
                text=u.get("text", ""),
                confidence=float(u.get("confidence", 0.0)),
            )
            for u in utterances
        ]

        return TranscriptionResult(
            segments=segments,
            language_detected=language_detected,
            duration_s=duration_s,
        )

    async def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        async with httpx.AsyncClient(timeout=60.0) as client:
            audio_url, upload_duration_s = await self._upload(client, audio_bytes)

            # Adaptive polling timeout: 10 min for < 30 min audio, settings value otherwise
            if 0 < upload_duration_s < _SHORT_AUDIO_THRESHOLD_S:
                timeout_s = _SHORT_AUDIO_TIMEOUT_S
            else:
                timeout_s = float(self._timeout_s)

            job_id = await self._start_job(client, audio_url, language)
            raw = await self._poll(client, job_id, timeout_s)
            return self._map_result(raw, upload_duration_s)
