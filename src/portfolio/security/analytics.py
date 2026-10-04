from __future__ import annotations

from urllib.parse import urlparse


def analytics_origin(url: object, site_id: object) -> str | None:
    """Return the CSP origin for the analytics script, or None when it must not load."""
    if not str(site_id or "").strip():
        return None
    try:
        parsed = urlparse(str(url or "").strip())
        host, port = parsed.hostname, parsed.port
    except ValueError:
        return None
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return None
    if ":" in host:
        host = f"[{host}]"
    return f"https://{host}" + (f":{port}" if port else "")
