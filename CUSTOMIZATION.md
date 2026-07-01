# Customizing & extending OGTV Writer

OGTV Writer is the **Writer** role of the OnlyGainsTV studio. It's intentionally
small and built to grow — into other roles (Editor, Publisher, …) or with a real
LLM behind the generator. This is the map.

---

## Architecture at a glance

The Python import package is always `app/`, so most changes are additive — you
rarely move directories or rewrite imports.

```
config → service → route → template
```

- **config** ([app/config.py](app/config.py)) — the only place env vars are read.
- **domain** ([app/domain.py](app/domain.py)) — the controlled vocabulary
  (script + job statuses, tag kinds) and their display labels. The target model
  and output format now live inside each prompt file, not here.
- **services** — the only place that talks to the DB for an entity.
- **routes** — thin: parse input → call a service → render a template.
- **templates** — `pages/` extend `shell.html`; `partials/` are HTMX fragments.

---

## Branding & theme

- `APP_NAME`, `APP_DESCRIPTION`, `BRAND_NAME` in `.env` (and their defaults in
  [app/config.py](app/config.py)) — shown in the UI, page titles, PWA manifest.
- **Icon/logo:** replace [app/static/icons/icon.svg](app/static/icons/icon.svg).
- **Theme colors:** edit the CSS variables in
  [app/static/css/input.css](app/static/css/input.css) (`:root` light, `.dark`
  dark). The brand color drives buttons and active nav.

After editing templates/CSS, rebuild: `make css` (or `make css-watch` in dev).

---

## Tuning the generator

The generator calls **Google Gemini**. The pieces:

- **Prompts** — the briefs live as `.md` files in `app/static/prompts/`. The
  prompt file *is* the spec (role, task, constraints, output shape). Add or edit a
  prompt by dropping a file there; use `{{COUNT}}` where you want a per-job count
  injected.
- **[app/services/generation_service.py](app/services/generation_service.py)** —
  `assemble_prompt()` builds the final prompt (count substitution + addendum + the
  output contract) and `run_job()` drives a single job. The output contract (the
  `<<<SCRIPT n>>>` / `<<<TITLES>>>` / `<<<SUMMARY>>>` markers) lives here; the
  matching parser is [app/services/output_parser.py](app/services/output_parser.py).
- **[app/services/gemini_client.py](app/services/gemini_client.py)** — the only
  place that touches the SDK.
- **[app/services/job_worker.py](app/services/job_worker.py)** — the in-process
  worker that drains the queue.

### Using a different model or provider

Set `GEMINI_MODEL` in `.env` to switch Gemini models. To use a different provider
entirely, swap the body of `gemini_client.generate()` for your SDK call (and add
its key in [app/config.py](app/config.py) + `.env`). Routes, the worker, parsing,
the library, and export are all unaffected.

**Running two providers side by side** (STORY_025) is the worked example:
[app/services/local_client.py](app/services/local_client.py) is a second boundary
(an OpenAI-compatible endpoint on the DGX Spark) that raises the *same*
`RetryableError` / `GenerationError` as `gemini_client` — both are defined in
[app/services/llm_errors.py](app/services/llm_errors.py). `generation_service`
namespaces the picker values (`local:<name>`) and routes each job to the right client
in `_generate_with_retries()`, so adding a third provider is: a new `*_client.py`, a
branch in the router, and an entry in `model_options()`. Provider labels live in
[app/domain.py](app/domain.py) (`PROVIDER_LABELS`).

---

## Add a new entity (the five-file recipe)

The existing entities (`Job`, `Script`, `Tag`) are your blueprints. For an entity
`Thing`:

| File | Purpose |
|------|---------|
| `app/models/thing.py` | ORM model (+ register in `app/models/__init__.py`) |
| `app/schemas/thing.py` | `ThingCreate` / `ThingUpdate` / `ThingRead` |
| `app/services/thing_service.py` | CRUD functions taking a `Session` |
| `app/routes/thing.py` | `router` with page + HTMX partial routes |
| `app/templates/pages/thing.html` (+ `partials/thing/`) | UI |

Then:
- include the router in `app/main._register_routers()` (`>>> INCLUDE ... <<<`),
- add a nav item in `app/templates/partials/_sidebar.html` (`>>> ADD NAV ... <<<`).

**Closest blueprints:** copy `Tag` for lightweight inline CRUD; copy `Script` for
a list + detail/edit page with extra actions.

---

## Re-adding login (for multiple studio roles)

Login was intentionally removed — this is a single-operator internal tool. To
reintroduce it when you add other OnlyGainsTV roles:

1. Add a `User` model + `user_service` + password hashing (see git history of the
   original template, or any FastAPI session-auth example).
2. Reintroduce a `CurrentUser` dependency in
   [app/dependencies.py](app/dependencies.py) and add it to route signatures
   alongside `db` (every route already takes `db` the same way).
3. Add a `NotAuthenticated` handler in `app/main.py` that redirects browsers to
   `/login` and sends `HX-Redirect` for HTMX requests.

The `SessionMiddleware` is already wired (it powers flash messages today), so the
session cookie infrastructure is in place.

---

## Database & migrations

SQLite is the default and is perfect for a single-operator tool.

**Switch to Postgres:** set `DATABASE_URL` in `.env` and add the driver to
`pyproject.toml` (`"psycopg[binary]>=3.2"`).

**Migrations are managed with Alembic** (in `migrations/`):

- `make migration m="describe change"` — autogenerate a revision after editing a model.
- `make migrate` — apply migrations to head. It safely *adopts* a pre-migration DB
  (stamps it when it already matches the current schema; refuses a stale one rather than
  mis-stamping it).
- In dev the app **auto-applies migrations on startup** (`AUTO_MIGRATE=true`). In
  production set `AUTO_MIGRATE=false` and run `make migrate` as a deploy step — the app
  then only *verifies* the DB is at head and refuses to start if it's behind.

**Workflow for a schema change:** edit the model → `make migration m="..."` → review the
file in `migrations/versions/` → `make migrate` (or just restart in dev). Tests use
`create_all` directly (fast), and a drift test (`alembic check`) ensures every model
change has a matching migration.

---

## Checklist

```
[ ] Set APP_NAME / BRAND_NAME / SECRET_KEY in .env
[ ] Tuned theme colors + icon (input.css, icon.svg) and ran `make css`
[ ] Set GEMINI_API_KEY in .env (free key at aistudio.google.com)
[ ] Added your prompt files to app/static/prompts/
[ ] Updated scripts/seed.py for your real sample data
[ ] Added any new entities via the five-file recipe
[ ] Chose SQLite vs Postgres; set up migrations if needed
[ ] `make check` passes (lint + types + tests)
```

---

## Handy commands

```bash
make help        # list all tasks
make setup       # one-time: deps + browser + CSS + seed
make dev-all     # Tailwind watch + reloading server
make check       # lint + typecheck + tests (run before committing)
make seed        # (re)create sample data
make css         # build production CSS
make docker-run  # run in a container
```
