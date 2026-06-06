"""Job business logic — the generation queue.

CRUD for jobs. STORY_002 only needs create/list/get/delete; the worker (STORY_003)
adds status transitions on top of this.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.job import Job


def create_job(
    db: Session,
    *,
    prompt_slug: str,
    prompt_filename: str,
    addendum: str,
    count: int | None,
    image_path: str,
    image_filename: str,
) -> Job:
    """Create a queued job."""
    job = Job(
        prompt_slug=prompt_slug,
        prompt_filename=prompt_filename,
        addendum=addendum,
        count=count,
        image_path=image_path,
        image_filename=image_filename,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_jobs(db: Session, *, status: str | None = None, limit: int = 200) -> list[Job]:
    """Return jobs, newest first, optionally filtered by status."""
    stmt = select(Job).order_by(Job.created_at.desc(), Job.id.desc())
    if status:
        stmt = stmt.where(Job.status == status)
    return list(db.scalars(stmt.limit(limit)).all())


def count_jobs(db: Session, *, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(Job)
    if status:
        stmt = stmt.where(Job.status == status)
    return db.scalar(stmt) or 0


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def delete_job(db: Session, job: Job) -> None:
    db.delete(job)
    db.commit()
