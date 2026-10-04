from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy import select

from portfolio.content.models import SiteProfile
from portfolio.extensions import db
from portfolio.integrations.crypto import encrypt_secret
from portfolio.integrations.models import IntegrationSecret
from portfolio.integrations.openai import SeoOptimizationResult
from portfolio.seo.automation import load_settings, run_daily_review
from portfolio.seo.models import SeoActionLog, SeoTargetQuery


@pytest.fixture()
def authenticated_client(client):
    with client.session_transaction() as session:
        session["admin_session_id"] = "seo-admin"
    return client


@dataclass
class FakeOpenAIClient:
    def optimize_seo(self, request):
        return SeoOptimizationResult(
            target_queries=["software workflow portfolio"],
            seo_title="Software Workflow Portfolio | Jeremy Guill",
            seo_description="Practical software and workflow automation portfolio.",
            visible_summary="Improved public summary.",
            rationale="Matches employer search intent.",
        )


class FailingOpenAIClient:
    def optimize_seo(self, request):
        raise RuntimeError("OpenAI request failed: 404 model not found")


def test_daily_review_updates_metadata_and_targets(db_session):
    profile = SiteProfile(display_name="Jeremy Guill", summary="Original summary")
    db.session.add(profile)
    db.session.add(
        IntegrationSecret(
            name="openai_api_key",
            encrypted_value=encrypt_secret("openai-secret"),
            key_hint="cret",
        )
    )
    settings = load_settings()
    settings.enabled = True
    settings.daily_request_limit = 1
    db.session.commit()

    result = run_daily_review(client=FakeOpenAIClient())

    db.session.refresh(profile)
    assert result.updated == 1
    assert profile.seo_title == "Software Workflow Portfolio | Jeremy Guill"
    assert profile.summary == "Original summary"
    assert (
        db.session.execute(
            select(SeoTargetQuery).where(SeoTargetQuery.query == "software workflow portfolio")
        ).scalar_one_or_none()
        is not None
    )
    assert (
        db.session.execute(
            select(SeoActionLog).where(SeoActionLog.action == "seo.daily.completed")
        ).scalar_one_or_none()
        is not None
    )


def test_daily_review_logs_actionable_entity_failure_details(db_session):
    db.session.add(SiteProfile(display_name="Jeremy Guill", summary="Original summary"))
    db.session.add(
        IntegrationSecret(
            name="openai_api_key",
            encrypted_value=encrypt_secret("openai-secret"),
            key_hint="cret",
        )
    )
    settings = load_settings()
    settings.enabled = True
    settings.daily_request_limit = 1
    db.session.commit()

    result = run_daily_review(client=FailingOpenAIClient())

    failure = db.session.execute(
        select(SeoActionLog).where(SeoActionLog.action == "seo.entity.failed")
    ).scalar_one()
    assert result.skipped == 1
    assert failure.details == {
        "error_code": "RuntimeError",
        "error_message": "OpenAI request failed: 404 model not found",
    }


def test_seo_settings_page_uses_saved_model_dropdown(authenticated_client, db_session):
    db.session.add(
        IntegrationSecret(
            name="openai_models",
            encrypted_value=encrypt_secret(
                '[{"id":"gpt-4o-mini","enabled":true},'
                '{"id":"text-embedding-3-small","enabled":false}]'
            ),
        )
    )
    db.session.commit()

    response = authenticated_client.get("/admin/settings/seo")

    assert response.status_code == 200
    assert b"gpt-4o-mini" in response.data
    assert b"text-embedding-3-small" not in response.data
