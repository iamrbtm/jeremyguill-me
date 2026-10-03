from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost
from portfolio.extensions import db
from portfolio.integrations.openai import SeoOptimizationResult
from portfolio.seo.automation import run_blog_seo
from portfolio.seo.models import SeoActionLog, SeoTargetQuery


@dataclass
class FakeOpenAIClient:
    def optimize_seo(self, request):
        return SeoOptimizationResult(
            target_queries=["practical software portfolio"],
            seo_title="Practical Software Portfolio | Jeremy Guill",
            seo_description="Notes on workflow systems and practical software.",
            visible_summary="AI-improved summary.",
            rationale="Matches employer search intent.",
        )


class FailingOpenAIClient:
    def optimize_seo(self, request):
        raise RuntimeError("OpenAI request failed: 404 model not found")


@pytest.fixture(autouse=True)
def openai_key_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_run_blog_seo_applies_metadata_and_summary(db_session):
    post = BlogPost(
        title="My Post",
        slug="my-post",
        summary="Original summary",
        source_markdown="Body content",
        state=PublicationState.DRAFT,
    )
    db.session.add(post)
    db.session.commit()

    run_blog_seo(post, client=FakeOpenAIClient())

    db.session.refresh(post)
    assert post.seo_title == "Practical Software Portfolio | Jeremy Guill"
    assert post.seo_description == "Notes on workflow systems and practical software."
    assert post.seo_target_query == "practical software portfolio"
    assert post.summary == "AI-improved summary."
    assert (
        db.session.execute(
            select(SeoTargetQuery).where(SeoTargetQuery.query == "practical software portfolio")
        ).scalar_one_or_none()
        is not None
    )
    log = db.session.execute(
        select(SeoActionLog).where(SeoActionLog.action == "seo.blog.reviewed")
    ).scalar_one()
    assert log.entity_id == post.id


def test_run_blog_seo_does_not_overwrite_source_markdown(db_session):
    post = BlogPost(
        title="My Post",
        slug="my-post",
        summary="Original summary",
        source_markdown="Body content",
        state=PublicationState.DRAFT,
    )
    db.session.add(post)
    db.session.commit()

    run_blog_seo(post, client=FakeOpenAIClient())

    db.session.refresh(post)
    assert post.source_markdown == "Body content"


def test_run_blog_seo_raises_when_not_configured(db_session, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    post = BlogPost(
        title="My Post",
        slug="my-post",
        summary="Original summary",
        source_markdown="Body content",
        state=PublicationState.DRAFT,
    )
    db.session.add(post)
    db.session.commit()

    from portfolio.integrations.services import IntegrationNotConfigured

    with pytest.raises(IntegrationNotConfigured):
        run_blog_seo(post, client=FakeOpenAIClient())


def test_run_blog_seo_does_not_bump_version_when_unchanged(db_session):
    post = BlogPost(
        title="My Post",
        slug="my-post",
        summary="AI-improved summary.",
        source_markdown="Body content",
        state=PublicationState.DRAFT,
        version=1,
        seo_title="Practical Software Portfolio | Jeremy Guill",
        seo_description="Notes on workflow systems and practical software.",
        seo_target_query="practical software portfolio",
    )
    db.session.add(post)
    db.session.commit()

    run_blog_seo(post, client=FakeOpenAIClient())

    db.session.refresh(post)
    assert post.version == 1
