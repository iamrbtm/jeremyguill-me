from __future__ import annotations

from datetime import timedelta

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project, Redirect, utcnow
from portfolio.content.schemas import ContentCommand
from portfolio.content.services import change_slug, publish, save_draft
from portfolio.jobs.models import Job


def test_publish_creates_revision_and_sets_timestamp(db_session):
    project = Project(
        title="Project",
        slug="project",
        summary="Summary",
        source_markdown="## Body",
        state=PublicationState.DRAFT,
    )
    db_session.add(project)
    db_session.commit()

    published = publish(project)

    assert published.state is PublicationState.PUBLISHED
    assert published.published_at is not None
    assert published.revisions[-1].source_markdown == project.source_markdown
    assert published.revisions[-1].reason == "publish"


def test_scheduled_publish_creates_single_job(db_session):
    project = Project(
        title="Project", slug="project", summary="Summary", state=PublicationState.DRAFT
    )
    db_session.add(project)
    db_session.commit()

    run_at = utcnow() + timedelta(days=1)
    publish(project, when=run_at)
    publish(project, when=run_at)

    assert project.state is PublicationState.SCHEDULED
    assert db_session.query(Job).filter_by(kind="publish", entity_id=project.id).count() == 1


def test_save_draft_updates_rendered_html_and_version(db_session):
    project = Project(title="Old", slug="old", summary="Old", state=PublicationState.DRAFT)
    db_session.add(project)
    db_session.commit()

    save_draft(
        project,
        ContentCommand(title="New", summary="New summary", source_markdown="**Safe**"),
        expected_version=1,
    )

    assert project.title == "New"
    assert "<strong>Safe</strong>" in project.rendered_html
    assert project.version == 2
    assert project.revisions[-1].reason == "draft-save"


def test_change_slug_creates_redirect(db_session):
    project = Project(title="Project", slug="old", summary="Summary", state=PublicationState.DRAFT)
    db_session.add(project)
    db_session.commit()

    redirect = change_slug(project, "new")

    assert project.slug == "new"
    assert redirect is not None
    assert redirect.old_path == "/work/old"
    assert redirect.new_path == "/work/new"
    assert db_session.query(Redirect).one().old_path == "/work/old"
