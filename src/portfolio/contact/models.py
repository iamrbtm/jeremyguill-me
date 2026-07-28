from __future__ import annotations

import uuid

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from portfolio.content.models import EditableMixin
from portfolio.extensions import db


class ContactSubmission(EditableMixin, db.Model):
    __tablename__ = "contact_submissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(40), default="unread", nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    delivery_error_code: Mapped[str | None] = mapped_column(String(80))
