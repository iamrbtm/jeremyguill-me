from __future__ import annotations

from datetime import timedelta

import pytest

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project, utcnow
from portfolio.extensions import db
from portfolio.jobs.services import claim_due_jobs, enqueue_unique, fail_job, succeed_job


@pytest.fixture()
def project(db_session):
    project = Project(title="Queued", slug="queued", summary="", state=PublicationState.DRAFT)
    db.session.add(project)
    db.session.commit()
    return project


def test_enqueue_unique_does_not_duplicate_active_job(db_session, project):
    first = enqueue_unique("publish", "project", project.id, utcnow())
    second = enqueue_unique("publish", "project", project.id, utcnow() + timedelta(minutes=1))

    assert first.id == second.id
    assert second.run_at > first.created_at


def test_completed_job_allows_new_job(db_session, project):
    first = enqueue_unique("publish", "project", project.id, utcnow())
    succeed_job(first)
    second = enqueue_unique("publish", "project", project.id, utcnow())

    assert first.id != second.id


def test_two_workers_cannot_claim_same_job(db_session, project):
    due_job = enqueue_unique("publish", "project", project.id, utcnow())

    claimed_a = claim_due_jobs("worker-a")
    claimed_b = claim_due_jobs("worker-b")

    assert due_job in claimed_a
    assert due_job not in claimed_b
    assert due_job.state == "running"


def test_expired_lease_can_be_reclaimed(db_session, project):
    due_job = enqueue_unique("publish", "project", project.id, utcnow())
    claim_due_jobs("worker-a")
    due_job.lease_until = utcnow() - timedelta(seconds=1)
    db.session.commit()

    claimed = claim_due_jobs("worker-b")

    assert due_job in claimed
    assert due_job.worker_id == "worker-b"


def test_fail_job_uses_bounded_retries_then_dead_state(db_session, project):
    job = enqueue_unique("publish", "project", project.id, utcnow())
    claim_due_jobs("worker-a")

    for _ in range(4):
        fail_job(job, RuntimeError("temporary"))
        assert job.state == "pending"
        job.run_at = utcnow()
        claim_due_jobs("worker-a")
    fail_job(job, RuntimeError("dead"))

    assert job.state == "failed"
    assert job.attempts == 5
