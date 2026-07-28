from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import ContentRevision, Project
from portfolio.content.revisions import rollback


def test_rollback_restores_prior_revision(db_session):
    project = Project(
        title="Project",
        slug="project",
        summary="Summary",
        source_markdown="new",
        rendered_html="<p>new</p>",
        state=PublicationState.PUBLISHED,
    )
    db_session.add(project)
    db_session.commit()
    db_session.add(
        ContentRevision(
            entity_type="project",
            entity_id=project.id,
            source_markdown="original",
            rendered_html="<p>original</p>",
            revision_number=1,
        )
    )
    db_session.commit()

    rollback(project, 1)

    assert project.source_markdown == "original"
    assert project.rendered_html == "<p>original</p>"
    assert project.revisions[-1].reason == "rollback"
