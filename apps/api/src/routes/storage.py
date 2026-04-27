import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models.transcription import Transcription
from src.services.storage_token import verify_upload_token
from src.storage import StorageBackend, get_storage
from src.utils.audio_format import ALLOWED_MIMES, detect_audio_mime, mime_to_format

logger = logging.getLogger("greffo.storage")

router = APIRouter(prefix="/storage", tags=["storage"])

_MAX_SIZE = 500 * 1024 * 1024  # 500 MB


@router.put("/upload/{token}", status_code=status.HTTP_200_OK)
async def upload_audio(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> dict:
    # --- Verify HMAC token ---
    try:
        transcription_id, org_id = verify_upload_token(token)
    except ValueError as exc:
        detail = "upload_url_expired" if "expired" in str(exc) else "invalid_token"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

    # --- Load transcription (tenant-scoped) ---
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.organization_id == org_id,
            Transcription.deleted_at.is_(None),
        )
    )
    tr = result.scalar_one_or_none()
    if tr is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found"
        )

    # Idempotence guard — already uploaded
    if tr.audio_s3_key is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="audio_already_uploaded"
        )

    # --- Pre-flight size check via Content-Length ---
    content_length_hdr = request.headers.get("content-length")
    if content_length_hdr is not None and int(content_length_hdr) > _MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="file_too_large"
        )

    # --- Stream body with running size counter ---
    # Note: we buffer in memory (suitable for dev/staging). Production should stream to
    # a temp file then move to object storage to avoid RAM pressure at 500 MB.
    body = b""
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > _MAX_SIZE:
            # No partial file to clean up since we haven't written to storage yet.
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="file_too_large",
            )
        body += chunk

    # --- MIME detection from magic bytes ---
    detected_mime = detect_audio_mime(body)
    claimed_mime = request.headers.get("content-type", "").split(";")[0].strip()

    if detected_mime not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported_audio_format:{detected_mime}",
        )

    if detected_mime != claimed_mime:
        logger.warning(
            "MIME mismatch for transcription %s — claimed=%s detected=%s (accepting detected)",
            transcription_id,
            claimed_mime,
            detected_mime,
        )

    audio_format = mime_to_format(detected_mime)
    storage_key = f"audio/{transcription_id}"

    await storage.upload(storage_key, body, detected_mime)

    # --- Persist audio metadata ---
    tr.audio_s3_key = storage_key
    tr.audio_size_bytes = total_bytes
    tr.audio_format = audio_format
    await db.commit()

    logger.info(
        "Audio uploaded: transcription=%s format=%s size_bytes=%d",
        transcription_id,
        audio_format,
        total_bytes,
    )

    return {"status": "ok", "key": storage_key, "format": audio_format, "size_bytes": total_bytes}
