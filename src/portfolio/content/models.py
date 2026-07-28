from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio.extensions import db

from .enums import PublicationState


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class EditableMixin(TimestampMixin):
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class SiteProfile(EditableMixin, db.Model):
    __tablename__ = "site_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(160), default="Jeremy Guill")
    headline: Mapped[str] = mapped_column(
        String(240), default="I build practical software for real-world problems."
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    email: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(160))


class Project(EditableMixin, db.Model):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    summary: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    source_markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rendered_html: Mapped[str] = mapped_column(Text, default="", nullable=False)
    state: Mapped[PublicationState] = mapped_column(
        Enum(PublicationState, native_enum=False), index=True, nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sort_position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hero_media_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media_assets.id")
    )


class BlogPost(EditableMixin, db.Model):
    __tablename__ = "blog_posts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    summary: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    source_markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rendered_html: Mapped[str] = mapped_column(Text, default="", nullable=False)
    state: Mapped[PublicationState] = mapped_column(
        Enum(PublicationState, native_enum=False), index=True, nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Experience(EditableMixin, db.Model):
    __tablename__ = "experience_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization: Mapped[str] = mapped_column(String(180), nullable=False)
    role: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    start_date: Mapped[str | None] = mapped_column(String(40))
    end_date: Mapped[str | None] = mapped_column(String(40))
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Education(EditableMixin, db.Model):
    __tablename__ = "education_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution: Mapped[str] = mapped_column(String(180), nullable=False)
    program: Mapped[str] = mapped_column(String(180), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Credential(EditableMixin, db.Model):
    __tablename__ = "credentials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(180))
    issued_at: Mapped[str | None] = mapped_column(String(40))
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ContentRevision(TimestampMixin, db.Model):
    __tablename__ = "content_revisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    source_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_html: Mapped[str] = mapped_column(Text, default="", nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(80), default="manual", nullable=False)


class Redirect(TimestampMixin, db.Model):
    __tablename__ = "redirects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    old_path: Mapped[str] = mapped_column(String(240), unique=True, index=True, nullable=False)
    new_path: Mapped[str] = mapped_column(String(240), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))


Project.revisions = relationship(
    ContentRevision,
    primaryjoin="and_(foreign(ContentRevision.entity_id) == Project.id, "
    "ContentRevision.entity_type == 'project')",
    order_by=ContentRevision.revision_number,
    viewonly=True,
)
