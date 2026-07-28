from __future__ import annotations

import uuid

from sqlalchemy import JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from portfolio.content.models import TimestampMixin
from portfolio.extensions import db


class AuditEvent(TimestampMixin, db.Model):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(120))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)

    def __getattribute__(self, name: str):
        if name == "metadata":
            return object.__getattribute__(self, "metadata_json")
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "metadata":
            name = "metadata_json"
        super().__setattr__(name, value)
