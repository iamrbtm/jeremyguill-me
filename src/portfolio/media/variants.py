from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from flask import current_app
from PIL import Image, ImageOps

VARIANT_SPECS = {
    "hero_desktop": (1600, 900),
    "hero_mobile": (900, 1200),
    "profile": (640, 640),
    "open_graph": (1200, 630),
}
VARIANT_NAMES = frozenset(VARIANT_SPECS)


@dataclass(frozen=True)
class MediaVariant:
    name: str
    storage_key: str
    mime_type: str
    width: int
    height: int
    byte_size: int


def media_root() -> Path:
    return Path(current_app.config.get("MEDIA_ROOT", "var/media"))


def generate_variants(asset) -> list[MediaVariant]:
    root = media_root()
    tmp_dir = root / ".tmp" / f"variants-{uuid.uuid4()}"
    final_dir = root / "public" / str(asset.id)
    tmp_public_dir = tmp_dir / "public" / str(asset.id)
    try:
        with Image.open(root / asset.storage_key) as image:
            image = ImageOps.exif_transpose(image)
            image.load()
            variants = write_variants_for_image(image, asset.id, tmp_public_dir)
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        if final_dir.exists():
            _remove_tree(final_dir)
        os.replace(tmp_public_dir, final_dir)
        _fsync_directory(final_dir.parent)
        return variants
    finally:
        _remove_tree(tmp_dir)


def write_variants_for_image(image: Image.Image, asset_id, output_dir: Path) -> list[MediaVariant]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variants: list[MediaVariant] = []
    for name, (width, height) in VARIANT_SPECS.items():
        variant = _resize_crop(image, width, height)
        path = output_dir / f"{name}.webp"
        variant.save(path, format="WEBP", quality=86, method=6)
        _fsync_file(path)
        variants.append(
            MediaVariant(
                name=name,
                storage_key=f"public/{asset_id}/{name}.webp",
                mime_type="image/webp",
                width=width,
                height=height,
                byte_size=path.stat().st_size,
            )
        )
    _fsync_directory(output_dir)
    return variants


def _resize_crop(image: Image.Image, width: int, height: int) -> Image.Image:
    source = image.convert("RGB")
    source_ratio = source.width / source.height
    target_ratio = width / height
    if source_ratio > target_ratio:
        crop_width = round(source.height * target_ratio)
        left = max((source.width - crop_width) // 2, 0)
        box = (left, 0, left + crop_width, source.height)
    else:
        crop_height = round(source.width / target_ratio)
        top = max((source.height - crop_height) // 2, 0)
        box = (0, top, source.width, top + crop_height)
    return source.crop(box).resize((width, height), Image.Resampling.LANCZOS)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_dir():
            child.rmdir()
        else:
            child.unlink()
    path.rmdir()
