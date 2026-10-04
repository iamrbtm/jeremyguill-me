from __future__ import annotations

import hashlib
from pathlib import Path

from flask import Flask, Response, current_app, request, url_for

_cache: dict[tuple[str, float], str] = {}


def _digest(path: Path) -> str | None:
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None
    key = (str(path), stamp)
    if key not in _cache:
        _cache[key] = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
    return _cache[key]


def static_url(filename: str) -> str:
    digest = _digest(Path(current_app.static_folder or "") / filename)
    if digest is None:
        return url_for("static", filename=filename)
    return url_for("static", filename=filename, v=digest)


def apply_cache_headers(response: Response) -> Response:
    if request.endpoint == "static" and response.status_code in (200, 304):
        if request.args.get("v"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "public, max-age=3600"
    return response


def init_assets(app: Flask) -> None:
    app.jinja_env.globals["static_url"] = static_url
    app.after_request(apply_cache_headers)
