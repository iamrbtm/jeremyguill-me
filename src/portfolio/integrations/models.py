from __future__ import annotations

import uuid

from sqlalchemy import LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from portfolio.content.models import EditableMixin
from portfolio.extensions import db


class IntegrationSecret(EditableMixin, db.Model):
    __tablename__ = "integration_secrets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    encrypted_value: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_hint: Mapped[str | None] = mapped_column(String(32))
