from __future__ import annotations

import uuid

from flask import Blueprint, abort, redirect, render_template, request, url_for

from portfolio.auth.decorators import passkey_required
from portfolio.extensions import db

from .models import MediaAsset

media_bp = Blueprint("media", __name__, url_prefix="/admin/media")


@media_bp.get("")
@passkey_required
def index():
    from .services import list_media

    return render_template("admin/media/index.html", assets=list_media())


@media_bp.get("/<asset_id>/edit")
@passkey_required
def edit(asset_id: str):
    try:
        media_id = uuid.UUID(asset_id)
    except ValueError:
        abort(404)
    asset = db.session.get(MediaAsset, media_id)
    if asset is None:
        abort(404)
    return render_template("admin/media/edit.html", asset=asset)


@media_bp.post("/<asset_id>/edit")
@passkey_required
def update(asset_id: str):
    try:
        media_id = uuid.UUID(asset_id)
    except ValueError:
        abort(404)
    asset = db.session.get(MediaAsset, media_id)
    if asset is None:
        abort(404)
    asset.alt_text = request.form.get("alt_text", "").strip()
    asset.caption = request.form.get("caption", "").strip()
    asset.version += 1
    db.session.commit()
    return redirect(url_for("media.edit", asset_id=asset.id))
