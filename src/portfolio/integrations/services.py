from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict

import httpx
from flask import current_app

from portfolio.audit.services import record_event
from portfolio.content.models import Project, utcnow
from portfolio.content.schemas import ContentCommand
from portfolio.content.services import save_draft
from portfolio.extensions import db

from .crypto import decrypt_secret, encrypt_secret
from .models import AiRevisionSuggestion, IntegrationSecret
from .openai import OpenAIClient, RevisionRequest, hash_source


class IntegrationNotConfigured(RuntimeError):
    pass


class RevisionConflict(ValueError):
    pass


def load_openai_model() -> str:
    return _load_secret_value(
        "openai_model", current_app.config.get("OPENAI_MODEL", "gpt-4o-mini")
    )


def load_openai_models() -> list[dict[str, object]]:
    raw = _load_secret_value("openai_models", "[]")
    try:
        models = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(models, list):
        return []
    clean_models: list[dict[str, object]] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = str(model.get("id", "")).strip()
        if not model_id:
            continue
        clean_models.append(
            {
                "id": model_id,
                "enabled": bool(model.get("enabled", False)),
                "disabled_reason": str(model.get("disabled_reason", "")),
            }
        )
    return clean_models


def save_openai_model(model: str) -> str:
    clean_model = model.strip()[:160]
    if not clean_model:
        raise ValueError("OpenAI model is required")
    _save_secret_value("openai_model", clean_model)
    record_event(
        action="openai.model.saved",
        actor="admin",
        target_type="integration",
        target_id="openai",
        metadata={"model": clean_model},
    )
    db.session.commit()
    return clean_model


def save_openai_key(api_key: str, client: OpenAIClient | None = None) -> list[object]:
    client = client or OpenAIClient()
    models = client.validate_key(api_key)
    key_hint = api_key[-4:]
    _save_secret_value("openai_api_key", api_key, key_hint=key_hint)
    _save_secret_value("openai_models", json.dumps([asdict(model) for model in models]))
    record_event(
        action="openai.key.validated",
        actor="admin",
        target_type="integration",
        target_id="openai",
        metadata={"key_hint": key_hint},
    )
    db.session.commit()
    return models


def request_revision(
    *, entity_type: str, entity_id: uuid.UUID, action: str, custom_prompt: str = ""
) -> AiRevisionSuggestion:
    if entity_type != "project":
        raise ValueError("Unsupported AI revision entity")
    project = db.get_or_404(Project, entity_id)
    api_key = openai_api_key()
    model = load_openai_model()
    try:
        revision = OpenAIClient(base_url=os.getenv("OPENAI_BASE_URL")).revise(
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


def openai_api_key() -> str:
    env_key = os.getenv("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key
    secret = IntegrationSecret.query.filter_by(name="openai_api_key").one_or_none()
    if secret is None:
        raise IntegrationNotConfigured("OpenAI API key is not configured")
    return decrypt_secret(secret.encrypted_value)


def _load_secret_value(name: str, default: str = "") -> str:
    secret = IntegrationSecret.query.filter_by(name=name).one_or_none()
    if secret is None:
        return default
    return decrypt_secret(secret.encrypted_value)


def _save_secret_value(name: str, value: str, *, key_hint: str | None = None) -> None:
    secret = IntegrationSecret.query.filter_by(name=name).one_or_none()
    if secret is None:
        secret = IntegrationSecret(name=name, encrypted_value=b"")
        db.session.add(secret)
    secret.encrypted_value = encrypt_secret(value)
    secret.key_hint = key_hint
    secret.version = (secret.version or 1) + 1
