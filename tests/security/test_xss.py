from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.extensions import db


def test_project_summary_is_escaped(client, db_session):
    project = Project(
        title="Safe",
        slug="safe",
        summary="<script>alert(1)</script>",
        source_markdown="Body",
        rendered_html="<p>Body</p>",
        state=PublicationState.PUBLISHED,
    )
    db.session.add(project)
    db.session.commit()

    response = client.get("/work/safe")

    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data
