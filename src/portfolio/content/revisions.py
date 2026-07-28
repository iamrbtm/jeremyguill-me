from __future__ import annotations

from sqlalchemy import func, select

from portfolio.content.models import ContentRevision
from portfolio.extensions import db


def entity_type_for(entity: object) -> str:
    return entity.__class__.__name__.replace("Post", "").lower()


def next_revision_number(entity: object) -> int:
    current = db.session.execute(
        select(func.max(ContentRevision.revision_number)).where(
            ContentRevision.entity_type == entity_type_for(entity),
            ContentRevision.entity_id == entity.id,
        )
    ).scalar_one()
    return int(current or 0) + 1


def create_revision(entity: object, *, reason: str) -> ContentRevision:
    revision = ContentRevision(
        entity_type=entity_type_for(entity),
        entity_id=entity.id,
        source_markdown=entity.source_markdown,
        rendered_html=entity.rendered_html,
        revision_number=next_revision_number(entity),
        reason=reason,
    )
    db.session.add(revision)
    db.session.flush()
    return revision


def rollback(entity: object, revision_number: int):
    revision = db.session.execute(
        select(ContentRevision).where(
            ContentRevision.entity_type == entity_type_for(entity),
            ContentRevision.entity_id == entity.id,
            ContentRevision.revision_number == revision_number,
        )
    ).scalar_one()
    entity.source_markdown = revision.source_markdown
    entity.rendered_html = revision.rendered_html
    entity.version += 1
    create_revision(entity, reason="rollback")
    db.session.commit()
    return entity
