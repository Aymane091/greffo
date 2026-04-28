import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from arq.connections import RedisSettings
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db import AsyncSessionLocal
from src.models.transcription import Transcription
from src.models.transcription_segment import TranscriptionSegment
from src.services.audit import log_action
from src.services.transcription import TranscriptionError, get_provider
from src.storage import StorageBackend, init_storage

logger = logging.getLogger("greffo.worker")

# TODO(ticket-cleanup): Add a scheduled ARQ job that runs every hour to delete files
# from storage whose key is not referenced by any transcription.audio_s3_key.
# These are orphaned uploads where confirm-upload was never called after a successful PUT.


async def _run_pipeline(
    db: AsyncSession, storage: StorageBackend, transcription_id: str
) -> None:
    """Pure pipeline logic — testable without ARQ or Redis."""
    result = await db.execute(
        select(Transcription).where(Transcription.id == transcription_id)
    )
    tr = result.scalar_one_or_none()
    if tr is None:
        logger.error("Transcription not found: %s", transcription_id)
        return

    try:
        tr.status = "processing"
        tr.processing_started_at = datetime.now(timezone.utc)
        await db.commit()
        await log_action("PROCESSING", "transcription", tr.id, tr.organization_id)

        if not tr.audio_s3_key:
            raise ValueError("No audio key — confirm-upload not called")
        if not await storage.exists(tr.audio_s3_key):
            raise FileNotFoundError(f"Audio file missing from storage: {tr.audio_s3_key}")

        audio_bytes = await storage.download(tr.audio_s3_key)
        provider = get_provider()
        result_data = await provider.transcribe(audio_bytes, tr.language or "fr")

        # DELETE + INSERT + status update in one atomic transaction
        async with db.begin():
            await db.execute(
                delete(TranscriptionSegment).where(
                    TranscriptionSegment.transcription_id == tr.id
                )
            )
            for i, seg in enumerate(result_data.segments):
                db.add(
                    TranscriptionSegment(
                        transcription_id=tr.id,
                        organization_id=tr.organization_id,
                        segment_index=i,
                        speaker=seg.speaker,
                        start_s=seg.start_s,
                        end_s=seg.end_s,
                        text=seg.text,
                        confidence=seg.confidence,
                    )
                )
            tr.status = "done"
            tr.progress_pct = 100
            tr.processing_ended_at = datetime.now(timezone.utc)
            tr.audio_duration_s = int(result_data.duration_s)
            tr.language = result_data.language_detected

        await log_action("DONE", "transcription", tr.id, tr.organization_id)
        logger.info(
            "Pipeline done: transcription=%s segments=%d duration=%.1fs",
            tr.id,
            len(result_data.segments),
            result_data.duration_s,
        )

    except TranscriptionError as exc:
        logger.error(
            "Transcription error for %s: error_code=%s", transcription_id, exc.error_code
        )
        try:
            tr.status = "failed"
            tr.error_code = exc.error_code
            tr.error_message = exc.message[:500]
            await db.commit()
            await log_action("FAILED", "transcription", tr.id, tr.organization_id)
        except Exception:
            logger.exception("Could not persist failure state for %s", transcription_id)

    except Exception as exc:
        logger.exception("Pipeline failed for transcription %s", transcription_id)
        try:
            tr.status = "failed"
            tr.error_code = type(exc).__name__
            tr.error_message = str(exc)[:500]
            await db.commit()
            await log_action("FAILED", "transcription", tr.id, tr.organization_id)
        except Exception:
            logger.exception("Could not persist failure state for %s", transcription_id)


async def process_transcription(ctx: dict, transcription_id: str) -> None:
    """ARQ job entry point. Opens its own DB session."""
    storage: StorageBackend = ctx.get("storage") or init_storage()
    async with AsyncSessionLocal() as db:
        await _run_pipeline(db, storage, transcription_id)


async def _on_startup(ctx: dict) -> None:
    ctx["storage"] = init_storage()


def _parse_redis_settings(url: str) -> RedisSettings:
    u = urlparse(url)
    return RedisSettings(
        host=u.hostname or "localhost",
        port=u.port or 6379,
        password=u.password,
        database=int(u.path.strip("/") or "0"),
    )


class WorkerSettings:
    on_startup = _on_startup
    functions = [process_transcription]
    redis_settings = _parse_redis_settings(settings.redis_url)
    max_jobs = 4
    job_timeout = 7200  # 2h max per file
    keep_result = 3600
