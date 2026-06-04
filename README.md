# Hyperstack

A **production-quality starter template** for building server-rendered web apps with
**FastAPI + Jinja2 + HTMX + Tailwind CSS**. It's intentionally generic — copy it,
rename it, and grow it into a dashboard, admin tool, AI utility, SaaS, internal
tool, or PWA.

> HTML-first. Minimal JavaScript. One repo for frontend + backend. Boring, fast,
> and maintainable by a solo developer.

---

## Why this stack?

| Layer        | Choice                | Why |
|--------------|-----------------------|-----|
| Web framework| **FastAPI**           | Async-ready, typed, great DX, batteries you actually use |
| Templating   | **Jinja2**            | Server-rendered HTML, no client framework needed |
| Interactivity| **HTMX**              | AJAX/partials via HTML attributes — minimal JS |
| Styling      | **Tailwind CSS**      | Utility-first, themeable, no CSS sprawl |
| Data         | **SQLAlchemy 2.0 + SQLite** | Simple default; swap to Postgres in one env var |
| Config       | **pydantic-settings** | Typed env config with `.env` support |
| Tests        | **pytest + Playwright** | Fast unit/integration + real browser e2e |
| Tooling      | **Ruff + mypy**       | One linter/formatter + static types |

No React/Vue/Svelte. No bundler. The only Node usage is compiling Tailwind.

---

## Features out of the box

- 🔐 Session-based **auth** (login / logout / optional signup) with hashed passwords
- 📊 **Dashboard** with self-refreshing stat cards (HTMX polling)
- 📝 Generic **Items CRUD** demonstrating every common HTMX pattern
- ⚙️ **Settings** area (profile + password + feature flags) with inline HTMX updates
- 🎨 **Dark mode**, responsive app-shell layout, reusable component classes
- 📱 **PWA**: installable, manifest, service worker, offline app-shell caching
- 🧪 Tests: unit, integration, and Playwright e2e
- 🐳 **Docker** + docker-compose, **Makefile**, **CI**, VS Code settings
- 🧱 Clean separation: `routes / services / models / schemas / templates / static`

---

## Project structure

```
hyperstack/
├── app/
│   ├── main.py              # App factory + middleware + router wiring
│   ├── config.py            # Typed settings from env (.env)
│   ├── database.py          # SQLAlchemy engine/session/Base + get_db
│   ├── dependencies.py      # Shared deps: DbSession, CurrentUser, auth
│   ├── templating.py        # Jinja2 setup, flash(), toast helpers
│   ├── security.py          # Password hashing
│   ├── logging_config.py    # Logging setup (dev vs prod)
│   ├── models/              # SQLAlchemy ORM models (User, Item)
│   ├── schemas/             # Pydantic validation/serialization
│   ├── services/            # Business logic (the only place that queries the DB)
│   ├── routes/              # HTTP routers (pages, items, settings, auth, ...)
│   ├── templates/
│   │   ├── base.html        # Root document (head, PWA, dark-mode bootstrap)
│   │   ├── shell.html       # App chrome (sidebar + topbar)
│   │   ├── pages/           # Full pages (dashboard, items, settings, login)
│   │   ├── partials/        # HTMX fragments (_list, _row, _form, ...)
│   │   └── errors/          # 404 / 500
│   └── static/
│       ├── css/input.css    # Tailwind source (compiled to app.css)
│       ├── js/app.js        # The entire client-side footprint (~120 lines)
│       ├── icons/icon.svg    # App icon (used by PWA + favicon)
│       └── service-worker.js
├── tests/{unit,integration,e2e}/
├── scripts/seed.py          # Demo user + sample data
├── data/                    # Local SQLite lives here (gitignored)
├── pyproject.toml           # Deps + Ruff + mypy + pytest config
├── package.json             # Tailwind build scripts only
├── tailwind.config.js
├── Dockerfile / docker-compose.yml
├── Makefile
├── README.md
└── CUSTOMIZATION.md         # ← Checklist for turning this into your app
```

---

## Quick start

**Prerequisites:** Python 3.11+, Node 18+ (for Tailwind), and `make` (optional).

