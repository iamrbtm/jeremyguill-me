from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from portfolio.admin.view_models import create_preview_token
from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.extensions import db


@pytest.fixture()
def authenticated_client(client):
    with client.session_transaction() as session:
        session["admin_session_id"] = "session-one"
    return client


@pytest.fixture()
def draft_project(db_session):
    project = Project(
        title="Draft Preview",
        slug="draft-preview",
        summary="Private summary",
        source_markdown="# Draft body",
        rendered_html="<h1>Draft body</h1>",
        state=PublicationState.DRAFT,
    )
    db.session.add(project)
    db.session.commit()
    return project


def test_signed_preview_renders_unpublished_project_for_active_session(
    authenticated_client, draft_project
):
    response = authenticated_client.get(f"/admin/projects/{draft_project.id}/preview")

    assert response.status_code == 302
    preview = authenticated_client.get(response.headers["Location"])
    assert preview.status_code == 200
    assert b"Draft Preview" in preview.data
    assert preview.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_signed_preview_rejects_different_admin_session(
    app, authenticated_client, draft_project
):
    token = create_preview_token(draft_project, "session-one")
    with authenticated_client.session_transaction() as session:
        session["admin_session_id"] = "session-two"

    response = authenticated_client.get(f"/admin/preview/{token}")

    assert response.status_code == 403


def test_signed_preview_expires(authenticated_client, draft_project):
    token = create_preview_token(
        draft_project,
        "session-one",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    response = authenticated_client.get(f"/admin/preview/{token}")

    assert response.status_code == 410


def test_signed_preview_rejects_version_mismatch(authenticated_client, db_session, draft_project):
    token = create_preview_token(draft_project, "session-one")
    draft_project.version += 1
    db.session.commit()

    response = authenticated_client.get(f"/admin/preview/{token}")

    assert response.status_code == 409


def test_preview_requires_authenticated_session(client, draft_project):
    token = create_preview_token(draft_project, str(uuid.uuid4()))

    response = client.get(f"/admin/preview/{token}")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/sign-in")
