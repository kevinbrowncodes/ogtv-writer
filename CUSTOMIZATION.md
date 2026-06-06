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
  (target models, output formats, statuses, tag kinds) and their display labels.
  A new model or format is a one-line change here that the whole app picks up.
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

[app/services/generation_service.py](app/services/generation_service.py) is the
heart of the Generate workspace. Everything is data-driven:

- **`VARIATION_LENSES`** — the camera/lighting/mood combos that make each
  variation distinct. Add entries for more variety before they repeat.
- **`MODEL_GUIDANCE`** — per-model prompt style tokens + an "avoid" list. Tune
  these to match how Veo / Wan actually behave for your channel.
- **`FORMAT_TECH`** and the `_FORMAT_BUILDERS` (`_short_form`, `_cinematic`,
  `_montage`, `_narrated`, `_shot_list`) — the structure for each output format.

### Plugging in a real LLM

Keep `create_scripts()` as the seam. Swap the body of `build_script_body()` for
a Claude/OpenAI call:

1. Add the key in [app/config.py](app/config.py) (`anthropic_api_key: str = ""`)
   and `.env`, then add the SDK to `pyproject.toml` dependencies.
2. In `build_script_body()`, build your messages from `subject`, `target_model`,
   `output_format`, and the per-variation `lens`, and return the model's
   markdown. The template, routes, library, and export are unaffected.

---

## Add a new entity (the five-file recipe)

The existing entities (`Prompt`, `Script`, `ScriptTemplate`, `Tag`) are your
blueprints. For an entity `Thing`:

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

**Closest blueprints:** copy `Prompt` for a modal-based CRUD; copy `Script` for a
list + detail/edit page with extra actions.

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

**Adopt migrations (before you have data you care about):**

```bash
pip install alembic
alembic init migrations
# point migrations/env.py at app.database.Base.metadata and app.config DATABASE_URL
alembic revision --autogenerate -m "init"
alembic upgrade head
```

Then make `init_db()` in [app/database.py](app/database.py) a no-op (or
test-only). It currently runs `create_all` on startup for dev convenience.

---

## Checklist

```
[ ] Set APP_NAME / BRAND_NAME / SECRET_KEY in .env
[ ] Tuned theme colors + icon (input.css, icon.svg) and ran `make css`
[ ] Tuned the generator (lenses / model guidance / format builders)
[ ] (Optional) wired a real LLM into generation_service
[ ] Updated scripts/seed.py for your real prompts/templates
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
