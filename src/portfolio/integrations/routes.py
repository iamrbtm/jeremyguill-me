from __future__ import annotations

import smtplib
import uuid

import httpx
from flask import Blueprint, jsonify, render_template, request

from portfolio.auth.decorators import passkey_required
from portfolio.contact.mailer import (
    load_smtp_settings,
    save_smtp_settings,
    send_test_email,
    smtp_password_is_saved,
)
from portfolio.seo.automation import active_targets, recent_logs
from portfolio.seo.automation import load_settings as load_seo_settings
from portfolio.seo.automation import save_settings as save_seo_settings_service

from .services import (
    IntegrationNotConfigured,
    RevisionConflict,
    accept_revision,
    load_openai_model,
    load_openai_models,
    reject_revision,
    request_revision,
    save_openai_key,
    save_openai_model,
)

integrations_bp = Blueprint("integrations", __name__, url_prefix="/admin")


@integrations_bp.get("/settings/ai")
@passkey_required
def ai_settings():
    return _render_ai_settings()


@integrations_bp.get("/settings/email")
@passkey_required
def email_settings():
    return render_template(
        "admin/settings/email.html",
        settings=load_smtp_settings(),
        password_is_saved=smtp_password_is_saved(),
    )


@integrations_bp.get("/settings/seo")
@passkey_required
def seo_settings():
    return render_template(
        "admin/settings/seo.html",
        settings=load_seo_settings(),
        openai_models=load_openai_models(),
        targets=active_targets(),
        logs=recent_logs(),
    )


@integrations_bp.post("/settings/seo")
@passkey_required
def save_seo_settings():
    try:
        settings = save_seo_settings_service(request.form)
    except ValueError as exc:
        return (
            render_template(
                "admin/settings/seo.html",
                settings=load_seo_settings(),
                openai_models=load_openai_models(),
                targets=active_targets(),
                logs=recent_logs(),
                error=str(exc),
            ),
            422,
        )
    return render_template(
        "admin/settings/seo.html",
        settings=settings,
        openai_models=load_openai_models(),
        targets=active_targets(),
        logs=recent_logs(),
        message="SEO automation settings saved.",
    )


@integrations_bp.post("/settings/email")
@passkey_required
def save_email_settings():
    try:
        settings = save_smtp_settings(request.form)
    except ValueError as exc:
        return (
            render_template(
                "admin/settings/email.html",
                settings=load_smtp_settings(),
                password_is_saved=smtp_password_is_saved(),
                error=str(exc),
            ),
            422,
        )
    return render_template(
        "admin/settings/email.html",
        settings=settings,
        password_is_saved=smtp_password_is_saved(),
        message="SMTP settings saved.",
    )


@integrations_bp.post("/settings/email/test")
@passkey_required
def test_email_settings():
    try:
        send_test_email(request.form.get("test_recipient") or None)
    except (RuntimeError, OSError, smtplib.SMTPException) as exc:
        return (
            render_template(
                "admin/settings/email.html",
                settings=load_smtp_settings(),
                password_is_saved=smtp_password_is_saved(),
                error=f"Test email failed: {exc.__class__.__name__}",
            ),
            502,
        )
    return render_template(
        "admin/settings/email.html",
        settings=load_smtp_settings(),
        password_is_saved=smtp_password_is_saved(),
        message="Test email sent.",
    )


@integrations_bp.post("/settings/ai/key")
@passkey_required
def save_ai_key():
    payload = request.get_json(silent=True) or request.form
    models = save_openai_key(str(payload.get("api_key", "")))
    if not request.is_json:
        return _render_ai_settings(message="OpenAI API key validated and model list refreshed.")
    return jsonify({"models": [model.__dict__ for model in models]})


@integrations_bp.post("/settings/ai/model")
@passkey_required
def save_ai_model():
    try:
        save_openai_model(str(request.form.get("openai_model", "")))
    except ValueError as exc:
        return _render_ai_settings(error=str(exc)), 422
    return _render_ai_settings(message="Default OpenAI model saved.")


@integrations_bp.post("/settings/ai/models/refresh")
@passkey_required
def refresh_ai_models():
    payload = request.get_json(silent=True) or request.form
    models = save_openai_key(str(payload.get("api_key", "")))
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
        return jsonify({"error": "openai-timeout"}), 504
    except IntegrationNotConfigured:
        return jsonify({"error": "openai-not-configured"}), 409
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


def _render_ai_settings(*, message: str = "", error: str = ""):
    return render_template(
        "admin/settings/ai.html",
        current_model=load_openai_model(),
        openai_models=load_openai_models(),
        message=message,
        error=error,
    )
