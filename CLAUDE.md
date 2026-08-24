# CLAUDE.md

> Project context, workflow, and guardrails for AI coding assistants working in the `ogtv-writer` repository.

---

## 1. Project Overview

**OGTV Writer** is the **Writer** role of the **OnlyGainsTV** video-studio workflow: a
**server-rendered web app** for one operator (you) to turn markdown prompts into
structured, model-ready scripts for AI video generation — **Google Veo**, **Wan**,
and similar text-to-video / image-to-video systems — then organize, edit, tag, and
export them as clean Markdown.

```
Prompt (markdown) → Generate N variations → Edit / tag / status → Copy / export .md → Veo / Wan
```

- **Web framework:** **FastAPI** (app factory in [app/main.py](app/main.py))
- **Templating:** **Jinja2**, server-rendered HTML
- **Interactivity:** **HTMX** (AJAX/partials via HTML attributes) — *no* React/Vue/Svelte, *no* bundler
- **Styling:** **Tailwind CSS** (the only Node usage is compiling CSS)
- **Data:** **SQLAlchemy 2.0 (synchronous) + SQLite** (Postgres-ready via `DATABASE_URL`)
- **Generator:** **offline & deterministic** — no API key, no network (a rotating cinematic "lens" over per-model/format patterns). The single seam for a real LLM is [app/services/generation_service.py](app/services/generation_service.py).
- **Tests:** **pytest** (unit + integration) + **Playwright** (e2e)
- **PWA:** manifest + service worker (installable, offline app-shell)
- **Primary language:** Python 3.11+
- **Repo:** https://github.com/kevinbrowncodes/ogtv-writer

This is an **internal, single-operator tool** — **there is no login**. It runs as a
normal web server (`uvicorn app.main:app`); "shipping" means landing working code on
`develop` (CI green). It can also run in Docker (see §5).

> **Entities:** the app is built around four — **Prompt**, **Script**, **ScriptTemplate**, **Tag** — each following the same five-file recipe (see §6b). A `Script` moves through a lifecycle: `draft → ready → used → archived` (marking it **used** stamps a used-date).

---

## 2. Repo Structure

```
ogtv-writer/
├── CLAUDE.md                  ← you are here
├── README.md                  ← setup + usage guide
├── CUSTOMIZATION.md           ← how to extend (new entity, real LLM, re-add login, migrations)
├── pyproject.toml             ← project metadata + tooling (ruff, mypy, pytest); installed editable
├── package.json               ← Tailwind build scripts only (no JS framework, no bundler)
├── tailwind.config.js         ← Tailwind content globs + theme
├── Makefile                   ← all developer tasks (run `make help`)
├── Dockerfile / docker-compose.yml / .dockerignore
├── .env.example               ← template; copy → .env (git-ignored)
├── .github/workflows/ci.yml   ← CI: quality (ruff+mypy+pytest) + e2e (Playwright)
│
├── app/                       ← the import package (always `app/`)
│   ├── main.py                ← app factory; routers mounted in _register_routers()
│   ├── config.py              ← THE only place env vars are read (pydantic Settings, get_settings())
│   ├── domain.py              ← controlled vocab + labels (models, formats, statuses, tag kinds)
│   ├── database.py            ← SQLAlchemy engine/SessionLocal/Base + get_db() + init_db()
│   ├── dependencies.py        ← DbSession annotation (NO auth — internal tool)
│   ├── templating.py          ← Jinja2 setup, flash(), is_htmx(), toast_trigger(), domain globals
│   ├── logging_config.py      ← logging setup
│   ├── models/                ← ORM models: job, preference, script, tag (+ base mixins)
│   ├── schemas/               ← Pydantic validation per entity
│   ├── services/              ← business logic / all DB access (incl. generation_service)
│   ├── routes/                ← prompt_catalog, jobs, shoots, scripts, tags, pages, settings, health, pwa, common
│   ├── templates/
│   │   ├── base.html          ← page shell that pages extend
│   │   ├── pages/             ← dashboard, prompts, scripts, script_detail, script_edit, generate, templates, tags, settings
│   │   ├── partials/          ← HTMX fragments (per-feature: _list, _row, _form, _status_badge, …)
│   │   └── errors/            ← 404.html / 500.html
│   └── static/                ← css/ (input.css source → app.css built), js/app.js, icons/, service-worker.js
│
├── scripts/seed.py            ← idempotent sample OnlyGainsTV data (prompts/scripts/templates/tags)
├── tests/
│   ├── conftest.py            ← sets test env BEFORE importing app; fresh DB per test; client fixture
│   ├── unit/                  ← services against a temp DB (generation, prompt, script)
│   ├── integration/           ← routes via TestClient (HTML + HTMX headers): dashboard, prompts, scripts, generate, templates, tags
│   └── e2e/                   ← Playwright browser flows (live server)
├── data/                      ← SQLite db + generated output (git-ignored except .gitkeep)
└── docs/                      ← ticket workflow (see §3): epic/ story/ backlog/ bug/
```

