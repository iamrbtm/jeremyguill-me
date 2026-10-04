from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from flask import current_app
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy import func, select

from portfolio.content.models import BlogPost, Experience, Project
from portfolio.content.revisions import entity_type_for
from portfolio.extensions import db

PREVIEW_TTL = timedelta(minutes=30)


class InvalidPreview(ValueError):
    pass


class ExpiredPreview(ValueError):
    pass


@dataclass(frozen=True)
class DashboardView:
    project_count: int
    blog_count: int
    experience_count: int


@dataclass(frozen=True)
class PreviewClaims:
    entity_type: str
    entity_id: str
    version: int
    admin_session_id: str
    expires_at: datetime


def build_dashboard_view() -> DashboardView:
    return DashboardView(
        project_count=_count(Project),
        blog_count=_count(BlogPost),
        experience_count=_count(Experience),
    )


def create_preview_token(
    entity, admin_session_id: str, *, expires_at: datetime | None = None
) -> str:
    expiry = expires_at or datetime.now(UTC) + PREVIEW_TTL
    payload = {
        "entity_type": entity_type_for(entity),
        "entity_id": str(entity.id),
        "version": entity.version,
        "admin_session_id": admin_session_id,
        "expires_at": int(expiry.timestamp()),
    }
    return _serializer().dumps(payload)


def load_preview_token(token: str) -> PreviewClaims:
    try:
        payload = _serializer().loads(token)
    except BadSignature as exc:
        raise InvalidPreview("Preview signature is invalid") from exc
    try:
        claims = PreviewClaims(
            entity_type=str(payload["entity_type"]),
            entity_id=str(payload["entity_id"]),
            version=int(payload["version"]),
            admin_session_id=str(payload["admin_session_id"]),
            expires_at=datetime.fromtimestamp(int(payload["expires_at"]), UTC),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidPreview("Preview token is malformed") from exc
    if claims.expires_at <= datetime.now(UTC):
        raise ExpiredPreview("Preview URL has expired")
    return claims


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(current_app.secret_key, salt="admin-preview")


def _count(model) -> int:
    return int(db.session.execute(select(func.count()).select_from(model)).scalar_one())
