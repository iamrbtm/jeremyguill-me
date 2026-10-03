from __future__ import annotations

import uuid
from io import BytesIO

from PIL import Image

from portfolio.auth.services import make_password_hash
from portfolio.content.models import Project, ProjectGalleryItem
from portfolio.extensions import db


def _png_bytes() -> bytes:
    image = Image.new("RGB", (10, 10), (200, 30, 30))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _login(client, app):
    with app.app_context():
        app.config["ADMIN_USERNAME"] = "admin"
        app.config["ADMIN_PASSWORD_HASH"] = make_password_hash("pw")
    response = client.post("/admin/login", data={"username": "admin", "password": "pw"})
    assert response.status_code == 302


def test_new_project_form_posts_to_create_route(client, app):
    _login(client, app)
    response = client.get("/admin/projects/new")
    assert response.status_code == 200
    assert b'action="/admin/projects"' in response.data
    assert b'action="/admin/projects/new"' not in response.data


def test_upload_hero_and_gallery_creates_associations(client, app):
    _login(client, app)

    response = client.post(
        "/admin/projects",
        data={
            "title": "Demo",
            "slug": "demo",
            "version": "0",
            "hero_image": (BytesIO(_png_bytes()), "hero.png"),
            "gallery_images": [
                (BytesIO(_png_bytes()), "g1.png"),
                (BytesIO(_png_bytes()), "g2.png"),
            ],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    with app.app_context():
        project = db.session.execute(
            db.select(Project).where(Project.slug == "demo")
        ).scalar_one()
        assert project.hero_media_id is not None
        gallery_count = db.session.execute(
            db.select(db.func.count())
            .select_from(ProjectGalleryItem)
            .where(ProjectGalleryItem.project_id == project.id)
        ).scalar()
        assert gallery_count == 2

    edit = client.get(response.headers["Location"])
    assert edit.status_code == 200
    assert b"/media/public/" in edit.data


def test_gallery_removal_updates_associations(client, app):
    _login(client, app)

    created = client.post(
        "/admin/projects",
        data={
            "title": "Demo",
            "slug": "demo",
            "version": "0",
            "gallery_images": [(BytesIO(_png_bytes()), "g1.png"), (BytesIO(_png_bytes()), "g2.png")],
        },
        content_type="multipart/form-data",
    )
    project_id = uuid.UUID(created.headers["Location"].rsplit("/", 1)[1])

    with app.app_context():
        project = db.session.get(Project, project_id)
        media_ids = [str(item.media_id) for item in project.gallery_items]

    client.post(
        f"/admin/projects/{project_id}",
        data={
            "title": "Demo",
            "slug": "demo",
            "version": str(project.version),
            "remove_gallery": media_ids[0],
        },
        content_type="multipart/form-data",
    )

    with app.app_context():
        remaining = db.session.execute(
            db.select(db.func.count())
            .select_from(ProjectGalleryItem)
            .where(ProjectGalleryItem.project_id == project_id)
        ).scalar()
        assert remaining == 1


def test_create_project_without_files(client, app):
    _login(client, app)
    response = client.post(
        "/admin/projects",
        data={"title": "Plain", "slug": "plain", "version": "0", "summary": "hi"},
        content_type="multipart/form-data",
    )
    print("STATUS", response.status_code)
    print(response.data.decode()[:2000])
    assert response.status_code == 302


def test_duplicate_slug_returns_form_error_not_500(client, app):
    _login(client, app)
    payload = {"title": "Dup", "slug": "dup", "version": "0", "summary": "x"}
    first = client.post("/admin/projects", data=payload, content_type="multipart/form-data")
    assert first.status_code == 302
    second = client.post("/admin/projects", data=payload, content_type="multipart/form-data")
    assert second.status_code == 409
    assert b"slug already exists" in second.data
