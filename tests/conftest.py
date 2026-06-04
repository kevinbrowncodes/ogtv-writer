"""Shared pytest fixtures for unit + integration tests.

IMPORTANT: environment variables are set BEFORE importing the app, because
`app.config` and `app.database` read settings at import time. This points the
tests at a dedicated SQLite file and a test secret.
"""

from __future__ import annotations

import os

# --- Configure the test environment (must run before importing `app`) --------
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DEBUG", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import user_service  # noqa: E402

TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"


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


@pytest.fixture
def user(db: Session) -> User:
    """A persisted, active user for tests that need an account."""
    return user_service.create_user(
        db, email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD, name="Test User"
    )


@pytest.fixture
def auth_client(client: TestClient, user: User) -> TestClient:
    """A TestClient that has already logged in (session cookie set)."""
    resp = client.post(
        "/login",
        data={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    return client