> **Git-ignored, never commit:** `.env`, `data/*` (except `data/.gitkeep`), `*.db`,
> `app/static/css/app.css` (a build artifact — CI/`make css` regenerates it), `.venv/`,
> `node_modules/`. These hold secrets, local DB state, or regenerable output.

---

## 3. How Features Are Built (IMPORTANT)

> **No story file → no code. No exceptions.**

1. Every new feature **must have a story file** in [docs/story/](docs/story/) **before any code is written**.
2. Story files follow the format in [docs/story/_TEMPLATE.md](docs/story/_TEMPLATE.md): a user-story sentence, **Acceptance Criteria** checklist, **Technical Notes**, **Testing Plan**, **Estimated Complexity**.
3. Stories are implemented **one at a time**, with the story file used as the spec.
4. **Never write code for a feature that does not yet have a story file.** If the user requests work without a story, draft the story first, get approval, then implement.
5. **Every story must include a Testing Plan that calls out which test layers apply: unit, integration, and e2e.** Follow a roughly 70/20/10 pyramid:
   - **Unit** (`pytest`, `tests/unit/`) — services and pure functions against a temp DB: generation logic (lenses / format builders / `build_script_body()` output shape), `domain.parse_tags`, slugify, CRUD in `*_service.py`. Default: **required** for any new service function or pure helper.
   - **Integration** (`pytest` + FastAPI `TestClient`, `tests/integration/`) — routes end-to-end: status codes, **rendered HTML assertions**, **HTMX headers** (`HX-Request` handling, `HX-Trigger` toasts, OOB swaps), redirects, and `422` validation paths. Default: **required** for any new or changed route.
   - **e2e** (`pytest -m e2e` + Playwright, `tests/e2e/`) — a real browser drives a live server through a user-visible flow (dashboard, create-prompt modal, the generate flow, the script library). Default: **required** when a story adds or changes a visible workflow. (Excluded from the default `pytest` run; use `make test-e2e`.)
   - If a layer is not applicable, the Testing Plan must explicitly say so and explain why. **"No tests needed" is not an acceptable answer without justification.**
6. A story is not **Done** until its Testing Plan tests are written and passing locally (`make check` green, plus `make test-e2e` if the story touched a flow), and `make lint`/`mypy` are clean.

> **No live, paid API calls in automated tests.** The generator is offline and
> deterministic today, so tests never touch the network. If you later wire a real LLM
> into [`build_script_body()`](app/services/generation_service.py), **mock the client at
> the boundary** — never make live model calls (which cost money) from tests.

---

## 3b. How Bugs Are Tracked

> Bug tickets live in [docs/bug/](docs/bug/) as `BUG_NNN_short_slug.md`. Use a **bug ticket** when existing behaviour is broken. Use a **story** when new behaviour is being added.

- Bug numbers are three-digit zero-padded: `BUG_001`, `BUG_002`, …
- Each ticket follows [docs/bug/_TEMPLATE.md](docs/bug/_TEMPLATE.md): **Summary**, **Steps to Reproduce**, **Expected vs Actual Behaviour**, **Root Cause**, **Acceptance Criteria**, **Status**.
- A bug ticket is not a substitute for a story — once a bug is understood and the fix requires meaningful new code, create a story that references the bug ticket.
- Bug tickets are never deleted; mark them resolved by setting **Status** to `Resolved` and adding a **Resolution** note at the bottom.

