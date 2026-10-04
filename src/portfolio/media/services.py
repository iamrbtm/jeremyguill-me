from __future__ import annotations

import io
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy import select

from portfolio.audit.services import record_event
from portfolio.content.models import Project
from portfolio.extensions import db

from .models import MediaAsset
from .validation import ValidatedUpload, validate_upload
from .variants import (
    _fsync_directory,
    _fsync_file,
    _remove_tree,
    media_root,
    write_variants_for_image,
)


class MediaInUse(ValueError):
    pass


class MediaNotFound(LookupError):
    pass


@dataclass(frozen=True)
class MediaMetadata:
    alt_text: str
    caption: str = ""
    private: bool = True


def store_image(upload: ValidatedUpload, metadata: MediaMetadata) -> MediaAsset:
    root = media_root()
    asset_id = uuid.uuid4()
    original_key = f"private/originals/{asset_id}{upload.extension}"
    tmp_dir = root / ".tmp" / str(asset_id)
    final_original = root / original_key
    final_variant_dir = root / "public" / str(asset_id)
    final_paths: list[Path] = []

    try:
        root.mkdir(parents=True, exist_ok=True)
        with Image.open(io.BytesIO(upload.payload)) as image:
            image = ImageOps.exif_transpose(image)
            image.load()
            tmp_original = tmp_dir / original_key
            tmp_original.parent.mkdir(parents=True, exist_ok=True)
            _save_original(image, tmp_original, upload.mime_type)
            write_variants_for_image(image, asset_id, tmp_dir / "public" / str(asset_id))

        final_original.parent.mkdir(parents=True, exist_ok=True)
        final_variant_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_dir / original_key, final_original)
        final_paths.append(final_original)
        os.replace(tmp_dir / "public" / str(asset_id), final_variant_dir)
        final_paths.append(final_variant_dir)
        _fsync_directory(final_original.parent)
        _fsync_directory(final_variant_dir.parent)

        asset = MediaAsset(
            id=asset_id,
            original_filename=upload.filename,
            storage_key=original_key,
            mime_type=upload.mime_type,
            byte_size=final_original.stat().st_size,
            alt_text=metadata.alt_text.strip(),
            caption=metadata.caption.strip(),
            private=metadata.private,
        )
        db.session.add(asset)
        record_event(
            action="media.created",
            actor="admin",
            target_type="media_asset",
            target_id=str(asset.id),
            metadata={"mime_type": asset.mime_type, "byte_size": asset.byte_size},
        )
        db.session.commit()
        return asset
    except Exception:
        db.session.rollback()
        for path in final_paths:
            if path.is_dir():
                _remove_tree(path)
            elif path.exists():
                path.unlink()
        _remove_tree(tmp_dir)
        raise
    finally:
        _remove_tree(tmp_dir)
        _remove_empty_directory(root / ".tmp")


def store_upload_file(
    stream,
    filename: str,
    mime_type: str,
    *,
    alt_text: str = "",
    caption: str = "",
    private: bool = True,
) -> MediaAsset:
    validated = validate_upload(stream, filename, mime_type)
    return store_image(
        validated, MediaMetadata(alt_text=alt_text, caption=caption, private=private)
    )


def delete_media(asset_id) -> None:
    asset = db.session.get(MediaAsset, asset_id)
    if asset is None:
        raise MediaNotFound("Media asset not found")

    in_use = db.session.execute(
        select(Project.id).where(Project.hero_media_id == asset.id).limit(1)
    ).first()
    if in_use is not None:
        raise MediaInUse("Media asset is referenced by published content")

    from portfolio.content.models import Experience, ProjectGalleryItem

    gallery_use = db.session.execute(
        select(ProjectGalleryItem.project_id)
        .where(ProjectGalleryItem.media_id == asset.id)
        .limit(1)
    ).first()
    if gallery_use is not None:
        raise MediaInUse("Media asset is used in a project gallery")

    experience_use = db.session.execute(
        select(Experience.id).where(Experience.logo_media_id == asset.id).limit(1)
    ).first()
    if experience_use is not None:
        raise MediaInUse("Media asset is used as an experience logo")

    root = media_root()
    original_path = root / asset.storage_key
    variant_dir = root / "public" / str(asset.id)
    if original_path.exists():
        original_path.unlink()
    _remove_tree(variant_dir)
    db.session.delete(asset)
    record_event(
        action="media.deleted",
        actor="admin",
        target_type="media_asset",
        target_id=str(asset.id),
    )
    db.session.commit()


def list_media() -> list[MediaAsset]:
    result = db.session.execute(select(MediaAsset).order_by(MediaAsset.created_at.desc()))
    return list(result.scalars())


def _save_original(image: Image.Image, path: Path, mime_type: str) -> None:
    if mime_type == "image/png":
        if image.mode == "RGBA":
            image.save(path, format="PNG", optimize=True)
        else:
            image.convert("RGB").save(path, format="PNG", optimize=True)
    elif mime_type == "image/webp":
        if image.mode == "RGBA":
            image.save(path, format="WEBP", quality=92, method=6)
        else:
            image.convert("RGB").save(path, format="WEBP", quality=92, method=6)
    else:
        image.convert("RGB").save(path, format="JPEG", quality=92, optimize=True)
    _fsync_file(path)


def _remove_empty_directory(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass
