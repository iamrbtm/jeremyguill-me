from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from portfolio.audit.services import record_event
from portfolio.content.editor_contract import validate_editor_source
from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, Redirect, utcnow
from portfolio.content.rendering import render_markdown
from portfolio.content.revisions import create_revision, entity_type_for
from portfolio.content.schemas import ContentCommand
from portfolio.extensions import db
from portfolio.jobs.models import Job


class ContentConflict(ValueError):
    pass


class ContentValidationError(ValueError):
    pass


def save_draft(entity: object, command: ContentCommand, *, expected_version: int | None = None):
    if expected_version is not None and entity.version != expected_version:
        raise ContentConflict("Content was modified by another edit")
    editor_validation = validate_editor_source(command.source_markdown)
    if not editor_validation.valid:
        raise ContentValidationError(" ".join(editor_validation.errors))
    entity.title = command.title.strip()
    entity.summary = command.summary.strip()
    entity.source_markdown = command.source_markdown
    entity.rendered_html = render_markdown(command.source_markdown)
    if command.slug:
        entity.slug = command.slug.strip()
    entity.version += 1
    create_revision(entity, reason="draft-save")
    record_event(
        action="content.draft.saved",
        actor="admin",
        target_type=entity_type_for(entity),
        target_id=str(entity.id),
        metadata={"version": entity.version},
    )
    db.session.commit()
    return entity


def validate_publishable(entity: object) -> None:
    if not entity.title.strip() or not entity.slug.strip():
        raise ContentValidationError("Published content requires a title and slug")
    editor_validation = validate_editor_source(entity.source_markdown)
    if not editor_validation.valid:
        raise ContentValidationError(" ".join(editor_validation.errors))
    entity.rendered_html = render_markdown(entity.source_markdown)


def enqueue_unique(kind: str, entity_type: str, entity_id, run_at: datetime) -> Job:
    existing = db.session.execute(
        select(Job).where(
            Job.kind == kind,
            Job.entity_type == entity_type,
            Job.entity_id == entity_id,
            Job.state == "pending",
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.run_at = run_at
        return existing
    job = Job(kind=kind, entity_type=entity_type, entity_id=entity_id, run_at=run_at)
    db.session.add(job)
    db.session.flush()
    return job


def publish(entity: object, when: datetime | None = None):
    validate_publishable(entity)
    create_revision(entity, reason="publish")
    if when and when > utcnow():
        entity.state = PublicationState.SCHEDULED
        entity.publish_at = when
        enqueue_unique("publish", entity_type_for(entity), entity.id, when)
    else:
        entity.state = PublicationState.PUBLISHED
        entity.published_at = utcnow()
    entity.version += 1
    record_event(
        action="content.published",
        actor="admin",
        target_type=entity_type_for(entity),
        target_id=str(entity.id),
        metadata={"state": entity.state.value},
    )
    db.session.commit()
    return entity


def public_path_for(entity: object, slug: str) -> str:
    if isinstance(entity, Project):
        return f"/work/{slug}"
    if isinstance(entity, BlogPost):
        return f"/blog/{slug}"
    raise ContentValidationError("Slug redirects are supported for projects and blog posts")


def change_slug(entity: object, new_slug: str) -> Redirect | None:
    new_slug = new_slug.strip()
    if entity.slug == new_slug:
        return None
    old_path = public_path_for(entity, entity.slug)
    new_path = public_path_for(entity, new_slug)
    entity.slug = new_slug
    entity.version += 1
    redirect = Redirect(
        old_path=old_path,
        new_path=new_path,
        entity_type=entity_type_for(entity),
        entity_id=entity.id,
    )
    db.session.add(redirect)
    record_event(
        action="content.slug.changed",
        actor="admin",
        target_type=entity_type_for(entity),
        target_id=str(entity.id),
        metadata={"old_path": old_path, "new_path": new_path},
    )
    db.session.commit()
    return redirect
