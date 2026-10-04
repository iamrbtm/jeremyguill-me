from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from portfolio.contact.models import ContactSubmission
from portfolio.content.enums import PublicationState
from portfolio.content.models import Project, utcnow
from portfolio.extensions import db
from portfolio.jobs.models import Job
from portfolio.jobs.services import enqueue_unique
from portfolio.worker import main, run_once


def test_run_once_publishes_scheduled_project(db_session):
    project = Project(
        title="Scheduled",
        slug="scheduled",
        summary="Summary",
        source_markdown="Body",
        rendered_html="<p>Body</p>",
        state=PublicationState.SCHEDULED,
        publish_at=utcnow() - timedelta(minutes=1),
    )
    db.session.add(project)
    db.session.commit()
    enqueue_unique("publish", "project", project.id, utcnow())

    result = run_once("worker-a")

    db.session.refresh(project)
    assert result.succeeded == 1
    assert project.state == PublicationState.PUBLISHED
    assert project.published_at is not None


def test_run_once_sends_contact_notification(db_session, monkeypatch: pytest.MonkeyPatch):
    submission = ContactSubmission(
        name="Ada",
        email="ada@example.com",
        subject="Question",
        message="Message body",
    )
    db.session.add(submission)
    db.session.commit()
    enqueue_unique("email-notification", "contact_submission", submission.id, utcnow())

    def sent(submission_id):
        submission.delivery_status = "sent"
        db.session.commit()

    monkeypatch.setattr("portfolio.jobs.handlers.send_submission_notification", sent)

    result = run_once("worker-a")

    assert result.succeeded == 1
    assert submission.delivery_status == "sent"


def test_run_once_retries_failed_job(db_session):
    job = Job(kind="unknown", entity_type="project", entity_id=uuid.uuid4(), run_at=utcnow())
    db.session.add(job)
    db.session.commit()

    result = run_once("worker-a")

    db.session.refresh(job)
    assert result.failed == 1
    assert job.state == "pending"
    assert job.attempts == 1


def test_run_once_is_graceful_with_no_jobs(db_session):
    result = run_once("worker-a")

    assert result.processed == 0


def test_worker_main_creates_application_context(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def once(worker_id: str):
        calls.append(worker_id)
        raise KeyboardInterrupt

    monkeypatch.setattr("portfolio.worker.run_once", once)
    monkeypatch.setattr("portfolio.worker.time.sleep", lambda seconds: None)

    with pytest.raises(KeyboardInterrupt):
        main()

    assert calls == ["worker-main"]
