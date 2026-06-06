"""Apply and verify Alembic migrations programmatically.

Replaces the old ``create_all``-on-startup. On startup the app calls
:func:`upgrade_to_head` (dev) or :func:`verify_at_head` (production). The tricky case
is *adopting* a pre-Alembic database (tables present, no ``alembic_version``): we stamp
it at head only when it already matches the current schema, and otherwise refuse —
better a clear "reset once" than silently marking a stale DB as current.

Going forward (once a DB is stamped) every schema change is an incremental migration
that applies in place — no wipe.
"""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.config import get_settings
from app.database import Base

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent  # app/ -> repo root


def _config() -> Config:
    cfg = Config(str(_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    return cfg


def head_revision() -> str | None:
    return ScriptDirectory.from_config(_config()).get_current_head()


def db_revision() -> str | None:
    engine = create_engine(get_settings().database_url)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()


def is_at_head() -> bool:
    return db_revision() == head_revision()


def _present_tables() -> set[str]:
    engine = create_engine(get_settings().database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _schema_matches_models(present: set[str]) -> bool:
    """True if every model table exists with at least its model columns present."""
    engine = create_engine(get_settings().database_url)
    try:
        insp = inspect(engine)
        for table in Base.metadata.sorted_tables:
            if table.name not in present:
                return False
            db_cols = {c["name"] for c in insp.get_columns(table.name)}
            if not {c.name for c in table.columns}.issubset(db_cols):
                return False
        return True
    finally:
        engine.dispose()


def upgrade_to_head() -> None:
    """Bring the database to the latest revision, adopting an existing DB if safe."""
    cfg = _config()

    if db_revision() is not None:
        log.info("Upgrading database to head.")
        command.upgrade(cfg, "head")
        return

    present = _present_tables()
    model_tables = {t.name for t in Base.metadata.sorted_tables}
    if not (present & model_tables):
        # Truly fresh database — create everything from the migrations.
        log.info("Fresh database — running migrations to head.")
        command.upgrade(cfg, "head")
        return

    # Pre-Alembic DB with tables but no version: adopt only if it's already current.
    if _schema_matches_models(present):
        log.info("Adopting existing database — stamping at head.")
        command.stamp(cfg, "head")
        return

    raise RuntimeError(
        "Your database predates migrations and doesn't match the current schema. "
        "Reset it once, then it will migrate cleanly: `rm data/app.db && make migrate`."
    )


def verify_at_head() -> None:
    """Raise if the DB is behind head (production, where AUTO_MIGRATE is off)."""
    if not is_at_head():
        raise RuntimeError(
            "Database schema is behind the latest migration. "
            "Run `make migrate` before starting the app."
        )


if __name__ == "__main__":  # `python -m app.migrations_runner` / `make migrate`
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    upgrade_to_head()