```bash
# 1. Clone your copy of the template, then:
cp .env.example .env                # configure (works as-is for local dev)

# 2. (Recommended) create a virtualenv
python3 -m venv .venv && source .venv/bin/activate

# 3. Install everything, build CSS, install the test browser, seed demo data
make setup
#   ↳ equivalent to:
#     pip install -e ".[dev]"
#     npm install
#     python -m playwright install chromium
#     npm run css:build
#     python -m scripts.seed

# 4. Run it (hot reload)
make dev
```

Open <http://localhost:8000>. Log in with the seeded account:

```
Email:    admin@example.com
Password: password123      # from SEED_USER_* in .env
```

### Hot-reload dev workflow

Two processes during development:

```bash
make css-watch     # terminal 1: rebuild Tailwind on template changes
make dev           # terminal 2: uvicorn --reload

# ...or both at once:
make dev-all
```

Editing a `.py`, `.html`, or `.css` file reloads automatically.

---

## Architecture & naming conventions

Keep these consistent and the codebase stays navigable as it grows.

| Concept   | Location                        | Convention | Example |
|-----------|---------------------------------|------------|---------|
| Model     | `app/models/<entity>.py`        | singular class | `class Item` |
| Schema    | `app/schemas/<entity>.py`       | `EntityCreate/Update/Read` | `ItemCreate` |
| Service   | `app/services/<entity>_service.py` | verb functions taking `Session` | `create_item(db, ...)` |
| Router    | `app/routes/<feature>.py`       | exposes `router` | `items.router` |
| Route fn  | inside the router               | `<feature>_<action>` | `items_create` |
| Page URL  | `GET /<feature>`                | full page  | `/items` |
| Partial URL | `GET /<feature>/<verb>`       | HTMX fragment | `/items/search` |
| Page tmpl | `templates/pages/<feature>.html`| extends `shell.html` | `pages/items.html` |
| Partial tmpl | `templates/partials/<feature>/_*.html` | no `extends` | `partials/items/_row.html` |

**The golden rule:** routes are thin (parse → call a service → render a template).
All DB access lives in services. All env access lives in `config.py`.

---

## Where to add new app features

Adding a feature called `Project` (for example) is the same five files every time:

1. **Model** — `app/models/project.py`, then export it in `app/models/__init__.py`.
2. **Schema** — `app/schemas/project.py` (`ProjectCreate`, `ProjectRead`, ...).
3. **Service** — `app/services/project_service.py` (functions taking a `Session`).
4. **Router** — `app/routes/project.py` exposing `router`, then include it in
   `app/main._register_routers()` (look for the `>>> INCLUDE NEW FEATURE ROUTERS <<<` marker).
5. **Templates** — `templates/pages/project.html` (+ `partials/project/_*.html`),
   and add a nav link in `templates/partials/_sidebar.html` (look for `>>> ADD NEW NAV ITEMS <<<`).

The `Items` feature is a complete, working blueprint for exactly this — copy it.
Search the codebase for `>>> ADD` / `>>> INCLUDE` markers to find every extension point.

---

## HTMX patterns demonstrated (in the Items feature)

| Pattern | Where |
|---------|-------|
| `hx-get` + live search (debounced) | search box in `pages/items.html` → `/items/search` |
| `hx-post` create | modal form in `partials/items/_form.html` |
| `hx-put` inline edit | `partials/items/_row_edit.html` |
| `hx-delete` | delete button in `partials/items/_row.html` |
| `hx-target` / `hx-swap` | `#modal`, `#item-list`, `closest tr` throughout |
| `hx-swap-oob` (out-of-band) | create success closes modal + updates list (`_list.html`) |
| `hx-indicator` loading state | search spinner + submit-button spinner |
| Modal | loaded into `#modal`, closed by clearing it (app.js) |
| Polling | dashboard stat cards `hx-trigger="every 10s"` |
| `HX-Trigger` → toast | server header → `app.js` shows a toast |
| `HX-Redirect` | unauthenticated HTMX requests redirect to login |

---

## Configuration

