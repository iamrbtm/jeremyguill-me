from __future__ import annotations

import io

import pytest
from PIL import Image

from portfolio.media.validation import InvalidUpload, validate_upload


def image_bytes(format_: str = "JPEG", size: tuple[int, int] = (32, 32)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(35, 38, 42)).save(buffer, format=format_)
    return buffer.getvalue()


@pytest.mark.parametrize("filename", ["shell.php", "vector.svg", "page.html"])
def test_executable_or_active_formats_are_rejected(filename: str):
    with pytest.raises(InvalidUpload, match="Unsupported image type"):
        validate_upload(io.BytesIO(image_bytes()), filename, "application/octet-stream")


def test_declared_type_must_match_detected_signature():
    with pytest.raises(InvalidUpload, match="does not match"):
        validate_upload(io.BytesIO(image_bytes("JPEG")), "portrait.jpg", "image/png")


def test_oversized_upload_is_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("portfolio.media.validation.MAX_UPLOAD_BYTES", 8)

    with pytest.raises(InvalidUpload, match="15 MB"):
        validate_upload(io.BytesIO(image_bytes()), "portrait.jpg", "image/jpeg")


def test_decompression_limits_are_enforced(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("portfolio.media.validation.MAX_IMAGE_PIXELS", 10)

    with pytest.raises(InvalidUpload, match="too large"):
        validate_upload(io.BytesIO(image_bytes(size=(8, 8))), "portrait.jpg", "image/jpeg")


def test_valid_image_returns_normalized_upload_metadata():
    upload = validate_upload(io.BytesIO(image_bytes("PNG", (40, 24))), "portrait.png", "image/png")

    assert upload.mime_type == "image/png"
    assert upload.extension == ".png"
    assert upload.width == 40
    assert upload.height == 24
    assert upload.payload
