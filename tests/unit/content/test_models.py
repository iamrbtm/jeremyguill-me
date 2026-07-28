from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from portfolio.content.enums import PublicationState
from portfolio.content.models import ContentRevision, Project


def test_project_slug_is_unique(db_session):
    db_session.add(Project(title="One", slug="same", summary="One", state=PublicationState.DRAFT))
    db_session.commit()

    db_session.add(Project(title="Two", slug="same", summary="Two", state=PublicationState.DRAFT))

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_revision_source_is_immutable(db_session):
    project = Project(title="One", slug="one", summary="One", state=PublicationState.DRAFT)
    db_session.add(project)
    db_session.commit()

    revision = ContentRevision(
        entity_type="project",
        entity_id=project.id,
        source_markdown="original",
        revision_number=1,
    )
    db_session.add(revision)
    db_session.commit()

    assert revision.source_markdown == "original"
