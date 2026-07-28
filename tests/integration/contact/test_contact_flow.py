from __future__ import annotations

import time

import pytest

from portfolio.contact.mailer import DeliveryResult
from portfolio.contact.models import ContactSubmission
from portfolio.extensions import db


def valid_contact_payload(**overrides):
    payload = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "subject": "Project question",
        "message": "Can we discuss a workflow system?",
        "company_website": "",
        "form_started_at": str(time.time() - 10),
    }
    payload.update(overrides)
    return payload


def test_valid_submission_is_persisted_before_notification(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "portfolio.contact.services.send_submission_notification",
        lambda submission_id: DeliveryResult.SENT,
    )

    response = client.post("/contact", data=valid_contact_payload())

    assert response.status_code == 302
    submission = ContactSubmission.query.one()
    assert submission.email == "ada@example.com"
    assert submission.delivery_status == "sent"


def test_submission_survives_email_failure(client, db_session, monkeypatch):
    def fail_delivery(submission_id):
        submission = db.session.get(ContactSubmission, submission_id)
        submission.delivery_status = "failed"
        submission.delivery_error_code = "smtp-error"
        return DeliveryResult.FAILED

    monkeypatch.setattr("portfolio.contact.services.send_submission_notification", fail_delivery)

    response = client.post("/contact", data=valid_contact_payload())

    assert response.status_code == 302
    submission = ContactSubmission.query.one()
    assert submission.delivery_status == "failed"
    assert submission.delivery_error_code == "smtp-error"


def test_invalid_contact_payload_returns_422(client):
    response = client.post("/contact", data=valid_contact_payload(email="not-an-email"))

    assert response.status_code == 422
    assert b"Valid reply email is required" in response.data


def test_admin_can_mark_contact_read(authenticated_client, db_session):
    submission = ContactSubmission(
        name="Ada",
        email="ada@example.com",
        subject="Question",
        message="Message",
    )
    db_session.add(submission)
    db_session.commit()

    response = authenticated_client.post(
        f"/admin/contact/{submission.id}/state", data={"state": "read"}
    )

    assert response.status_code == 302
    db_session.refresh(submission)
    assert submission.state == "read"


@pytest.fixture()
def authenticated_client(client):
    with client.session_transaction() as session:
        session["admin_session_id"] = "contact-admin"
    return client
