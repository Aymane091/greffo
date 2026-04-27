import hashlib
import hmac
import time
from datetime import datetime, timezone

from src.config import settings

_TOKEN_TTL_SECONDS = 900  # 15 minutes


def generate_upload_token(transcription_id: str, org_id: str) -> tuple[str, datetime]:
    """Returns (token, expires_at). Token format: {tr_id}.{org_id}.{exp}.{hmac_hex}"""
    exp = int(time.time()) + _TOKEN_TTL_SECONDS
    message = f"{transcription_id}|{org_id}|{exp}"
    sig = hmac.new(
        settings.storage_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    token = f"{transcription_id}.{org_id}.{exp}.{sig}"
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    return token, expires_at


def verify_upload_token(token: str) -> tuple[str, str]:
    """Returns (transcription_id, org_id). Raises ValueError on invalid/expired token."""
    parts = token.split(".")
    if len(parts) != 4:
        raise ValueError("Invalid token format")

    transcription_id, org_id, exp_str, received_sig = parts

    message = f"{transcription_id}|{org_id}|{exp_str}"
    expected_sig = hmac.new(
        settings.storage_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, received_sig):
        raise ValueError("Invalid token signature")

    if int(exp_str) < int(time.time()):
        raise ValueError("Token expired")

    return transcription_id, org_id
