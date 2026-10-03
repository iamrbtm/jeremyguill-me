from __future__ import annotations

import time

from sqlalchemy.exc import SQLAlchemyError

from portfolio import create_app
from portfolio.extensions import db
from portfolio.jobs.handlers import handle_job
from portfolio.jobs.services import WorkerResult, claim_due_jobs, fail_job, succeed_job
from portfolio.seo.automation import enqueue_daily_review_if_due


def run_once(worker_id: str, limit: int = 20) -> WorkerResult:
    try:
        enqueue_daily_review_if_due()
    except SQLAlchemyError:
        # The worker can start before the web entrypoint finishes migrations.
        db.session.rollback()
        pass
    jobs = claim_due_jobs(worker_id, limit=limit)
    succeeded = 0
    failed = 0
    for job in jobs:
        try:
            handle_job(job)
        except Exception as exc:
            fail_job(job, exc)
            failed += 1
        else:
            succeed_job(job)
            succeeded += 1
    return WorkerResult(processed=len(jobs), succeeded=succeeded, failed=failed)


def main() -> None:
    app = create_app()
    with app.app_context():
        while True:
            run_once("worker-main")
            time.sleep(60)


if __name__ == "__main__":
    main()
