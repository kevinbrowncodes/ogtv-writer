"""Integration tests for run export (.zip) and the copy controls."""

from __future__ import annotations

import io
import zipfile

from app.services import job_service, script_service


def _done_job(db, *, titles=""):
    job = job_service.create_job(
        db,
        prompt_slug="video-review-prompt",
        prompt_filename="video-review-prompt.md",
        addendum="",
        count=None,
        image_path="data/uploads/x.png",
        image_filename="x.png",
    )
    job.status = "done"
    job.titles = titles
    db.commit()
    script_service.create_generated_scripts(db, job, ["Alpha", "Beta"], title_base="Scene")
    return job


def test_export_zip_downloads(client, db):
    job = _done_job(db, titles="T1\nT2")
    resp = client.get(f"/jobs/{job.id}/export.zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "attachment" in resp.headers["content-disposition"]
    assert ".zip" in resp.headers["content-disposition"]

    archive = zipfile.ZipFile(io.BytesIO(resp.content))
    assert archive.namelist() == ["script1.txt", "script2.txt", "titles.txt"]
    assert archive.read("script2.txt").decode() == "Beta"


def test_export_unknown_job_404(client):
    assert client.get("/jobs/999/export.zip").status_code == 404


def test_detail_has_copy_and_download_controls(client, db):
    job = _done_job(db)
    resp = client.get(f"/jobs/{job.id}")
    assert resp.status_code == 200
    assert "data-copy=" in resp.text  # per-script copy buttons
    assert f"/jobs/{job.id}/export.zip" in resp.text  # download link
