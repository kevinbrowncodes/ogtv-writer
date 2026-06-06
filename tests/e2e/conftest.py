"""Fixtures for Playwright end-to-end tests.

Spins up the real ASGI app on a background uvicorn thread, seeds a known prompt
and script, and exposes the base URL. Browser fixtures (`page`, etc.) come from
pytest-playwright. There is no login in OGTV Writer, so tests hit pages directly.

Run these with:  make test-e2e   (i.e. `pytest -m e2e`)
First-time setup: `playwright install chromium`.
"""

from __future__ import annotations

import os
import socket
import threading
import time
from collections.abc import Iterator

# Use a dedicated database + secret for e2e (set before importing the app).
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/e2e.db")
os.environ.setdefault("SECRET_KEY", "e2e-secret-key")
# Blank the Gemini key so the live e2e server never calls the API (worker is off
# under tests anyway); the model picker falls back to the default.
os.environ["GEMINI_API_KEY"] = ""

import pytest  # noqa: E402
import uvicorn  # noqa: E402


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    """Start the app on a thread, seed data, and yield its base URL."""
    from app.database import Base, SessionLocal, engine
    from app.main import app
    from app.models.job import Job
    from app.schemas.script import ScriptCreate
    from app.services import script_service

    # Fresh schema + seed (once for the whole session).
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        script_service.create_script(
            db, ScriptCreate(title="Seeded script", body="# Seeded\nbody", status="ready")
        )
        # A completed job with split scripts, for the results view (worker is off under tests).
        done_job = Job(
            prompt_slug="video-review-prompt",
            prompt_filename="video-review-prompt.md",
            status="done",
            image_path="data/uploads/seed.png",
            image_filename="seed.png",
            result_raw="seeded raw response",
            titles="Seed title 1\nSeed title 2",
            summary="Seeded scene summary.",
        )
        db.add(done_job)
        db.commit()
        db.refresh(done_job)
        script_service.create_generated_scripts(
            db, done_job, ["Seeded script alpha", "Seeded script beta"], title_base="Seeded Job"
        )

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for the port to accept connections.
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("e2e server failed to start in time")

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)
