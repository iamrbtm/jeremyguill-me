from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.extensions import db
from portfolio.media.models import MediaAsset
from portfolio.media.services import MediaInUse, MediaMetadata, delete_media, store_image
from portfolio.media.validation import validate_upload
from portfolio.media.variants import VARIANT_NAMES, generate_variants


def image_bytes(size: tuple[int, int] = (1800, 1400)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(25, 27, 31)).save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


@pytest.fixture()
def media_root(app, tmp_path: Path) -> Path:
    app.config["MEDIA_ROOT"] = str(tmp_path)
    return tmp_path


def valid_upload():
    return validate_upload(io.BytesIO(image_bytes()), "portrait.jpg", "image/jpeg")


def test_store_image_generates_private_original_and_required_variants(db_session, media_root: Path):
    asset = store_image(
        valid_upload(),
        MediaMetadata(alt_text="Jeremy Guill portrait", caption="Studio portrait"),
    )

    assert asset.id is not None
    assert asset.private is True
    assert (media_root / asset.storage_key).exists()
    assert asset.alt_text == "Jeremy Guill portrait"

    variants = generate_variants(asset)
    assert {variant.name for variant in variants} == VARIANT_NAMES
    assert all((media_root / variant.storage_key).exists() for variant in variants)
    assert all(variant.mime_type == "image/webp" for variant in variants)


def test_atomic_failure_cleans_up_pending_media_files(
    app, db_session, media_root: Path, monkeypatch: pytest.MonkeyPatch
):
    def fail_variant_generation(*args, **kwargs):
        raise RuntimeError("variant failure")

    monkeypatch.setattr(
        "portfolio.media.services.write_variants_for_image", fail_variant_generation
    )

    with pytest.raises(RuntimeError, match="variant failure"):
        store_image(valid_upload(), MediaMetadata(alt_text="broken"))

    assert list(media_root.rglob("*")) == []
    assert db_session.execute(select(MediaAsset)).scalars().all() == []


def test_referenced_media_cannot_be_deleted(db_session, media_root: Path):
    asset = store_image(valid_upload(), MediaMetadata(alt_text="Project hero"))
    project = Project(
        title="Referenced Project",
        slug="referenced-project",
        summary="Summary",
        source_markdown="Body",
        rendered_html="<p>Body</p>",
        state=PublicationState.PUBLISHED,
        hero_media_id=asset.id,
    )
    db.session.add(project)
    db.session.commit()

    with pytest.raises(MediaInUse):
        delete_media(asset.id)

    assert db.session.get(MediaAsset, asset.id) is not None
    assert (media_root / asset.storage_key).exists()


def test_unreferenced_media_delete_removes_database_row_and_files(db_session, media_root: Path):
    asset = store_image(valid_upload(), MediaMetadata(alt_text="Unused"))

    delete_media(asset.id)

    assert db.session.get(MediaAsset, asset.id) is None
    assert not (media_root / asset.storage_key).exists()
    assert not (media_root / "public" / str(asset.id)).exists()
