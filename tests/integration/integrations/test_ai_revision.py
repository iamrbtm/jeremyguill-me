from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.extensions import db
from portfolio.integrations.crypto import encrypt_secret
from portfolio.integrations.models import AiRevisionSuggestion, IntegrationSecret


@pytest.fixture()
def authenticated_client(client):
    with client.session_transaction() as session:
        session["admin_session_id"] = str(uuid.uuid4())
    return client


@pytest.fixture()
def project(db_session):
    project = Project(
        title="AI Project",
        slug="ai-project",
        summary="Summary",
        source_markdown="original",
        rendered_html="<p>original</p>",
        state=PublicationState.DRAFT,
    )
    db.session.add(project)
    db.session.commit()
    return project


@pytest.fixture()
def saved_nvidia_key(db_session):
    secret = IntegrationSecret(
        name="nvidia_api_key",
        encrypted_value=encrypt_secret("nvapi-secret"),
        key_hint="cret",
    )
    db.session.add(secret)
    db.session.commit()
    return secret


def test_revision_timeout_preserves_source(
    authenticated_client, project, saved_nvidia_key, respx_mock
):
    respx_mock.post("https://integrate.api.nvidia.com/v1/chat/completions").mock(
        side_effect=httpx.ReadTimeout("late")
    )

    response = authenticated_client.post(
        "/admin/ai/revise",
        json={"entity_type": "project", "entity_id": str(project.id), "action": "clarity"},
    )

    assert response.status_code == 504
    db.session.refresh(project)
    assert project.source_markdown == "original"


def test_revision_stores_suggestion_without_overwriting_source(
    authenticated_client, project, saved_nvidia_key, respx_mock
):
    respx_mock.post("https://integrate.api.nvidia.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "clearer original"}}]},
        )
    )

    response = authenticated_client.post(
        "/admin/ai/revise",
        json={"entity_type": "project", "entity_id": str(project.id), "action": "clarity"},
    )

    assert response.status_code == 201
    db.session.refresh(project)
    assert project.source_markdown == "original"
    suggestion = db.session.execute(select(AiRevisionSuggestion)).scalar_one()
    assert suggestion.suggestion_markdown == "clearer original"
    assert suggestion.accepted_at is None


def test_accept_revision_fails_when_source_hash_changed(
    authenticated_client, db_session, project, saved_nvidia_key, respx_mock
):
    respx_mock.post("https://integrate.api.nvidia.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "clearer original"}}]},
        )
    )
    created = authenticated_client.post(
        "/admin/ai/revise",
        json={"entity_type": "project", "entity_id": str(project.id), "action": "clarity"},
    ).get_json()
    project.source_markdown = "changed"
    db.session.commit()

    response = authenticated_client.post(
        "/admin/ai/accept",
        json={"suggestion_id": created["suggestion_id"], "source_hash": created["source_hash"]},
    )

    assert response.status_code == 409
    db.session.refresh(project)
    assert project.source_markdown == "changed"


def test_accept_revision_requires_explicit_acceptance(
    authenticated_client, db_session, project, saved_nvidia_key, respx_mock
):
    respx_mock.post("https://integrate.api.nvidia.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "clearer original"}}]},
        )
    )
    created = authenticated_client.post(
        "/admin/ai/revise",
        json={"entity_type": "project", "entity_id": str(project.id), "action": "clarity"},
    ).get_json()

    response = authenticated_client.post(
        "/admin/ai/accept",
        json={"suggestion_id": created["suggestion_id"], "source_hash": created["source_hash"]},
    )

    assert response.status_code == 204
    db.session.refresh(project)
    assert project.source_markdown == "clearer original"
    suggestion = db.session.get(AiRevisionSuggestion, uuid.UUID(created["suggestion_id"]))
    assert suggestion.accepted_at is not None
