from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from portfolio.audit.models import AuditEvent
from portfolio.content.enums import PublicationState
from portfolio.content.models import ContentRevision, Project
from portfolio.extensions import db


@pytest.fixture()
def authenticated_client(client):
    with client.session_transaction() as session:
        session["admin_session_id"] = str(uuid.uuid4())
    return client


@pytest.fixture()
def project(db_session):
    project = Project(
        title="Original",
        slug="original",
        summary="Original summary",
        source_markdown="Original body",
        rendered_html="<p>Original body</p>",
        state=PublicationState.DRAFT,
    )
    db.session.add(project)
    db.session.commit()
    return project


def project_form(project: Project, **overrides):
    data = {
        "title": project.title,
        "slug": project.slug,
        "summary": project.summary,
        "source_markdown": project.source_markdown,
        "version": str(project.version),
    }
    data.update(overrides)
    return data


def test_admin_requires_passkey_session(client):
    response = client.get("/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/sign-in")


def test_edit_project_creates_revision_and_audit_event(authenticated_client, db_session, project):
    response = authenticated_client.post(
        f"/admin/projects/{project.id}",
        data=project_form(project, title="Revised", source_markdown="**Body**"),
    )

    assert response.status_code == 302
    db.session.refresh(project)
    assert project.title == "Revised"
    assert project.version == 2
    revision = db.session.execute(select(ContentRevision)).scalar_one()
    assert revision.reason == "draft-save"
    assert revision.source_markdown == "**Body**"
    event = db.session.execute(
        select(AuditEvent).where(AuditEvent.action == "content.draft.saved")
    ).scalar_one()
    assert event.target_id == str(project.id)


def test_project_edit_rejects_concurrent_update(authenticated_client, db_session, project):
    project.version = 3
    db.session.commit()

    response = authenticated_client.post(
        f"/admin/projects/{project.id}",
        data=project_form(project, title="Stale edit", version="2"),
    )

    assert response.status_code == 409
    assert b"Content changed while you were editing" in response.data
    db.session.refresh(project)
    assert project.title == "Original"


def test_project_edit_validates_explicit_fields(authenticated_client, project):
    response = authenticated_client.post(
        f"/admin/projects/{project.id}",
        data=project_form(project, title="", slug=""),
    )

    assert response.status_code == 422
    assert b"Title is required" in response.data
    assert b"Slug is required" in response.data


def test_project_archive_restore_and_sorting(authenticated_client, db_session, project):
    second = Project(
        title="Second",
        slug="second",
        summary="Summary",
        source_markdown="Body",
        rendered_html="<p>Body</p>",
        state=PublicationState.DRAFT,
        sort_position=1,
    )
    db.session.add(second)
    db.session.commit()

    archive = authenticated_client.post(f"/admin/projects/{project.id}/archive")
    restore = authenticated_client.post(f"/admin/projects/{project.id}/restore")
    sort = authenticated_client.post(
        "/admin/projects/sort",
        data={"project_id": str(second.id), "sort_position": "0"},
    )

    assert archive.status_code == 302
    assert restore.status_code == 302
    assert sort.status_code == 302
    db.session.refresh(project)
    db.session.refresh(second)
    assert project.state == PublicationState.DRAFT
    assert second.sort_position == 0


def test_admin_project_list_is_ordered(authenticated_client, db_session):
    later = Project(
        title="Later", slug="later", summary="", state=PublicationState.DRAFT, sort_position=2
    )
    first = Project(
        title="First", slug="first", summary="", state=PublicationState.DRAFT, sort_position=1
    )
    db.session.add_all([later, first])
    db.session.commit()

    response = authenticated_client.get("/admin/projects")

    assert response.status_code == 200
    assert response.data.index(b"First") < response.data.index(b"Later")
