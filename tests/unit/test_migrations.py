"""Unit tests for the Alembic migration runner.

These point the runner at throwaway SQLite files (not the suite's test.db) and run
real Alembic operations against them.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect

from app import migrations_runner
from app.config import get_settings
from app.database import Base


@pytest.fixture(autouse=True)
def _settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _point_at(tmp_path: Path, monkeypatch) -> Path:
    db = tmp_path / "m.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    get_settings.cache_clear()
    return db


def _tables(db: Path) -> set[str]:
    engine = create_engine(f"sqlite:///{db}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_fresh_db_upgrades_to_head(tmp_path, monkeypatch):
    db = _point_at(tmp_path, monkeypatch)
    migrations_runner.upgrade_to_head()
    assert {"jobs", "scripts", "tags", "alembic_version"} <= _tables(db)
    assert migrations_runner.is_at_head()


def test_adopts_existing_current_schema_by_stamping(tmp_path, monkeypatch):
    db = _point_at(tmp_path, monkeypatch)
    # A pre-Alembic DB created via create_all: current schema, no alembic_version.
    engine = create_engine(f"sqlite:///{db}")
    Base.metadata.create_all(engine)
    engine.dispose()
    assert migrations_runner.db_revision() is None

    migrations_runner.upgrade_to_head()  # should stamp, not error

    assert migrations_runner.is_at_head()


def test_refuses_stale_mismatched_schema(tmp_path, monkeypatch):
    db = _point_at(tmp_path, monkeypatch)
    # A pre-Alembic DB whose scripts table is missing the newer columns.
    engine = create_engine(f"sqlite:///{db}")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE jobs (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE tags (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE scripts (id INTEGER PRIMARY KEY, title TEXT)")
    engine.dispose()

    with pytest.raises(RuntimeError, match="predates migrations"):
        migrations_runner.upgrade_to_head()


def test_no_model_migration_drift(tmp_path, monkeypatch):
    # Bring a fresh DB to head, then `alembic check` must find no pending changes.
    _point_at(tmp_path, monkeypatch)
    migrations_runner.upgrade_to_head()
    command.check(migrations_runner._config())  # raises if a model drifted from migrations
