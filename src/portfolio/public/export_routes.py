from __future__ import annotations

from flask import Blueprint, Response, jsonify

from .site_export import build_site_export

export_bp = Blueprint("export", __name__)


@export_bp.get("/api/site-content.json")
def site_content() -> Response:
    response = jsonify(build_site_export())
    response.headers["Cache-Control"] = "public, max-age=300"
    return response