---

## 3c. How Epics & Backlog Are Tracked

> Epics group related stories ([docs/epic/](docs/epic/), `EPIC_NNN_slug.md`). Backlog items hold not-yet-ready work ([docs/backlog/](docs/backlog/), `BACKLOG_NNN_slug.md`).

- Numbers are three-digit zero-padded (`EPIC_001`, `BACKLOG_001`, …).
- Backlog items stay lightweight: summary, user impact, rough scope, dependencies, open questions, priority (see [docs/backlog/_TEMPLATE.md](docs/backlog/_TEMPLATE.md)).
- **Do not implement directly from epics or backlog items.** Once an item is clear and prioritized, convert it to a `docs/story/STORY_NNN_*.md` before any code is written, then remove/archive the backlog item and link to the new story.

---

## 4. Dev Workflow

- **This is a solo repo; `develop` is the trunk.** Work and push directly to `develop` once the gates below pass; merge `develop → main` for releases. CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on pushes to **both** `main` and `develop` and on PRs.
- **Always work inside the project virtualenv:**
  ```bash
  cd /Users/kevinbrown/Documents/GitHub/kevinbrowncodes/ogtv-writer
  # Copy the env template (defaults work as-is for local dev)
  cp .env.example .env
  python3 -m venv .venv && source .venv/bin/activate
  # Install deps (editable + dev) + Playwright browser + CSS + seed data
  make setup
  ```
- **Run the app:**
  ```bash
  # uvicorn with hot reload → http://localhost:8000 (no login; lands on the dashboard)
  make dev
  # second terminal: rebuild Tailwind on template changes
  make css-watch
  # both at once
  make dev-all
  ```
- **Before every commit, these gates must pass in order** (cheapest first, so failures surface fast):
  1. `make lint` — Ruff lint **and** `ruff format --check .` (CI fails on unformatted code; run `make format` to fix).
  2. `make typecheck` — `mypy app`.
  3. `make test` — `pytest` (unit + integration; Playwright e2e excluded here).
  4. `make test-e2e` — Playwright, **when the change touches a user-visible flow**.
  5. `git add -A && git commit && git push origin develop` — only after 1–4 are green.

  Steps 1–3 are bundled as **`make check`**. **Never commit if a step fails** — fix locally, re-run from the failed step, then commit.
- **Don't commit the built CSS.** [app/static/css/app.css](app/static/css/app.css) is git-ignored and rebuilt by `make css` / CI; edit [app/static/css/input.css](app/static/css/input.css) instead and rebuild.
- **One commit + push per completed story or bug.** As soon as a unit of work passes its gate and the §3 "Done" criteria, commit and push it — don't batch several stories into one end-of-session commit. Name the unit in the message (e.g. `STORY_004: …` or `Fix BUG_002: …`).
- **Prefer CLI tools** (git, the Makefile targets, `python -m scripts.seed`) over asking the user to click around.
- Always give a clear summary after making changes — what changed, what commands you ran, and the outcome.

---

## 5. Stack Reference

| Layer            | Detail                                                                                   |
| ---------------- | ---------------------------------------------------------------------------------------- |
| Language         | Python 3.11+ (CI runs 3.12; dev on 3.13)                                                  |
| Web framework    | FastAPI (`app.main:app`), app factory in [app/main.py](app/main.py)                       |
| Templating       | Jinja2 server-rendered HTML via [app/templating.py](app/templating.py)                    |
| Interactivity    | HTMX (partials + `HX-*` headers); vanilla JS in [app/static/js/app.js](app/static/js/app.js) |
| Styling          | Tailwind CSS — `npm run css:build` / `css:dev`; source [input.css](app/static/css/input.css) → built `app.css` |
| Data             | SQLAlchemy 2.0 **synchronous** + SQLite; `DATABASE_URL` swaps to Postgres                 |
| Config           | `.env` (copied from [.env.example](.env.example)) → pydantic Settings in [app/config.py](app/config.py) |
| AI generator     | Offline & deterministic in [app/services/generation_service.py](app/services/generation_service.py); LLM seam = `build_script_body()` |
| Linting/format   | Ruff (`make lint` / `make format`), config in [pyproject.toml](pyproject.toml)            |
| Type checking    | mypy (`make typecheck`)                                                                   |
| Testing          | `pytest` (unit + integration, e2e excluded by default) + Playwright e2e (`pytest -m e2e`); config in [pyproject.toml](pyproject.toml); tests in [tests/](tests/) |
| PWA              | manifest + [app/static/service-worker.js](app/static/service-worker.js)                   |
| Container        | [Dockerfile](Dockerfile) + [docker-compose.yml](docker-compose.yml)                       |
| CI               | [.github/workflows/ci.yml](.github/workflows/ci.yml) — quality + e2e on push to main/develop and PRs |
| Entry point      | `make dev` (uvicorn `--reload`) or `make run` / Docker                                    |
| Repo             | https://github.com/kevinbrowncodes/ogtv-writer                                            |

