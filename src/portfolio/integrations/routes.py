from __future__ import annotations

import uuid

import httpx
from flask import Blueprint, jsonify, render_template, request

from portfolio.auth.decorators import passkey_required

from .services import (
    IntegrationNotConfigured,
    RevisionConflict,
    accept_revision,
    reject_revision,
    request_revision,
    save_nvidia_key,
)

integrations_bp = Blueprint("integrations", __name__, url_prefix="/admin")


@integrations_bp.get("/settings/ai")
@passkey_required
def ai_settings():
    return render_template("admin/settings/ai.html")


@integrations_bp.post("/settings/ai/key")
@passkey_required
def save_ai_key():
    payload = request.get_json(silent=True) or request.form
    models = save_nvidia_key(str(payload.get("api_key", "")))
    return jsonify({"models": [model.__dict__ for model in models]})


@integrations_bp.post("/settings/ai/models/refresh")
@passkey_required
def refresh_ai_models():
    payload = request.get_json(silent=True) or request.form
    models = save_nvidia_key(str(payload.get("api_key", "")))
    return jsonify({"models": [model.__dict__ for model in models]})


@integrations_bp.post("/ai/revise")
@passkey_required
def revise():
    payload = request.get_json(silent=True) or {}
    try:
        suggestion = request_revision(
            entity_type=str(payload.get("entity_type", "")),
            entity_id=uuid.UUID(str(payload.get("entity_id", ""))),
            action=str(payload.get("action", "")),
            custom_prompt=str(payload.get("custom_prompt", "")),
        )
    except httpx.TimeoutException:
        return jsonify({"error": "nvidia-timeout"}), 504
    except IntegrationNotConfigured:
        return jsonify({"error": "nvidia-not-configured"}), 409
    return (
        jsonify(
            {
                "suggestion_id": str(suggestion.id),
                "source_hash": suggestion.source_hash,
                "suggestion_markdown": suggestion.suggestion_markdown,
            }
        ),
        201,
    )


@integrations_bp.post("/ai/accept")
@passkey_required
def accept():
    payload = request.get_json(silent=True) or {}
    try:
        accept_revision(
            uuid.UUID(str(payload.get("suggestion_id", ""))),
            str(payload.get("source_hash", "")),
        )
    except RevisionConflict:
        return jsonify({"error": "source-hash-conflict"}), 409
    return "", 204


@integrations_bp.post("/ai/reject")
@passkey_required
def reject():
    payload = request.get_json(silent=True) or {}
    reject_revision(uuid.UUID(str(payload.get("suggestion_id", ""))))
    return "", 204
