from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost
from portfolio.extensions import db
from portfolio.integrations.openai import SeoOptimizationResult
from portfolio.seo.automation import OpenAIClient as RealOpenAIClient


class FakeOpenAIClient:
    def __init__(self, *args, **kwargs):
        pass

    def optimize_seo(self, request):
        return SeoOptimizationResult(
            target_queries=["practical software portfolio"],
            seo_title="Practical Software Portfolio | Jeremy Guill",
            seo_description="Notes on workflow systems and practical software.",
            visible_summary="AI-improved summary.",
            rationale="Matches employer search intent.",
        )


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("portfolio.seo.automation.OpenAIClient", FakeOpenAIClient)


@pytest.fixture()
def authenticated_client(client):
    with client.session_transaction() as session:
        session["admin_session_id"] = str(uuid.uuid4())
    return client


@pytest.fixture()
def blog_post(db_session):
    post = BlogPost(
        title="Draft Post",
        slug="draft-post",
        summary="A draft",
        source_markdown="Draft body",
        state=PublicationState.DRAFT,
    )
    db.session.add(post)
    db.session.commit()
    return post


def blog_form(post: BlogPost, **overrides):
    data = {
        "title": post.title,
        "slug": post.slug,
        "summary": post.summary,
        "source_markdown": post.source_markdown,
        "seo_title": post.seo_title or "",
        "seo_description": "",
        "seo_target_query": post.seo_target_query or "",
        "version": str(post.version),
    }
    data.update(overrides)
    return data


def test_admin_blog_list_links_to_edit(authenticated_client, db_session, blog_post):
    response = authenticated_client.get("/admin/blog")

    assert response.status_code == 200
    assert b"New Blog Post" in response.data
    assert f"/admin/blog/{blog_post.id}".encode() in response.data


def test_create_blog_post_then_edit(authenticated_client, db_session):
    response = authenticated_client.post(
        "/admin/blog",
        data={
            "title": "New Post",
            "slug": "new-post",
            "summary": "New summary",
            "source_markdown": "New body",
            "version": "0",
        },
    )

    assert response.status_code == 302
    post = db.session.execute(select(BlogPost).where(BlogPost.slug == "new-post")).scalar_one()
    assert post.state == PublicationState.DRAFT
    assert post.source_markdown == "New body"

    updated = authenticated_client.post(
        f"/admin/blog/{post.id}",
        data=blog_form(post, title="Renamed", source_markdown="Updated body"),
    )
    assert updated.status_code == 302
    db.session.refresh(post)
    assert post.title == "Renamed"
    assert post.version == 2


def test_create_blog_rejects_duplicate_slug(authenticated_client, db_session, blog_post):
    response = authenticated_client.post(
        "/admin/blog",
        data={
            "title": "Duplicate",
            "slug": blog_post.slug,
            "summary": "x",
            "source_markdown": "y",
            "version": "0",
        },
    )

    assert response.status_code == 409
    assert b"A blog post with this slug already exists" in response.data


def test_run_ai_seo_applies_metadata(authenticated_client, db_session, blog_post):
    response = authenticated_client.post(f"/admin/blog/{blog_post.id}/seo")

    assert response.status_code == 302
    db.session.refresh(blog_post)
    assert blog_post.seo_title == "Practical Software Portfolio | Jeremy Guill"
    assert blog_post.summary == "AI-improved summary."


def test_publish_runs_seo_then_publishes(authenticated_client, db_session, blog_post):
    response = authenticated_client.post(f"/admin/blog/{blog_post.id}/publish")

    assert response.status_code == 302
    db.session.refresh(blog_post)
    assert blog_post.state == PublicationState.PUBLISHED
    assert blog_post.published_at is not None
    assert blog_post.seo_title == "Practical Software Portfolio | Jeremy Guill"


def test_publish_without_openai_still_publishes(
    authenticated_client, db_session, blog_post, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("portfolio.seo.automation.OpenAIClient", RealOpenAIClient)

    response = authenticated_client.post(f"/admin/blog/{blog_post.id}/publish")

    assert response.status_code == 302
    db.session.refresh(blog_post)
    assert blog_post.state == PublicationState.PUBLISHED


def test_archive_restore_delete(authenticated_client, db_session, blog_post):
    archive = authenticated_client.post(f"/admin/blog/{blog_post.id}/archive")
    db.session.refresh(blog_post)
    assert archive.status_code == 302
    assert blog_post.state == PublicationState.ARCHIVED

    restore = authenticated_client.post(f"/admin/blog/{blog_post.id}/restore")
    db.session.refresh(blog_post)
    assert restore.status_code == 302
    assert blog_post.state == PublicationState.DRAFT

    delete = authenticated_client.post(f"/admin/blog/{blog_post.id}/delete")
    assert delete.status_code == 302
    assert (
        db.session.execute(select(BlogPost).where(BlogPost.id == blog_post.id)).scalar_one_or_none()
        is None
    )