---

## 6. Key Rules

1. **Always read the relevant story file before writing any code.** The story is the spec.
2. **Never modify a story file's content after it has been implemented.** Acceptance-criteria checkboxes may be flipped `[ ]` → `[x]`, but the prose stays frozen. New requirements → new story.
3. **Follow the `STORY_NNN_short_slug.md` naming convention.** Three-digit zero-padded numbers, snake_case slugs. **Story numbers must match implementation order within their epic** — the lowest-numbered story ships first; renumber unimplemented stories before any code if priorities shift. **The `# STORY_NNN — …` / `# EPIC_NNN — …` headings must use plain-English titles a non-engineer understands at a glance** — no raw function names, no jargon, no backtick-wrapped symbols. Good: `"Scripts can be exported as a downloadable .md file"`. Bad: `` "`scripts_export` Content-Disposition edge case" ``.
4. **The golden rule of layering — keep routes thin.** A route does: parse input → call a service → render a template. **All DB access lives in `app/services/`.** **All env access lives in [app/config.py](app/config.py)** (`get_settings()`). All controlled vocabulary + labels live in [app/domain.py](app/domain.py). Don't reach across these seams.
5. **Test one story at a time.** Never implement multiple stories in a single session. Land one, verify, then start the next.
6. **Never commit secrets or generated state.** `.env`, `data/*`, `*.db`, the built `app/static/css/app.css`, `.venv/`, and `node_modules/` are git-ignored — keep them that way. **Any new setting goes in [app/config.py](app/config.py) (typed, with a default) AND [.env.example](.env.example) (with a safe placeholder)** — never only in a local `.env`.
7. **No live, paid API calls — ever — from tests.** The generator is offline today. If you wire a real LLM in, mock it at the boundary (Key Rule for cost safety).
8. **Every story ships with tests** per §3 — unit + integration, plus e2e when a flow changes. New code with no tests (and no documented reason a layer is N/A) is incomplete.

---

## 6b. FastAPI / HTMX / Web Conventions

- **Add a feature area = the five-file recipe** (the existing entities are blueprints; see [CUSTOMIZATION.md](CUSTOMIZATION.md)). For an entity `Thing`:
  | File | Purpose |
  |------|---------|
  | `app/models/thing.py` | ORM model (+ register in [app/models/__init__.py](app/models/__init__.py)) |
  | `app/schemas/thing.py` | `ThingCreate` / `ThingUpdate` / `ThingRead` |
  | `app/services/thing_service.py` | CRUD functions taking a `Session` |
  | `app/routes/thing.py` | `router` with page + HTMX partial routes |
  | `app/templates/pages/thing.html` (+ `partials/thing/`) | UI |
  Then **mount the router** in [`_register_routers()`](app/main.py) (`>>> INCLUDE NEW FEATURE ROUTERS BELOW <<<`) and **add a nav item** in [app/templates/partials/_sidebar.html](app/templates/partials/_sidebar.html). Copy `Prompt` for modal-based CRUD; copy `Script` for a list + detail/edit page with extra actions.
