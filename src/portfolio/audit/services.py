from __future__ import annotations

from collections.abc import Mapping

from portfolio.audit.models import AuditEvent
from portfolio.audit.types import JSONValue
from portfolio.extensions import db

SENSITIVE_KEYS = {"api_key", "authorization", "cookie", "password", "secret", "token"}


def redact_json(value: JSONValue) -> JSONValue:
    if isinstance(value, Mapping):
        return redact_metadata(value)
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    return value


def redact_metadata(value: Mapping[str, JSONValue]) -> dict[str, JSONValue]:
    return {
        key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else redact_json(raw)
        for key, raw in value.items()
    }


def record_event(
    *,
    action: str,
    actor: str,
    target_type: str,
    target_id: str | None = None,
    metadata: Mapping[str, JSONValue] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        action=action,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        metadata_json=redact_metadata(metadata or {}),
    )
    db.session.add(event)
    db.session.flush()
    return event
