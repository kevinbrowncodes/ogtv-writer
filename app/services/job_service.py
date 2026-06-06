"""Job business logic — the generation queue.

CRUD for jobs. STORY_002 only needs create/list/get/delete; the worker (STORY_003)
adds status transitions on top of this.
"""

from __future__ import annotations

import io
import re
import zipfile

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.script import Script


def create_job(
    db: Session,
    *,
    prompt_slug: str,
    prompt_filename: str,
    addendum: str,
    count: int | None,
    image_path: str,
    image_filename: str,
    model: str = "",
    source_dir: str = "",
) -> Job:
    """Create a queued job."""
    job = Job(
        prompt_slug=prompt_slug,
        prompt_filename=prompt_filename,
        addendum=addendum,
        count=count,
        image_path=image_path,
        image_filename=image_filename,
        model=model,
        source_dir=source_dir,
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


def _slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value.lower()).strip()
    return re.sub(r"[-\s]+", "-", value)[:60] or "run"


def build_run_zip(job: Job, scripts: list[Script]) -> tuple[bytes, str]:
    """Bundle a job's scripts (+ titles.txt, if any) into a .zip.

    Returns ``(zip_bytes, filename)``. Each script is ``scriptN.txt`` in order,
    body-only; the filename is derived from the prompt + job id.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, script in enumerate(scripts, start=1):
            archive.writestr(f"script{index}.txt", script.body)
        if job.titles.strip():
            archive.writestr("titles.txt", job.titles)
    base = _slugify((job.prompt_filename or job.prompt_slug).removesuffix(".md"))
    return buffer.getvalue(), f"{base}_job{job.id}.zip"
