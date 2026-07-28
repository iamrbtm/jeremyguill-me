from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, SiteProfile


def test_homepage_uses_required_headline(client, db_session):
    db_session.add(SiteProfile())
    db_session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert b"I build practical software for real-world problems." in response.data


def test_blog_navigation_is_hidden_without_published_posts(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b'href="/blog"' not in response.data


def test_blog_navigation_shows_with_published_posts(client, db_session):
    db_session.add(
        BlogPost(
            title="Post",
            slug="post",
            summary="Summary",
            state=PublicationState.PUBLISHED,
        )
    )
    db_session.commit()

    response = client.get("/")

    assert b'href="/blog"' in response.data


def test_draft_project_is_not_public(client, db_session):
    draft_project = Project(
        title="Draft",
        slug="draft",
        summary="Draft",
        state=PublicationState.DRAFT,
    )
    db_session.add(draft_project)
    db_session.commit()

    assert client.get(f"/work/{draft_project.slug}").status_code == 404


def test_published_project_has_public_page(client, db_session):
    project = Project(
        title="Pollywog",
        slug="pollywog",
        summary="Scheduling automation",
        source_markdown="Replaced a manual process with an automated workflow.",
        rendered_html="<p>Replaced a manual process with an automated workflow.</p>",
        state=PublicationState.PUBLISHED,
    )
    db_session.add(project)
    db_session.commit()

    response = client.get("/work/pollywog")

    assert response.status_code == 200
    assert b"Pollywog" in response.data
