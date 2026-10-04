from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import timedelta
from email.message import EmailMessage

from flask import current_app
from sqlalchemy import select

from portfolio.audit.services import record_event
from portfolio.contact.mailer import load_smtp_settings, send_message
from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, SiteProfile, utcnow
from portfolio.extensions import db
from portfolio.integrations.openai import (
    OpenAIClient,
    SeoOptimizationRequest,
    SeoOptimizationResult,
)
from portfolio.integrations.services import IntegrationNotConfigured, openai_api_key
from portfolio.jobs.services import enqueue_unique

from .models import SeoActionLog, SeoAutomationSettings, SeoTargetQuery

SEO_DAILY_JOB_ID = uuid.uuid5(uuid.NAMESPACE_URL, "https://jeremyguill.me/jobs/seo-daily-review")


@dataclass(frozen=True)
class SeoRunResult:
    reviewed: int
    updated: int
    skipped: int


def load_settings() -> SeoAutomationSettings:
    settings = db.session.get(SeoAutomationSettings, "default")
    if settings is None:
        settings = SeoAutomationSettings(
            id="default",
            nvidia_model=current_app.config.get("OPENAI_MODEL", "gpt-4o-mini"),
        )
        db.session.add(settings)
        db.session.commit()
    return settings


def save_settings(form) -> SeoAutomationSettings:
    settings = load_settings()
    settings.enabled = str(form.get("enabled", "")).lower() in {"1", "true", "on", "yes"}
    settings.nvidia_model = _clean_model(str(form.get("openai_model", "")).strip())
    settings.daily_request_limit = _coerce_int(str(form.get("daily_request_limit", "3")), 1, 25)
    publish_policy = str(form.get("publish_policy", "metadata_only")).strip()
    if publish_policy not in {"metadata_only", "publish_visible"}:
        raise ValueError("Unsupported SEO publish policy")
    settings.publish_policy = publish_policy
    settings.weekly_summary_recipient = str(form.get("weekly_summary_recipient", "")).strip()[:255]
    db.session.commit()
    record_event(
        action="seo.settings.saved",
        actor="admin",
        target_type="seo",
        target_id="default",
        metadata={
            "enabled": settings.enabled,
            "model": settings.nvidia_model,
            "daily_request_limit": settings.daily_request_limit,
            "publish_policy": settings.publish_policy,
        },
    )
    return settings


def enqueue_daily_review_if_due() -> None:
    settings = load_settings()
    if not settings.enabled:
        return
    now = utcnow()
    if settings.last_daily_run_at and settings.last_daily_run_at.date() == now.date():
        return
    enqueue_unique("seo-daily-review", "seo", SEO_DAILY_JOB_ID, now)


def run_daily_review(client: OpenAIClient | None = None) -> SeoRunResult:
    settings = load_settings()
    if not settings.enabled:
        _log("seo.daily.skipped", status="skipped", details={"reason": "disabled"})
        return SeoRunResult(reviewed=0, updated=0, skipped=1)
    try:
        api_key = openai_api_key()
    except IntegrationNotConfigured:
        _log("seo.daily.skipped", status="skipped", details={"reason": "openai-not-configured"})
        return SeoRunResult(reviewed=0, updated=0, skipped=1)

    client = client or OpenAIClient(base_url=os.getenv("OPENAI_BASE_URL"))
    reviewed = 0
    updated = 0
    skipped = 0
    for entity_type, entity in _reviewable_entities(limit=settings.daily_request_limit):
        reviewed += 1
        try:
            result = client.optimize_seo(
                SeoOptimizationRequest(
                    api_key=api_key,
                    model=settings.nvidia_model,
                    entity_type=entity_type,
                    title=entity.display_name if entity_type == "profile" else entity.title,
                    summary=entity.summary or "",
                    body=getattr(entity, "source_markdown", "") or entity.summary or "",
                    current_target_query=entity.seo_target_query or "",
                )
            )
        except Exception as exc:
            skipped += 1
            _log(
                "seo.entity.failed",
                status="failed",
                entity_type=entity_type,
                entity_id=entity.id,
                model=settings.nvidia_model,
                details={
                    "error_code": exc.__class__.__name__,
                    "error_message": str(exc)[:300],
                },
            )
            continue
        if _apply_result(entity_type, entity, result, settings):
            updated += 1
        else:
            skipped += 1

    settings.last_daily_run_at = utcnow()
    db.session.commit()
    _log(
        "seo.daily.completed",
        model=settings.nvidia_model,
        details={"reviewed": reviewed, "updated": updated, "skipped": skipped},
    )
    maybe_send_weekly_summary(settings)
    return SeoRunResult(reviewed=reviewed, updated=updated, skipped=skipped)


