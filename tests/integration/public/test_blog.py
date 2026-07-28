from __future__ import annotations

from datetime import UTC, datetime

import pytest

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost
from portfolio.extensions import db


@pytest.fixture()
def published_post(db_session):
    post = BlogPost(
        title="Useful Post",
        slug="useful-post",
        summary="A useful summary",
        source_markdown="Body",
        rendered_html="<p>Body</p>",
        state=PublicationState.PUBLISHED,
        published_at=datetime.now(UTC),
    )
    db.session.add(post)
    db.session.commit()
    return post


def test_blog_index_empty_state(client):
    response = client.get("/blog")

    assert response.status_code == 200
    assert b"No posts are published yet" in response.data


def test_published_blog_post_is_visible(client, published_post):
    response = client.get(f"/blog/{published_post.slug}")

    assert response.status_code == 200
    assert b"Useful Post" in response.data
    assert b"<p>Body</p>" in response.data


def test_draft_blog_post_is_private(client, db_session):
    post = BlogPost(title="Draft", slug="draft", summary="", state=PublicationState.DRAFT)
    db.session.add(post)
    db.session.commit()

    response = client.get("/blog/draft")

    assert response.status_code == 404


def test_resume_redirects_to_current_public_asset(client):
    response = client.get("/resume")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/static/resume/Resume2026.pdf")
