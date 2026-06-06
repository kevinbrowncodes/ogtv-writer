"""In-process background worker that drains the job queue.

A single daemon thread polls for the oldest queued job, marks it running, and runs
it via ``generation_service``. Sequential (concurrency = 1) to respect Gemini rate
limits and cost. Started/stopped from ``app.main``'s lifespan; it is never started
during tests — the unit of work, :func:`process_next_job`, is called directly.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.job import Job
from app.services.generation_service import run_job

log = logging.getLogger(__name__)

POLL_SECONDS = 2.0

_stop = threading.Event()
_thread: threading.Thread | None = None


def process_next_job(db: Session) -> Job | None:
    """Claim the oldest queued job, mark it running, and run it. Returns it, or None."""
    job = db.scalars(
        select(Job)
        .where(Job.status == "queued")
        .order_by(Job.created_at.asc(), Job.id.asc())
        .limit(1)
    ).first()
    if job is None:
        return None
    job.status = "running"
    job.started_at = datetime.now(UTC)
    db.commit()
    run_job(db, job)
    return job


def _loop() -> None:
    while not _stop.is_set():
        processed: Job | None = None
        try:
            with SessionLocal() as db:
                processed = process_next_job(db)
        except Exception:
            log.exception("Job worker iteration failed")
        if processed is None:
            _stop.wait(POLL_SECONDS)


def start() -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="job-worker", daemon=True)
    _thread.start()
    log.info("Job worker started")


def stop() -> None:
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=5)
    log.info("Job worker stopped")