def recent_logs(limit: int = 25) -> list[SeoActionLog]:
    return list(
        db.session.execute(
            select(SeoActionLog).order_by(SeoActionLog.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )


def active_targets(limit: int = 25) -> list[SeoTargetQuery]:
    return list(
        db.session.execute(
            select(SeoTargetQuery)
            .where(SeoTargetQuery.state == "active")
            .order_by(SeoTargetQuery.priority.desc(), SeoTargetQuery.updated_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def maybe_send_weekly_summary(settings: SeoAutomationSettings | None = None) -> None:
    settings = settings or load_settings()
    if not settings.weekly_summary_recipient:
        return
    now = utcnow()
    if settings.last_weekly_summary_at and settings.last_weekly_summary_at > now - timedelta(
        days=7
    ):
        return
    smtp_settings = load_smtp_settings()
    if not smtp_settings.is_configured:
        _log(
            "seo.weekly_summary.skipped",
            status="skipped",
            details={"reason": "smtp-not-configured"},
        )
        return
    logs = recent_logs(limit=10)
    message = EmailMessage()
    message["From"] = smtp_settings.sender
    message["To"] = settings.weekly_summary_recipient
    message["Subject"] = "JeremyGuill.me weekly SEO automation summary"
    body_lines = ["Weekly autonomous SEO summary", ""]
    for log in logs:
        body_lines.append(f"{log.created_at:%Y-%m-%d}: {log.action} ({log.status})")
    message.set_content("\n".join(body_lines))
    send_message(message, smtp_settings)
    settings.last_weekly_summary_at = now
    db.session.commit()
    _log("seo.weekly_summary.sent", details={"recipient": settings.weekly_summary_recipient})


def _reviewable_entities(limit: int):
    entities: list[tuple[str, object]] = []
    profile = db.session.execute(select(SiteProfile).limit(1)).scalar_one_or_none()
    if profile is not None:
        entities.append(("profile", profile))
    projects = db.session.execute(
        select(Project)
        .where(Project.state == PublicationState.PUBLISHED)
        .order_by(Project.seo_last_reviewed_at.isnot(None), Project.seo_last_reviewed_at)
        .limit(limit)
    ).scalars()
    entities.extend(("project", project) for project in projects)
    remaining = max(0, limit - len(entities))
    if remaining:
        posts = db.session.execute(
            select(BlogPost)
            .where(BlogPost.state == PublicationState.PUBLISHED)
            .order_by(BlogPost.seo_last_reviewed_at.isnot(None), BlogPost.seo_last_reviewed_at)
            .limit(remaining)
        ).scalars()
        entities.extend(("blog", post) for post in posts)
    return entities[:limit]


def _apply_result(
    entity_type: str,
    entity: SiteProfile | Project | BlogPost,
    result: SeoOptimizationResult,
    settings: SeoAutomationSettings,
) -> bool:
    changed = False
    primary_query = result.target_queries[0] if result.target_queries else ""
    if result.seo_title and result.seo_title != entity.seo_title:
        entity.seo_title = result.seo_title
        changed = True
    if result.seo_description and result.seo_description != entity.seo_description:
        entity.seo_description = result.seo_description
        changed = True
    if primary_query and primary_query != entity.seo_target_query:
        entity.seo_target_query = primary_query
        changed = True
    if settings.publish_policy == "publish_visible" and result.visible_summary:
        if result.visible_summary != entity.summary:
            entity.summary = result.visible_summary
            changed = True
    entity.seo_last_reviewed_at = utcnow()
    for position, query in enumerate(result.target_queries):
        _upsert_target(
            query,
            entity_type,
            entity.id,
            priority=100 - position * 10,
            notes=result.rationale,
        )
    if changed:
        entity.version += 1
    db.session.commit()
    _log(
        "seo.entity.reviewed",
        entity_type=entity_type,
        entity_id=entity.id,
        target_query=primary_query or None,
        model=settings.nvidia_model,
        details={
            "changed": changed,
            "publish_policy": settings.publish_policy,
            "rationale": result.rationale,
        },
    )
    return changed


def _upsert_target(
    query: str, entity_type: str, entity_id: uuid.UUID, *, priority: int, notes: str
) -> None:
    target = db.session.execute(
        select(SeoTargetQuery).where(
            SeoTargetQuery.query == query,
            SeoTargetQuery.entity_type == entity_type,
            SeoTargetQuery.entity_id == entity_id,
        )
    ).scalar_one_or_none()
    if target is None:
        target = SeoTargetQuery(query=query, entity_type=entity_type, entity_id=entity_id)
        db.session.add(target)
    target.priority = priority
    target.state = "active"
    target.notes = notes
    target.last_evaluated_at = utcnow()


def _log(
    action: str,
    *,
    status: str = "ok",
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    target_query: str | None = None,
    model: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    db.session.add(
        SeoActionLog(
            action=action,
            status=status,
            entity_type=entity_type,
            entity_id=entity_id,
            target_query=target_query,
            model=model,
            details=details or {},
        )
    )
    db.session.commit()


def _clean_model(model: str) -> str:
    return model[:160] or current_app.config.get("OPENAI_MODEL", "gpt-4o-mini")


def _coerce_int(value: str, minimum: int, maximum: int) -> int:
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"Value must be between {minimum} and {maximum}")
    return number


def run_blog_seo(post: "BlogPost", client: OpenAIClient | None = None) -> SeoOptimizationResult:
    settings = load_settings()
    try:
        api_key = openai_api_key()
    except IntegrationNotConfigured:
        _log(
            "seo.blog.skipped",
            entity_type="blog",
            entity_id=post.id,
            status="skipped",
            details={"reason": "openai-not-configured"},
        )
        raise
    client = client or OpenAIClient(base_url=os.getenv("OPENAI_BASE_URL"))
    result = client.optimize_seo(
        SeoOptimizationRequest(
            api_key=api_key,
            model=settings.nvidia_model,
            entity_type="blog",
            title=post.title,
            summary=post.summary or "",
            body=post.source_markdown or post.summary or "",
            current_target_query=post.seo_target_query or "",
        )
    )
    _apply_blog_result(post, result, settings)
    return result


def _apply_blog_result(
    post: "BlogPost", result: SeoOptimizationResult, settings: SeoAutomationSettings
) -> bool:
    changed = False
    primary_query = result.target_queries[0] if result.target_queries else ""
    if result.seo_title and result.seo_title != post.seo_title:
        post.seo_title = result.seo_title
        changed = True
    if result.seo_description and result.seo_description != post.seo_description:
        post.seo_description = result.seo_description
        changed = True
    if primary_query and primary_query != post.seo_target_query:
        post.seo_target_query = primary_query
        changed = True
    if result.visible_summary and result.visible_summary != post.summary:
        post.summary = result.visible_summary
        changed = True
    post.seo_last_reviewed_at = utcnow()
    for position, query in enumerate(result.target_queries):
        _upsert_target(
            query,
            "blog",
            post.id,
            priority=100 - position * 10,
            notes=result.rationale,
        )
    if changed:
        post.version += 1
    db.session.commit()
    _log(
        "seo.blog.reviewed",
        entity_type="blog",
        entity_id=post.id,
        target_query=primary_query or None,
        model=settings.nvidia_model,
        details={"changed": changed, "rationale": result.rationale},
    )
    return changed
