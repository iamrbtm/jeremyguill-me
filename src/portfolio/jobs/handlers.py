from __future__ import annotations

from portfolio.contact.mailer import send_submission_notification
from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, utcnow
from portfolio.extensions import db
from portfolio.media.models import MediaAsset
from portfolio.media.variants import generate_variants

from .models import Job


def handle_job(job: Job) -> None:
    if job.kind == "publish":
        _handle_publish(job)
    elif job.kind in {"email-notification", "email-retry"}:
        send_submission_notification(job.entity_id)
    elif job.kind == "media-variant":
        asset = db.get_or_404(MediaAsset, job.entity_id)
        generate_variants(asset)
    else:
        raise ValueError(f"Unsupported job kind: {job.kind}")


def _handle_publish(job: Job) -> None:
    if job.entity_type == "project":
        entity = db.get_or_404(Project, job.entity_id)
    elif job.entity_type == "blog":
        entity = db.get_or_404(BlogPost, job.entity_id)
    else:
        raise ValueError("Unsupported publish entity")
    if entity.state == PublicationState.PUBLISHED:
        return
    if entity.state != PublicationState.SCHEDULED:
        raise ValueError("Only scheduled content can be published by the worker")
    entity.state = PublicationState.PUBLISHED
    entity.published_at = utcnow()
    entity.publish_at = None
    entity.version += 1
    db.session.commit()
