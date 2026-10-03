from __future__ import annotations

import time

import pytest

from portfolio.contact.mailer import DeliveryResult
from portfolio.contact.models import ContactSubmission
from portfolio.extensions import db
from portfolio.integrations.models import IntegrationSecret


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


def test_admin_can_save_smtp_settings(authenticated_client, db_session):
    response = authenticated_client.post(
        "/admin/settings/email",
        data={
            "host": "smtp.example.com",
            "port": "587",
            "security": "starttls",
            "username": "mailer@example.com",
            "password": "secret-password",
            "sender": "contact@jeremyguill.me",
            "recipient": "jeremy@jeremyguill.me",
        },
    )

    assert response.status_code == 200
    assert b"SMTP settings saved" in response.data
    assert IntegrationSecret.query.filter_by(name="smtp_host").one() is not None
    password_secret = IntegrationSecret.query.filter_by(name="smtp_password").one()
    assert password_secret.key_hint == "word"


def test_blank_smtp_password_keeps_existing_password(authenticated_client, db_session):
    authenticated_client.post(
        "/admin/settings/email",
        data={
            "host": "smtp.example.com",
            "port": "587",
            "security": "starttls",
            "username": "mailer@example.com",
            "password": "secret-password",
            "sender": "contact@jeremyguill.me",
            "recipient": "jeremy@jeremyguill.me",
        },
    )
    first_password = IntegrationSecret.query.filter_by(name="smtp_password").one().encrypted_value

    authenticated_client.post(
        "/admin/settings/email",
        data={
            "host": "smtp2.example.com",
            "port": "465",
            "security": "ssl",
            "username": "mailer2@example.com",
            "password": "",
            "sender": "contact@jeremyguill.me",
            "recipient": "jeremy@jeremyguill.me",
        },
    )

    second_password = IntegrationSecret.query.filter_by(name="smtp_password").one().encrypted_value
    assert second_password == first_password


def test_admin_can_send_smtp_test_email(authenticated_client, db_session, monkeypatch):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            assert username == "mailer@example.com"
            assert password == "secret-password"

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr("portfolio.contact.mailer.smtplib.SMTP", FakeSMTP)
    authenticated_client.post(
        "/admin/settings/email",
        data={
            "host": "smtp.example.com",
            "port": "587",
            "security": "starttls",
            "username": "mailer@example.com",
            "password": "secret-password",
            "sender": "contact@jeremyguill.me",
            "recipient": "jeremy@jeremyguill.me",
        },
    )

    response = authenticated_client.post(
        "/admin/settings/email/test", data={"test_recipient": "test@example.com"}
    )

    assert response.status_code == 200
    assert b"Test email sent" in response.data
    assert sent_messages[0]["To"] == "test@example.com"


@pytest.fixture()
def authenticated_client(client):
    with client.session_transaction() as session:
        session["admin_session_id"] = "contact-admin"
    return client
