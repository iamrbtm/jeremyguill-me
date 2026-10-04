from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import or_, select

from portfolio.audit.services import record_event
from portfolio.content.models import utcnow
from portfolio.extensions import db

from .models import Job

RETRY_DELAYS = [
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(minutes=60),
]
MAX_ATTEMPTS = 5


@dataclass(frozen=True)
class WorkerResult:
    processed: int
    succeeded: int
    failed: int


def enqueue_unique(kind: str, entity_type: str, entity_id, run_at) -> Job:
    existing = db.session.execute(
        select(Job).where(
            Job.kind == kind,
            Job.entity_type == entity_type,
            Job.entity_id == entity_id,
            Job.state.in_(("pending", "running")),
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.run_at = run_at
        db.session.commit()
        return existing
    job = Job(kind=kind, entity_type=entity_type, entity_id=entity_id, run_at=run_at)
    db.session.add(job)
    db.session.commit()
    return job


def claim_due_jobs(worker_id: str, limit: int = 20) -> list[Job]:
    now = utcnow()
    jobs = db.session.execute(
        select(Job)
        .where(
            or_(
                (Job.state == "pending") & (Job.run_at <= now),
                (Job.state == "running") & (Job.lease_until < now),
            )
        )
        .order_by(Job.run_at)
        .with_for_update(skip_locked=True)
        .limit(limit)
    ).scalars().all()
    for job in jobs:
        job.state = "running"
        job.worker_id = worker_id
        job.lease_until = now + timedelta(minutes=5)
    db.session.commit()
    return list(jobs)


def succeed_job(job: Job) -> None:
    job.state = "completed"
    job.worker_id = None
    job.lease_until = None
    db.session.commit()


def fail_job(job: Job, exc: BaseException) -> None:
    job.attempts += 1
    job.worker_id = None
    job.lease_until = None
    if job.attempts >= MAX_ATTEMPTS:
        job.state = "failed"
        record_event(
            action="job.failed",
            actor="worker",
            target_type="job",
            target_id=str(job.id),
            metadata={"kind": job.kind, "error_code": exc.__class__.__name__},
        )
    else:
        job.state = "pending"
        delay = RETRY_DELAYS[min(job.attempts - 1, len(RETRY_DELAYS) - 1)]
        job.run_at = utcnow() + delay
    db.session.commit()
