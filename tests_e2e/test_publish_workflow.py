from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.content.schemas import ContentCommand
from portfolio.content.services import publish, save_draft
from portfolio.extensions import db


def test_draft_save_publish_and_public_project_flow(client, app):
    with app.app_context():
        project = Project(
            title="Draft",
            slug="draft",
            summary="Draft",
            state=PublicationState.DRAFT,
        )
        db.session.add(project)
        db.session.commit()
        save_draft(
            project,
            ContentCommand(
                title="A practical system",
                slug="practical-system",
                summary="Workflow software",
                source_markdown="rough notes",
            ),
            expected_version=project.version,
        )
        publish(project)

    response = client.get("/work/practical-system")

    assert response.status_code == 200
    assert b"A practical system" in response.data
    assert b"rough notes" in response.data


def test_admin_project_preview_is_noindexed(client, app):
    with app.app_context():
        project = Project(
            title="Preview",
            slug="preview",
            summary="Preview summary",
            source_markdown="Body",
            rendered_html="<p>Body</p>",
            state=PublicationState.DRAFT,
        )
        db.session.add(project)
        db.session.commit()
        project_id = project.id
    with client.session_transaction() as session:
        session["admin_session_id"] = "acceptance-admin"

    redirect = client.get(f"/admin/projects/{project_id}/preview")
    preview = client.get(redirect.headers["Location"])

    assert preview.status_code == 200
    assert preview.headers["X-Robots-Tag"] == "noindex, nofollow"
