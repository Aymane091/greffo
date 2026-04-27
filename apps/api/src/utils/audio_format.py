_MIME_TO_FORMAT: dict[str, str] = {
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "audio/flac": "flac",
}

ALLOWED_MIMES: frozenset[str] = frozenset(_MIME_TO_FORMAT.keys())

# Manual magic-byte signatures as fallback when libmagic lacks audio entries (e.g. macOS).
_MAGIC_SIGNATURES: list[tuple[bytes, int, bytes, str]] = [
    # (prefix, wave_offset, wave_tag, mime)  — RIFF/WAV uses a two-part check
    (b"RIFF", 8, b"WAVE", "audio/x-wav"),
]
_SIMPLE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"ID3", "audio/mpeg"),
    (b"OggS", "audio/ogg"),
    (b"fLaC", "audio/flac"),
]


def detect_audio_mime(data: bytes) -> str:
    """Detect audio MIME from magic bytes.

    Uses python-magic as the primary detector. Falls back to manual byte
    inspection for platforms where libmagic lacks audio format entries
    (e.g. macOS system libmagic returns application/octet-stream for RIFF/WAV).
    """
    import magic as _magic

    detected = _magic.from_buffer(data[:4096], mime=True)
    if detected in ALLOWED_MIMES:
        return detected

    # MP3 sync word (0xFF 0xFB/F3/F2) — no fixed header, check separately
    if len(data) >= 2 and data[0] == 0xFF and data[1] in (0xFB, 0xF3, 0xF2, 0xFE):
        return "audio/mpeg"

    for prefix, offset, tag, mime in _MAGIC_SIGNATURES:
        if data[: len(prefix)] == prefix and data[offset : offset + len(tag)] == tag:
            return mime

    for prefix, mime in _SIMPLE_SIGNATURES:
        if data[: len(prefix)] == prefix:
            return mime

    # M4A: ftyp box at offset 4 with M4A brand
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in (
        b"m4a ",
        b"M4A ",
        b"mp42",
        b"isom",
        b"iso2",
    ):
        return "audio/mp4"

    return detected  # Return whatever libmagic gave us (may be application/octet-stream)


def mime_to_format(mime: str) -> str:
    fmt = _MIME_TO_FORMAT.get(mime)
    if fmt is None:
        raise ValueError(f"Unsupported MIME type: {mime}")
    return fmt
