# STORY_008 — Schema changes apply to an existing database without wiping it

> Epic: — (infrastructure follow-on) · Status: Done

**As** the OnlyGainsTV operator, **I want** schema changes to apply to my existing
`data/app.db` automatically, **so that** pulling new work never greets me with a
`no such column` 500 and a "delete your database and reseed" chore.

Today `init_db()` runs `create_all` on startup, which **creates missing tables but
never alters existing ones**. So every schema change (a new column on `Job`/`Script`)
silently leaves a long-lived dev DB behind, and the next query 500s. This adopts
**Alembic migrations** so changes are versioned and applied to existing DBs, and adds
a guard so drift fails loudly instead of cryptically.

## Approach (confirm before implementing)

- **Adopt Alembic.** Migrations live in `migrations/`; `migrations/env.py` reads
  `Base.metadata` (for autogenerate) and `DATABASE_URL` from `app.config`.
- **Dev "just works":** on startup the app **upgrades the DB to head automatically**
  (replacing `create_all`), so an existing DB is migrated in place — no wipe. A config
  flag (`AUTO_MIGRATE`, default on outside production) controls this; in production you
  run `alembic upgrade head` as a deploy step and the app only **verifies** it's at
  head, failing loudly if not.
- **Tests stay fast:** unit/integration/e2e keep using `create_all`/`drop_all` on a
  throwaway DB — they don't run migrations. A dedicated test asserts the migrations and
  the models haven't drifted apart.
- Decision to confirm: **auto-migrate on startup in dev** (proposed — matches today's
  zero-step ergonomics) vs **explicit `make migrate` only**.

## Acceptance Criteria

- [x] Running the app against an **existing older DB** brings it to the current schema
      automatically (dev) — the `no such column` 500 cannot recur from a stale local DB.
- [x] `make migrate` runs `alembic upgrade head`; `make migration m="..."` autogenerates
      a revision. `make setup` migrates instead of relying on `create_all`.
- [x] A **baseline migration** reproduces the current schema (jobs, scripts, tags); a
      fresh DB reaches the full schema via `alembic upgrade head`.
- [x] Introducing Alembic to an **already-current** DB (no `alembic_version` table but
      tables present, e.g. the operator's current `app.db`) is handled — it's stamped at
      head, not erroneously re-created.
- [x] In production (`AUTO_MIGRATE` off), the app **refuses to start / fails loudly with
      a clear "run migrations" message** if the DB is behind head — never a per-query 500.
- [x] A test fails if a model changed without a matching migration (no model↔migration drift).
- [x] Tests still run on `create_all` (fast); the full suite stays green.

## Technical Notes

- **Dependency:** add `alembic>=1.13` to `pyproject.toml`.
- **Init:** `alembic init migrations`. In `migrations/env.py`: set
  `target_metadata = app.database.Base.metadata`, import all models so they're
  registered, and pull the URL from `app.config.get_settings().database_url` (don't
  hardcode `alembic.ini`'s `sqlalchemy.url`). Enable `render_as_batch=True` so SQLite
  can do `ALTER` via batch mode (SQLite can't drop/alter columns natively).
- **Baseline:** `alembic revision --autogenerate -m "baseline schema"`, review it, commit.
- **Replace `init_db`:** add `app/migrations_runner.py` (or extend `database.py`):
  - `current_head()` / `db_revision()` via Alembic's `ScriptDirectory` + `MigrationContext`.
  - `upgrade_to_head()` runs `alembic upgrade head` programmatically (`alembic.command`).
  - **Adopt-on-existing logic:** if there's no `alembic_version` table but the core
    tables already exist → `stamp head` (don't re-create); otherwise `upgrade head`.
  - `app/main.py` lifespan: when `not is_testing` → if `settings.auto_migrate`,
    `upgrade_to_head()`; else verify `db_revision() == current_head()` and raise a clear
    `RuntimeError("Database is behind — run `make migrate`")` if not. `init_db()` becomes
    test-only (conftest still calls `create_all`).
- **Config:** add `auto_migrate: bool` (default `not is_production`) to `Settings` + `.env.example`.
- **Makefile:** `migrate` (`alembic upgrade head`), `migration` (`alembic revision --autogenerate -m "$(m)"`); `setup` calls `migrate` (drop the implicit create_all reliance).
- **Docs:** README (setup/run + a "migrations" note) and CUSTOMIZATION (replace the
  "adopt migrations later" section with "this is how migrations work now").
- **`.gitignore`:** keep `data/*` ignored; **commit** `migrations/` (versions are code).

## Testing Plan

~60/30/10 — heavier on integration since this is wiring/ops.

- **Unit:**
  - `upgrade_to_head()` on a fresh temp SQLite file creates the expected tables
    (jobs/scripts/tags) and records a revision.
  - The adopt-on-existing path: given a DB with tables but no `alembic_version`, it
    stamps head rather than erroring.
  - **No-drift check:** `alembic check` (or autogenerate in offline mode) reports **no
    pending changes** against `Base.metadata` — fails if a model changed without a migration.
- **Integration:**
  - Simulate a stale DB (create the *old* schema, e.g. a `scripts` table missing
    `job_id`), run `upgrade_to_head()`, then `GET /dashboard` → 200 (the original bug,
    now fixed by migration).
  - With `AUTO_MIGRATE` off and a behind DB, app startup raises the clear error.
- **e2e:** unchanged (fresh `create_all` DB) — just confirm the suite stays green; no new
  e2e needed since this is infra, not a user-facing flow. *(Justified per §3: no visible UI change.)*

## Estimated Complexity

**L** — Alembic wiring (`env.py`, batch mode for SQLite), the adopt-on-existing logic,
the startup runner + prod verify path, and the no-drift test. Mostly one-time plumbing;
the payoff is no more wipe-and-reseed.
