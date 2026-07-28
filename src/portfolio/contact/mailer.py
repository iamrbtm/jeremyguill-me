from __future__ import annotations

import smtplib
from email.message import EmailMessage
from enum import StrEnum

from flask import current_app

from portfolio.extensions import db

from .models import ContactSubmission


class DeliveryResult(StrEnum):
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


def send_submission_notification(submission_id) -> DeliveryResult:
    submission = db.session.get(ContactSubmission, submission_id)
    if submission is None:
        return DeliveryResult.SKIPPED
    host = current_app.config.get("SMTP_HOST", "")
    if not host:
        submission.delivery_status = DeliveryResult.SKIPPED.value
        db.session.commit()
        return DeliveryResult.SKIPPED
    try:
        message = build_notification(submission)
        with smtplib.SMTP(host, int(current_app.config.get("SMTP_PORT", 587)), timeout=10) as smtp:
            if current_app.config.get("SMTP_TLS", True):
                smtp.starttls()
            username = current_app.config.get("SMTP_USERNAME", "")
            password = current_app.config.get("SMTP_PASSWORD", "")
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        submission.delivery_status = DeliveryResult.FAILED.value
        submission.delivery_error_code = safe_error_code(exc)
        db.session.commit()
        return DeliveryResult.FAILED
    submission.delivery_status = DeliveryResult.SENT.value
    db.session.commit()
    return DeliveryResult.SENT


def build_notification(submission: ContactSubmission) -> EmailMessage:
    message = EmailMessage()
    sender = current_app.config.get("SMTP_SENDER", "contact@jeremyguill.me")
    recipient = current_app.config.get("CONTACT_RECIPIENT", "jeremy@jeremyguill.me")
    message["From"] = sender
    message["To"] = recipient
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


def safe_error_code(exc: BaseException) -> str:
    return exc.__class__.__name__.lower()[:80]
