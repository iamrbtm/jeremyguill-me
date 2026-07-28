from __future__ import annotations

import time

from portfolio.contact.models import ContactSubmission


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


def test_honeypot_submission_is_discarded_without_revealing_detection(client):
    payload = valid_contact_payload(company_website="spam.example")

    response = client.post("/contact", data=payload)

    assert response.status_code == 302
    assert ContactSubmission.query.count() == 0


def test_too_fast_submission_is_discarded_without_revealing_detection(client):
    payload = valid_contact_payload(form_started_at=str(time.time()))

    response = client.post("/contact", data=payload)

    assert response.status_code == 302
    assert ContactSubmission.query.count() == 0


def test_oversized_message_is_rejected(client):
    payload = valid_contact_payload(message="x" * 5001)

    response = client.post("/contact", data=payload)

    assert response.status_code == 422