All config is environment variables (see [.env.example](.env.example)), parsed by
[app/config.py](app/config.py). Key ones:

| Variable | Purpose |
|----------|---------|
| `APP_NAME`, `APP_URL`, `APP_DESCRIPTION` | Branding, shown in UI + PWA manifest |
| `ENVIRONMENT` | `development` / `production` / `test` |
| `DEBUG` | Verbose logging + interactive tracebacks |
| `SECRET_KEY` | Signs the session cookie — **change in prod** |
| `DATABASE_URL` | `sqlite:///./data/app.db` or a Postgres URL |
| `FEATURE_*` | Feature flags read in templates/routes |

### Dev vs production

The `ENVIRONMENT` value changes real behavior:

- **development** — debug logging, interactive error pages, auto-reloading
  templates, API docs at `/docs`, insecure cookies (http OK).
- **production** — concise logs, friendly 500 page (no traceback leak),
  `/docs` disabled, **secure (HTTPS-only) session cookie**.

---

## Testing

```bash
make test       # unit + integration (fast, no browser)
make test-e2e   # Playwright browser tests (needs: playwright install chromium)
make test-all   # everything
```

- **Unit** (`tests/unit`) — services in isolation against a temp DB.
- **Integration** (`tests/integration`) — routes via FastAPI's `TestClient`,
  asserting on rendered HTML and HTMX headers. Covers the login flow, dashboard
  rendering, and the full Items CRUD + HTMX interactions.
- **e2e** (`tests/e2e`) — a real browser drives a live server: login, dashboard,
  live search, create-via-modal, and delete.

---

## PWA / installable app

- `manifest.webmanifest` is generated at `/manifest.webmanifest` (reflects `APP_NAME`).
- `service-worker.js` is served at the site root with `Service-Worker-Allowed: /`
  and caches the app shell for basic offline support.
- On macOS, open the app in Chrome/Edge → **Install app** from the address bar.

To replace the icon, swap `app/static/icons/icon.svg`. For best cross-browser
install support you may also want to add `192×192` and `512×512` **PNG** icons and
list them in [app/routes/pwa.py](app/routes/pwa.py).

> HTMX is loaded from a CDN by default. For a fully offline-capable PWA, vendor it
> into `app/static/js/vendor/` and point `base.html` at the local file (the service
> worker already runtime-caches the CDN copy after first load).

---

## Docker

```bash
docker compose up --build      # http://localhost:8000
# or
make docker-build && docker run -p 8000:8000 --env-file .env hyperstack
```

The image builds Tailwind in a Node stage, then runs a slim Python image as a
non-root user. SQLite data persists in a named volume.

---

## Production deployment recommendations

- **Set real secrets**: `SECRET_KEY` (run `python -c "import secrets; print(secrets.token_hex(32))"`),
  `ENVIRONMENT=production`, `DEBUG=false`.
- **Use Postgres** for anything multi-user/concurrent: set `DATABASE_URL` and add
  migrations (see [CUSTOMIZATION.md](CUSTOMIZATION.md)). SQLite is great for single-instance / personal apps.
- **Run behind a reverse proxy** (Caddy/nginx/Traefik) that terminates TLS. The
  secure session cookie requires HTTPS in production.
- **Process model**: `uvicorn` (1 worker is fine for SQLite). For Postgres, run
  multiple workers via `gunicorn -k uvicorn.workers.UvicornWorker app.main:app -w 4`.
- **Migrations, not `create_all`**: `init_db()` is a dev convenience. Adopt Alembic
  before you have production data.
- **Hardening to consider**: CSRF tokens for mutations (the `SameSite=Lax` cookie
  already blocks cross-site form posts), rate limiting on `/login`, and a stronger
  password hash (`argon2`/`bcrypt`) — see `app/security.py`.
- **Easy hosts**: Fly.io, Render, Railway, a small VPS, or any container platform.

---

## Using this as a template

Click **“Use this template”** on GitHub, or fork/clone it. Then follow the
step-by-step **[CUSTOMIZATION.md](CUSTOMIZATION.md)** checklist to rename it and
make it yours.

---

## License

MIT — see below. Use it for anything.
