"""Integration test for job retries (STORY_012).

A job whose first Gemini call hits a transient error still ends up ``done`` after a
retry, writes its scripts, and the detail page surfaces the attempt count. Gemini is
mocked and the backoff is patched to zero, so nothing is called live or slept on.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services import gemini_client, generation_service, job_service, job_worker


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(generation_service, "_sleep", lambda _seconds: None)
    yield
    get_settings.cache_clear()


def test_retried_job_completes_and_shows_attempts(client, db, tmp_path, monkeypatch):
    img = tmp_path / "01.jpg"
    img.write_bytes(b"img-bytes")
    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] < 2:
            raise gemini_client.RetryableError("rate limited")
        return "<<<SCRIPT 1>>>hello<<<END SCRIPT>>>"

    monkeypatch.setattr(gemini_client, "generate", flaky)

    job = job_service.create_job(
        db,
        prompt_slug="video-review-prompt",
        prompt_filename="video-review-prompt.md",
        addendum="",
        count=None,
        image_path=str(img),
        image_filename="01.jpg",
    )

    processed = job_worker.process_next_job(db)  # claim → run (with the retry inside)
    assert processed is not None

    resp = client.get(f"/jobs/{job.id}")
    assert resp.status_code == 200
    assert "Done" in resp.text
    assert "2 attempts" in resp.text  # the detail page surfaces the retry count
