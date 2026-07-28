from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from portfolio.content.models import EditableMixin, TimestampMixin
from portfolio.extensions import db


class IntegrationSecret(EditableMixin, db.Model):
    __tablename__ = "integration_secrets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    encrypted_value: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_hint: Mapped[str | None] = mapped_column(String(32))


class AiRevisionSuggestion(TimestampMixin, db.Model):
    __tablename__ = "ai_revision_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    suggestion_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
