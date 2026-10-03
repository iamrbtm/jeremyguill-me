from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from portfolio.content.models import TimestampMixin
from portfolio.extensions import db


class SeoAutomationSettings(TimestampMixin, db.Model):
    __tablename__ = "seo_automation_settings"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default="default")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nvidia_model: Mapped[str] = mapped_column(
        String(160), default="meta/llama-3.1-70b-instruct", nullable=False
    )
    daily_request_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    publish_policy: Mapped[str] = mapped_column(String(40), default="metadata_only", nullable=False)
    weekly_summary_recipient: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    last_daily_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_weekly_summary_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SeoTargetQuery(TimestampMixin, db.Model):
    __tablename__ = "seo_target_queries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    state: Mapped[str] = mapped_column(String(40), default="active", index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="nvidia", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SeoActionLog(TimestampMixin, db.Model):
    __tablename__ = "seo_action_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="ok", index=True, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80), index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    target_query: Mapped[str | None] = mapped_column(String(180))
    model: Mapped[str | None] = mapped_column(String(160))
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
