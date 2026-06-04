"""Fixtures for Playwright end-to-end tests.

Spins up the real ASGI app on a background uvicorn thread, seeds a known user
and item, and exposes the base URL. Browser fixtures (`page`, etc.) come from
pytest-playwright.

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

import pytest  # noqa: E402
import uvicorn  # noqa: E402

E2E_EMAIL = "e2e@example.com"
E2E_PASSWORD = "password123"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    """Start the app on a thread, seed data, and yield its base URL."""
    from app.database import Base, SessionLocal, engine
    from app.main import app
    from app.schemas.item import ItemCreate
    from app.services import item_service, user_service

    # Fresh schema + seed (once for the whole session).
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user_service.create_user(db, email=E2E_EMAIL, password=E2E_PASSWORD, name="E2E User")
        item_service.create_item(
            db, ItemCreate(title="Seeded item", description="from e2e seed", status="active")
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
