from __future__ import annotations

import uuid

import httpx
from flask import current_app

from portfolio.audit.services import record_event
from portfolio.content.models import Project, utcnow
from portfolio.content.schemas import ContentCommand
from portfolio.content.services import save_draft
from portfolio.extensions import db

from .crypto import decrypt_secret, encrypt_secret
from .models import AiRevisionSuggestion, IntegrationSecret
from .nvidia import NvidiaClient, RevisionRequest, hash_source


class IntegrationNotConfigured(RuntimeError):
    pass


class RevisionConflict(ValueError):
    pass


def save_nvidia_key(api_key: str, client: NvidiaClient | None = None) -> list[object]:
    client = client or NvidiaClient()
    models = client.validate_key(api_key)
    secret = IntegrationSecret.query.filter_by(name="nvidia_api_key").one_or_none()
    if secret is None:
        secret = IntegrationSecret(name="nvidia_api_key", encrypted_value=b"")
        db.session.add(secret)
    secret.encrypted_value = encrypt_secret(api_key)
    secret.key_hint = api_key[-4:]
    secret.version = (secret.version or 1) + 1
    record_event(
        action="nvidia.key.validated",
        actor="admin",
        target_type="integration",
        target_id="nvidia",
        metadata={"key_hint": secret.key_hint},
    )
    db.session.commit()
    return models


def request_revision(
    *, entity_type: str, entity_id: uuid.UUID, action: str, custom_prompt: str = ""
) -> AiRevisionSuggestion:
    if entity_type != "project":
        raise ValueError("Unsupported AI revision entity")
    project = db.get_or_404(Project, entity_id)
    api_key = _nvidia_api_key()
    model = current_app.config.get("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
    try:
        revision = NvidiaClient().revise(
            RevisionRequest(
                api_key=api_key,
                model=model,
                source_markdown=project.source_markdown,
                action=action,
                custom_prompt=custom_prompt,
            )
        )
    except httpx.TimeoutException:
        raise
    suggestion = AiRevisionSuggestion(
        entity_type=entity_type,
        entity_id=project.id,
        action=revision.action,
        model=revision.model,
        source_hash=revision.source_hash,
        suggestion_markdown=revision.suggestion_markdown,
    )
    db.session.add(suggestion)
    record_event(
        action="ai.revision.requested",
        actor="admin",
        target_type=entity_type,
        target_id=str(project.id),
        metadata={"action": action, "model": model},
    )
    db.session.commit()
    return suggestion


def accept_revision(suggestion_id: uuid.UUID, submitted_source_hash: str) -> None:
    suggestion = db.get_or_404(AiRevisionSuggestion, suggestion_id)
    if suggestion.entity_type != "project":
        raise ValueError("Unsupported AI revision entity")
    project = db.get_or_404(Project, suggestion.entity_id)
    current_source_hash = hash_source(project.source_markdown)
    if (
        submitted_source_hash != suggestion.source_hash
        or current_source_hash != suggestion.source_hash
    ):
        raise RevisionConflict("Source content changed after the suggestion was created")
    suggestion.accepted_at = utcnow()
    save_draft(
        project,
        ContentCommand(
            title=project.title,
            slug=project.slug,
            summary=project.summary,
            source_markdown=suggestion.suggestion_markdown,
        ),
        expected_version=project.version,
    )


def reject_revision(suggestion_id: uuid.UUID) -> None:
    suggestion = db.get_or_404(AiRevisionSuggestion, suggestion_id)
    suggestion.rejected_at = utcnow()
    record_event(
        action="ai.revision.rejected",
        actor="admin",
        target_type=suggestion.entity_type,
        target_id=str(suggestion.entity_id),
    )
    db.session.commit()


def _nvidia_api_key() -> str:
    secret = IntegrationSecret.query.filter_by(name="nvidia_api_key").one_or_none()
    if secret is None:
        raise IntegrationNotConfigured("NVIDIA API key is not configured")
    return decrypt_secret(secret.encrypted_value)
