"""Unit tests for the job service (CRUD against a temp DB)."""

from __future__ import annotations

from app.services import job_service


def _create(db, **kwargs):
    defaults = {
        "prompt_slug": "video-review-prompt",
        "prompt_filename": "video-review-prompt.md",
        "addendum": "",
        "count": None,
        "image_path": "data/uploads/x.png",
        "image_filename": "x.png",
    }
    defaults.update(kwargs)
    return job_service.create_job(db, **defaults)


def test_create_job_is_queued(db) -> None:
    job = _create(db)
    assert job.id is not None
    assert job.status == "queued"
    assert job.prompt_slug == "video-review-prompt"
    assert job.count is None


def test_create_job_stores_count(db) -> None:
    job = _create(db, prompt_slug="260601-0000_wip-prompt", count=8)
    assert job.count == 8


def test_list_jobs_newest_first(db) -> None:
    a = _create(db, image_filename="a.png")
    b = _create(db, image_filename="b.png")
    jobs = job_service.list_jobs(db)
    assert [j.id for j in jobs] == [b.id, a.id]


def test_list_jobs_filters_by_status(db) -> None:
    _create(db)
    assert job_service.list_jobs(db, status="queued")
    assert job_service.list_jobs(db, status="done") == []


def test_get_and_delete(db) -> None:
    job = _create(db)
    fetched = job_service.get_job(db, job.id)
    assert fetched is not None and fetched.id == job.id
    job_service.delete_job(db, job)
    assert job_service.get_job(db, job.id) is None


def test_count_jobs(db) -> None:
    _create(db)
    _create(db)
    assert job_service.count_jobs(db) == 2
    assert job_service.count_jobs(db, status="queued") == 2
    assert job_service.count_jobs(db, status="failed") == 0


# --- STORY_033 / BUG_007: orphaned running jobs recover -----------------------


def _mark_running(db, job) -> None:
    job.status = "running"
    db.commit()


def test_recover_fails_orphaned_running_job(db) -> None:
    job = _create(db)
    _mark_running(db, job)

    recovered = job_service.recover_orphaned_running_jobs(db)

    assert recovered == 1
    db.refresh(job)
    assert job.status == "failed"
    assert job.error == job_service.ORPHANED_RUNNING_ERROR
    assert job.finished_at is not None


def test_recover_leaves_other_states_untouched(db) -> None:
    queued = _create(db, image_filename="q.png")
    done = _create(db, image_filename="d.png")
    done.status = "done"
    db.commit()

    assert job_service.recover_orphaned_running_jobs(db) == 0
    db.refresh(queued)
    db.refresh(done)
    assert queued.status == "queued" and queued.error == ""
    assert done.status == "done" and done.error == ""


def test_recover_is_idempotent(db) -> None:
    job = _create(db)
    _mark_running(db, job)
    assert job_service.recover_orphaned_running_jobs(db) == 1
    assert job_service.recover_orphaned_running_jobs(db) == 0
