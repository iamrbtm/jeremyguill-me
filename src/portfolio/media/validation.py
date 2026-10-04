from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import PurePath
from typing import BinaryIO

import filetype
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000


class InvalidUpload(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedUpload:
    payload: bytes
    filename: str
    mime_type: str
    extension: str
    width: int
    height: int


def validate_upload(stream: BinaryIO, filename: str, declared_type: str) -> ValidatedUpload:
    suffix = PurePath(filename).suffix.lower()
    declared_type = declared_type.split(";", 1)[0].strip().lower()
    if suffix not in ALLOWED_IMAGE_TYPES.values() or declared_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidUpload("Unsupported image type")

    payload = stream.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise InvalidUpload("File exceeds 15 MB")

    detected = filetype.guess_mime(payload)
    if detected not in ALLOWED_IMAGE_TYPES:
        raise InvalidUpload("Unsupported image type")
    if detected != declared_type:
        raise InvalidUpload("Declared type does not match image signature")

    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.verify()
        with Image.open(io.BytesIO(payload)) as image:
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                raise InvalidUpload("Image dimensions are too large")
            image.load()
    except InvalidUpload:
        raise
    except (OSError, UnidentifiedImageError) as exc:
        raise InvalidUpload("Invalid image payload") from exc

    return ValidatedUpload(
        payload=payload,
        filename=PurePath(filename).name[:240],
        mime_type=detected,
        extension=ALLOWED_IMAGE_TYPES[detected],
        width=width,
        height=height,
    )
