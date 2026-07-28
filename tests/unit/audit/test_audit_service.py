from __future__ import annotations

from portfolio.audit import services as audit_services
from portfolio.audit.services import record_event, redact_metadata


def test_record_event_redacts_secret_values(db_session):
    event = record_event(
        action="nvidia.key.validated",
        actor="admin",
        target_type="integration",
        target_id="nvidia",
        metadata={"api_key": "nvapi-secret", "model": "writer"},
    )
    db_session.commit()

    assert event.metadata == {"api_key": "[REDACTED]", "model": "writer"}


def test_redaction_is_recursive():
    assert redact_metadata(
        {"outer": {"token": "secret", "safe": ["value", {"password": "hidden"}]}}
    ) == {"outer": {"token": "[REDACTED]", "safe": ["value", {"password": "[REDACTED]"}]}}


def test_audit_event_has_no_update_service():
    assert not hasattr(audit_services, "update_event")
