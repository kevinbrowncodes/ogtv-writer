"""Unit tests for the run-export zip builder."""

from __future__ import annotations

import io
import zipfile

from app.services import job_service, script_service


def _job(db, **kwargs):
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


def test_zip_bundles_scripts_and_titles(db):
    job = _job(db)
    job.titles = "T1\nT2"
    db.commit()
    script_service.create_generated_scripts(db, job, ["Alpha", "Beta"], title_base="Scene")
    scripts = script_service.list_for_job(db, job.id)

    data, filename = job_service.build_run_zip(job, scripts)

    archive = zipfile.ZipFile(io.BytesIO(data))
    assert archive.namelist() == ["script1.txt", "script2.txt", "titles.txt"]
    assert archive.read("script1.txt").decode() == "Alpha"
    assert archive.read("script2.txt").decode() == "Beta"
    assert archive.read("titles.txt").decode() == "T1\nT2"
    assert filename == f"video-review-prompt_job{job.id}.zip"


def test_zip_single_script_no_titles(db):
    job = _job(db)
    script_service.create_generated_scripts(db, job, ["Solo"], title_base="Scene")
    scripts = script_service.list_for_job(db, job.id)

    data, _ = job_service.build_run_zip(job, scripts)

    archive = zipfile.ZipFile(io.BytesIO(data))
    assert archive.namelist() == ["script1.txt"]
    assert archive.read("script1.txt").decode() == "Solo"
