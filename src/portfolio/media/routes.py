from __future__ import annotations

import uuid

from flask import Blueprint, abort, redirect, render_template, request, url_for

from portfolio.auth.decorators import passkey_required
from portfolio.extensions import db

from .models import MediaAsset
from .services import MediaInUse, delete_media, list_media, store_upload_file
from .validation import InvalidUpload

media_bp = Blueprint("media", __name__, url_prefix="/admin/media")


@media_bp.get("")
@passkey_required
def index():
    return render_template("admin/media/index.html", assets=list_media())


@media_bp.post("/upload")
@passkey_required
def upload():
    upload_file = request.files.get("file")
    if upload_file is None or not upload_file.filename:
        return (
            render_template(
                "admin/media/index.html", assets=list_media(), error="Select an image to upload."
            ),
            400,
        )
    try:
        store_upload_file(
            upload_file.stream,
            upload_file.filename,
            upload_file.mimetype,
            alt_text=request.form.get("alt_text", "").strip(),
            caption=request.form.get("caption", "").strip(),
            private=request.form.get("private", "on") == "on",
        )
    except InvalidUpload as exc:
        return render_template("admin/media/index.html", assets=list_media(), error=str(exc)), 400
    return redirect(url_for("media.index"))


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


@media_bp.post("/<asset_id>/delete")
@passkey_required
def delete(asset_id: str):
    try:
        media_id = uuid.UUID(asset_id)
    except ValueError:
        abort(404)
    try:
        delete_media(media_id)
    except MediaInUse as exc:
        return (
            render_template(
                "admin/media/edit.html",
                asset=db.session.get(MediaAsset, media_id),
                error=str(exc),
            ),
            409,
        )
    return redirect(url_for("media.index"))
