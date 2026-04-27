import asyncio
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
from src.storage import StorageBackend, init_storage

logger = logging.getLogger("greffo.worker")

# TODO(ticket-cleanup): Add a scheduled ARQ job that runs every hour to delete files
# from storage whose key is not referenced by any transcription.audio_s3_key.
# These are orphaned uploads where confirm-upload was never called after a successful PUT.

_STUB_SEGMENTS: list[tuple[float, float, str, str, float]] = [
    (0.0, 3.5, "SPEAKER_00", "Monsieur le Président, la séance est ouverte.", 0.92),
    (4.0, 7.2, "SPEAKER_01", "Maître, pouvez-vous présenter votre client ?", 0.89),
    (7.8, 12.1, "SPEAKER_00", "Bien entendu. Mon client, Monsieur Martin, est présent à l'audience.", 0.94),
    (12.5, 16.0, "SPEAKER_01", "Monsieur Martin, vous êtes bien prévenu des faits qui vous sont reprochés ?", 0.91),
    (16.8, 19.3, "SPEAKER_00", "Oui, Monsieur le Président. Je reconnais les faits.", 0.88),
    (20.0, 24.5, "SPEAKER_01", "Maître, quels sont les éléments à charge que vous souhaitez contester ?", 0.93),
    (25.0, 30.2, "SPEAKER_00", "Nous contestons la valeur probante du rapport d'expertise versé au dossier.", 0.87),
    (31.0, 35.8, "SPEAKER_01", "L'expert sera entendu à l'audience de renvoi. Avez-vous des observations ?", 0.90),
    (36.5, 41.0, "SPEAKER_00", "Nous demandons le renvoi de l'affaire pour permettre une contre-expertise.", 0.85),
    (42.0, 45.5, "SPEAKER_01", "La cour se retire pour délibérer. L'audience reprend dans trente minutes.", 0.96),
]


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

        # Sanity-check the audio file exists
        if tr.audio_s3_key and not await storage.exists(tr.audio_s3_key):
            raise FileNotFoundError(f"Audio file missing from storage: {tr.audio_s3_key}")

        # Idempotence: remove any segments from a previous (failed) run
        await db.execute(
            delete(TranscriptionSegment).where(
                TranscriptionSegment.transcription_id == tr.id
            )
        )

        for i, (start_s, end_s, speaker, text, confidence) in enumerate(_STUB_SEGMENTS):
            db.add(
                TranscriptionSegment(
                    transcription_id=tr.id,
                    organization_id=tr.organization_id,
                    segment_index=i,
                    speaker=speaker,
                    start_s=start_s,
                    end_s=end_s,
                    text=text,
                    confidence=confidence,
                )
            )

        tr.status = "done"
        tr.progress_pct = 100
        tr.processing_ended_at = datetime.now(timezone.utc)
        await db.commit()
        await log_action("DONE", "transcription", tr.id, tr.organization_id)

        logger.info(
            "Pipeline done: transcription=%s duration=%.1fs",
            tr.id,
            (tr.processing_ended_at - tr.processing_started_at).total_seconds(),
        )

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
    # Simulate processing time (replaced by real pipeline in ticket 11)
    await asyncio.sleep(5)
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