- **Full page vs HTMX partial.** A full page renders `pages/x.html` (which extends `base.html`); an HTMX fragment renders a template under `partials/` that does **not** extend `base.html`, so only the swapped fragment comes back. Detect HTMX with `is_htmx(request)` / the `is_htmx` template flag (the `HX-Request` header).
- **Toasts & flashes.** For one-shot messages on a redirect, use `flash(request, msg, category)`; for an HTMX response, attach `headers=toast_trigger(msg, category)` (an `HX-Trigger` that [app.js](app/static/js/app.js) turns into a toast). Both live in [app/templating.py](app/templating.py).
- **Validation.** Validate form input through the entity's Pydantic schema; on `ValidationError`, re-render the form with `field_errors(exc)` (see [app/routes/common.py](app/routes/common.py)) and a `422` status — don't let raw exceptions escape.
- **Domain values are centralized.** Statuses, target models, output formats, tag kinds, and their display labels live in [app/domain.py](app/domain.py) and are exposed to templates as Jinja globals (`MODEL_LABELS`, `SCRIPT_STATUS_LABELS`, …) via [app/templating.py](app/templating.py). Adding a model/format is a one-line change there — don't hard-code these elsewhere.
- **Don't block on slow work in a request.** Routes run synchronously in a threadpool; the generator is fast and deterministic. If you wire in a real (slow) LLM, keep request latency in mind — stream, background, or paginate rather than blocking a single request on a long call.
- **Theme through Tailwind + CSS variables**, not inline styles: edit [app/static/css/input.css](app/static/css/input.css) (`:root` light / `.dark` dark) and rebuild with `make css`. Respect the `feature_*` flags in [app/config.py](app/config.py) when gating UI areas.

---

## 6c. Config & Credentials

- **[app/config.py](app/config.py) is the single source of settings** (pydantic `Settings`), read once via the `lru_cache`d `get_settings()`. It is the **only** place env vars are read.
- Settings come from environment variables / a local `.env` (copied from [.env.example](.env.example), git-ignored). **Everything has a safe default, so the app runs with no `.env` at all.**
- **Any new setting must be added in two places:** a typed field in `Settings` (with a default) **and** a documented placeholder in [.env.example](.env.example). Tests can monkeypatch env then call `get_settings.cache_clear()`.
- `SECRET_KEY` only signs the session cookie that carries flash messages — **there is no login**. `SessionMiddleware` is wired in [app/main.py](app/main.py); if you ever re-add auth (see [CUSTOMIZATION.md](CUSTOMIZATION.md)), the cookie infra is already in place.
- **Database migrations are Alembic** (`migrations/`, run on startup via `app/migrations_runner.py`). **Any new or changed model needs a migration:** run `make migration m="describe change"`, then `ruff check --fix` + `ruff format` the generated file (autogenerated style fails lint). A drift test (`tests/unit/test_migrations.py::test_no_model_migration_drift`) fails `make test` if models and migrations disagree. Tests point `DATABASE_URL` at a throwaway SQLite file and rebuild the schema per test ([tests/conftest.py](tests/conftest.py)).

---

## 7. End of Session Checklist

At the end of **every** chat session:

1. **Commit and push all changes.** Stage modified files, commit with a meaningful message (e.g. `STORY_003: per-model avoid lists` or `Fix BUG_002: export filename slug`), and push to `origin develop`. **Double-check no git-ignored secret/state file (`.env`, `*.db`, `data/*`, built `app.css`) was force-added.**
2. Review the conversation: if anything built or discussed affects `CLAUDE.md`,
   **update it directly — no approval needed** — and state what changed. If nothing
   does, state: **"No updates to `CLAUDE.md` needed this session."**
3. Likewise for `README.md` / `CUSTOMIZATION.md`: **update them directly (no approval
   needed)**, then state what changed, whenever any of these are true:
     - A new feature, entity, or route is complete and working
     - The run/setup commands or Make targets change
     - New dependencies are added ([pyproject.toml](pyproject.toml) / [package.json](package.json))
     - A new config field or feature flag is introduced
     - The folder structure changes
   - If none apply, state: **"No updates to `README.md` / `CUSTOMIZATION.md` needed this session."**

> The operator has standing approval for docs upkeep: make warranted `CLAUDE.md`,
> `README.md`, and `CUSTOMIZATION.md` edits automatically (don't ask first) — just
> report what you changed.
