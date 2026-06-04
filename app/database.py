"""Database setup (SQLAlchemy 2.0, synchronous).

We use the *synchronous* SQLAlchemy API on purpose: it's simpler to read, works
great with FastAPI (which runs sync routes in a threadpool), and avoids the
sharp edges of async sessions. For most CRUD apps this is the right default.
Swap to async only if you have a measured need.

- `engine`       — the connection pool.
- `SessionLocal` — a factory; call it to get a Session.
- `Base`         — the declarative base every model inherits from.
- `get_db()`     — FastAPI dependency yielding a request-scoped Session.
- `init_db()`    — create tables (dev/test convenience; use migrations in prod).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()


def _make_engine_kwargs(database_url: str) -> dict:
    """SQLite needs a couple of special flags; other DBs use defaults."""
    if database_url.startswith("sqlite"):
        # Ensure the parent directory exists for file-based SQLite URLs.
        # (Skip for the in-memory ":memory:" URL used in tests.)
        if ":memory:" not in database_url:
            db_path = database_url.split("///", 1)[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return {
            # SQLite + threadpool: connections are shared across threads.
            "connect_args": {"check_same_thread": False},
        }
    # Pre-ping avoids stale connections on Postgres/MySQL behind load balancers.
    return {"pool_pre_ping": True}


engine = create_engine(
    settings.database_url,
    echo=False,  # logging_config controls SQL echo via the sqlalchemy logger
    **_make_engine_kwargs(settings.database_url),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped database session.

    Usage in a route:

        def my_route(db: Session = Depends(get_db)): ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables.

    Convenient for local dev and tests. For production schema changes, prefer a
    migration tool (e.g. Alembic) — see CUSTOMIZATION.md.
    """
    # Import models so they register on Base.metadata before create_all.
    from app import models  # noqa: F401  (side-effect import)

    log.info("Creating database tables (if not present)...")
    Base.metadata.create_all(bind=engine)
