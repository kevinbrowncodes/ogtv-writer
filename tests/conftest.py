"""Shared pytest fixtures for unit + integration tests.

IMPORTANT: environment variables are set BEFORE importing the app, because
`app.config` and `app.database` read settings at import time. This points the
tests at a dedicated SQLite file and a test secret.

OGTV Writer has no login, so there's no auth/user fixture — `client` can hit
every route directly.
"""

from __future__ import annotations

import os

# --- Configure the test environment (must run before importing `app`) --------
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DEBUG", "false")
# Force-blank the Gemini key so tests NEVER make a live call, even though a real
# key may live in .env. Tests that exercise generation set their own + mock the client.
os.environ["GEMINI_API_KEY"] = ""
# Point shoot discovery at a non-existent dir so /jobs/new is deterministic (no real
# data/logline shoots leak in); folder tests monkeypatch SOURCE_ROOT to a tmp dir.
os.environ["SOURCE_ROOT"] = "data/_test_shoots_none"

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import prompt_catalog  # noqa: E402

# Decouple the suite from the user-editable app/static/prompts/ folder — point the
# catalog at fixed fixtures so renaming/editing real prompts never breaks tests.
prompt_catalog.PROMPTS_DIR = Path(__file__).resolve().parent / "fixtures" / "prompts"


@pytest.fixture(autouse=True)
def _fresh_database(request):
    """Give every test a clean schema (create tables, drop them after).

    Skipped for e2e tests — those run against a live server with its own
    session-scoped database setup (see tests/e2e/conftest.py).
    """
    if request.node.get_closest_marker("e2e"):
        yield
        return
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_gemini_status_cache():
    """Clear the process-wide Gemini status cache around every test.

    ``generation_service.gemini_status()`` caches a successful probe for the process;
    without this, a test that mocks a working key would leak its cached models into a
    later test that expects the no-key warning. (Harmless for e2e — the live server
    runs in its own process.)
    """
    from app.services import generation_service

    generation_service._status_cache = None
    yield
    generation_service._status_cache = None


@pytest.fixture
def db() -> Session:
    """A database session for arrange/assert steps in tests."""
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    """A TestClient. Using it as a context manager runs the app lifespan."""
    with TestClient(app) as test_client:
        yield test_client
