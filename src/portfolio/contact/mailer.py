from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from enum import StrEnum

from flask import current_app

from portfolio.extensions import db
from portfolio.integrations.crypto import decrypt_secret, encrypt_secret
from portfolio.integrations.models import IntegrationSecret

from .models import ContactSubmission


class DeliveryResult(StrEnum):
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class SmtpSettings:
    host: str = ""
    port: int = 587
    security: str = "starttls"
    username: str = ""
    password: str = ""
    sender: str = "contact@jeremyguill.me"
    recipient: str = "jeremy@jeremyguill.me"

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.sender and self.recipient)


def send_submission_notification(submission_id) -> DeliveryResult:
    submission = db.session.get(ContactSubmission, submission_id)
    if submission is None:
        return DeliveryResult.SKIPPED
    settings = load_smtp_settings()
    if not settings.is_configured:
        submission.delivery_status = DeliveryResult.SKIPPED.value
        db.session.commit()
        return DeliveryResult.SKIPPED
    try:
        send_message(build_notification(submission, settings), settings)
    except (OSError, smtplib.SMTPException) as exc:
        submission.delivery_status = DeliveryResult.FAILED.value
        submission.delivery_error_code = safe_error_code(exc)
        db.session.commit()
        return DeliveryResult.FAILED
    submission.delivery_status = DeliveryResult.SENT.value
    db.session.commit()
    return DeliveryResult.SENT


def build_notification(submission: ContactSubmission, settings: SmtpSettings | None = None) -> EmailMessage:
    settings = settings or load_smtp_settings()
    message = EmailMessage()
    message["From"] = settings.sender
    message["To"] = settings.recipient
    message["Reply-To"] = submission.email
    message["Subject"] = f"Portfolio contact: {submission.subject}"
    body = (
        f"Name: {submission.name}\n"
        f"Email: {submission.email}\n"
        f"Subject: {submission.subject}\n\n"
        f"{submission.message}"
    )
    message.set_content(body)
    return message


def send_test_email(recipient: str | None = None) -> None:
    settings = load_smtp_settings()
    if not settings.is_configured:
        raise RuntimeError("SMTP settings are incomplete")
    message = EmailMessage()
    message["From"] = settings.sender
    message["To"] = recipient or settings.recipient
    message["Subject"] = "JeremyGuill.me SMTP test"
    message.set_content("SMTP delivery is configured for JeremyGuill.me.")
    send_message(message, settings)


def send_message(message: EmailMessage, settings: SmtpSettings) -> None:
    smtp_class = smtplib.SMTP_SSL if settings.security == "ssl" else smtplib.SMTP
    with smtp_class(settings.host, settings.port, timeout=10) as smtp:
        if settings.security == "starttls":
            smtp.starttls()
        if settings.username:
            smtp.login(settings.username, settings.password)
        smtp.send_message(message)


def save_smtp_settings(form) -> SmtpSettings:
    existing = load_smtp_settings()
    host = str(form.get("host", "")).strip()
    port = _coerce_port(str(form.get("port", "")).strip() or "587")
    security = str(form.get("security", "starttls")).strip().lower()
    if security not in {"none", "starttls", "ssl"}:
        raise ValueError("Unsupported SMTP security mode")
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    sender = str(form.get("sender", "")).strip()
    recipient = str(form.get("recipient", "")).strip()

    _save_setting("smtp_host", host)
    _save_setting("smtp_port", str(port))
    _save_setting("smtp_security", security)
    _save_setting("smtp_username", username)
    if password:
        _save_setting("smtp_password", password, key_hint=password[-4:])
    elif not existing.password:
        _save_setting("smtp_password", "")
    _save_setting("smtp_sender", sender)
    _save_setting("smtp_recipient", recipient)
    db.session.commit()
    return load_smtp_settings()


def load_smtp_settings() -> SmtpSettings:
    return SmtpSettings(
        host=_load_setting("smtp_host", "SMTP_HOST", ""),
        port=_coerce_port(_load_setting("smtp_port", "SMTP_PORT", "587")),
        security=_load_security(),
        username=_load_setting("smtp_username", "SMTP_USERNAME", ""),
        password=_load_setting("smtp_password", "SMTP_PASSWORD", ""),
        sender=_load_setting("smtp_sender", "SMTP_SENDER", "contact@jeremyguill.me"),
        recipient=_load_setting("smtp_recipient", "CONTACT_RECIPIENT", "jeremy@jeremyguill.me"),
    )


def smtp_password_is_saved() -> bool:
    secret = IntegrationSecret.query.filter_by(name="smtp_password").one_or_none()
    return bool(secret and decrypt_secret(secret.encrypted_value))


def _load_security() -> str:
    saved = _load_setting("smtp_security", "", "")
    if saved in {"none", "starttls", "ssl"}:
        return saved
    return "starttls" if current_app.config.get("SMTP_TLS", True) else "none"


def _load_setting(name: str, config_name: str, default: str) -> str:
    secret = IntegrationSecret.query.filter_by(name=name).one_or_none()
    if secret is not None:
        return decrypt_secret(secret.encrypted_value)
    return str(current_app.config.get(config_name, default)) if config_name else default


def _save_setting(name: str, value: str, *, key_hint: str | None = None) -> None:
    secret = IntegrationSecret.query.filter_by(name=name).one_or_none()
    if secret is None:
        secret = IntegrationSecret(name=name, encrypted_value=b"")
        db.session.add(secret)
    secret.encrypted_value = encrypt_secret(value)
    secret.key_hint = key_hint
    secret.version = (secret.version or 1) + 1


def _coerce_port(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65535:
        raise ValueError("SMTP port must be between 1 and 65535")
    return port


def safe_error_code(exc: BaseException) -> str:
    return exc.__class__.__name__.lower()[:80]
