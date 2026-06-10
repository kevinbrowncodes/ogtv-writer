# BUG_002 — Alembic is required to boot but is missing from the declared dependencies

> Status: Resolved

## Summary

The app imports `alembic` unconditionally at startup, but `alembic` is not listed in
[pyproject.toml](../../pyproject.toml). A clean install (`make setup` / a fresh venv)
therefore produces an app that crashes on import with `ModuleNotFoundError: No module
named 'alembic'`. It only ever "worked" because Alembic happened to be present in an
older, hand-installed venv.

## Steps to Reproduce

1. Recreate the virtualenv from scratch: `rm -rf .venv && python3 -m venv .venv`.
2. Install per the documented setup: `.venv/bin/python -m pip install -e ".[dev]"`.
3. Import the app: `.venv/bin/python -c "from app.main import app"` (or run `make dev`).

## Expected vs Actual Behaviour

- **Expected:** a fresh install per the README/`make setup` yields a bootable app.
- **Actual:** import fails:
  ```
  File "app/migrations_runner.py", line 18, in <module>
      from alembic import command
  ModuleNotFoundError: No module named 'alembic'
  ```
  (Surfaced in this case after Homebrew removed `python@3.13`, forcing a venv rebuild
  that exposed the undeclared dependency.)

## Root Cause

Alembic was introduced in [STORY_008](../story/STORY_008_schema_changes_apply_without_wiping.md)
along with [`alembic.ini`](../../alembic.ini), [`app/migrations_runner.py`](../../app/migrations_runner.py),
and the `make migrate` target — but the corresponding runtime dependency was never added
to the `dependencies` list in [pyproject.toml](../../pyproject.toml). Because
[`app/main.py`](../../app/main.py) imports `migrations_runner` at module load (which imports
`alembic`), the package is a hard runtime requirement, not an optional one. The declared
dependency set drifted from what the code actually imports.

## Acceptance Criteria

- [x] `alembic` is declared in `pyproject.toml` `dependencies` (not a dev-only extra).
- [x] A fresh `pip install -e ".[dev]"` installs Alembic, and `from app.main import app` succeeds without a manual `pip install alembic`.

---

## Resolution

Added `"alembic>=1.13"` to the runtime `dependencies` in
[pyproject.toml](../../pyproject.toml) (it is imported unconditionally on startup, so it
belongs alongside `sqlalchemy`, not in the `dev` extra). Verified: a clean venv rebuilt on
Python 3.14 with `pip install -e ".[dev]"` now pulls Alembic (1.18.4), `from app.main
import app` imports cleanly, and `make dev` boots and applies migrations to head. No new
test layer added — this is a packaging-metadata fix; the existing migrations runner and
its coverage already exercise Alembic at runtime, and the regression is in the dependency
manifest rather than in app code.
