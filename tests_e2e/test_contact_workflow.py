from __future__ import annotations

import time

from portfolio.contact.mailer import DeliveryResult
from portfolio.contact.models import ContactSubmission


def test_contact_submission_persists_and_redirects(client, monkeypatch):
    monkeypatch.setattr(
        "portfolio.contact.services.send_submission_notification",
        lambda submission_id: DeliveryResult.SKIPPED,
    )

    response = client.post(
        "/contact",
        data={
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "subject": "Workflow help",
            "message": "Please help with a workflow system.",
            "company_website": "",
            "form_started_at": str(time.time() - 10),
        },
    )

    assert response.status_code == 302
    assert ContactSubmission.query.count() == 1
