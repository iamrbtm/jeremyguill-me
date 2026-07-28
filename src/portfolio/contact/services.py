from __future__ import annotations

import time

from portfolio.audit.services import record_event
from portfolio.extensions import db

from . import mailer
from .forms import ContactCommand
from .mailer import DeliveryResult
from .models import ContactSubmission

CONTACT_STATES = {"unread", "read", "replied", "archived", "spam"}
MIN_FORM_FILL_SECONDS = 3.0


def save_submission(command: ContactCommand) -> ContactSubmission | None:
    if _is_spam(command):
        return None
    submission = ContactSubmission(
        name=command.name,
        email=command.email,
        subject=command.subject,
        message=command.message,
        state="unread",
        delivery_status="pending",
    )
    db.session.add(submission)
    record_event(
        action="contact.submitted",
        actor="public",
        target_type="contact_submission",
        metadata={"subject_length": len(command.subject), "message_length": len(command.message)},
    )
    db.session.commit()
    return submission


def mark_delivery_result(submission: ContactSubmission, result: DeliveryResult) -> None:
    if submission.delivery_status == "pending":
        submission.delivery_status = result.value
        db.session.commit()


def send_submission_notification(submission_id) -> DeliveryResult:
    return mailer.send_submission_notification(submission_id)


def update_contact_state(submission_id, state: str) -> ContactSubmission:
    if state not in CONTACT_STATES:
        raise ValueError("Unsupported contact state")
    submission = db.get_or_404(ContactSubmission, submission_id)
    submission.state = state
    submission.version += 1
    record_event(
        action="contact.state.changed",
        actor="admin",
        target_type="contact_submission",
        target_id=str(submission.id),
        metadata={"state": state},
    )
    db.session.commit()
    return submission


def _is_spam(command: ContactCommand) -> bool:
    if command.company_website:
        return True
    try:
        started_at = float(command.form_started_at)
    except ValueError:
        return True
    return time.time() - started_at < MIN_FORM_FILL_SECONDS
