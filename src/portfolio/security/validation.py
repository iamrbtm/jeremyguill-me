from __future__ import annotations

from urllib.parse import urlsplit


def safe_redirect_target(value: str) -> str | None:
    if not value or any(ord(character) < 32 for character in value):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or value.startswith("//"):
        return None
    if not value.startswith("/"):
        return None
    return value
