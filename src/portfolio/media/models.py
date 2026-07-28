from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from portfolio.content.models import EditableMixin
from portfolio.extensions import db


class MediaAsset(EditableMixin, db.Model):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(240), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(240), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    alt_text: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    caption: Mapped[str] = mapped_column(Text, default="", nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
