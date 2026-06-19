# OGTV Writer

The **Writer** tool for the **OnlyGainsTV** video studio workflow. It helps a
single operator (you) turn markdown prompts into structured, model-ready scripts
for AI video generation models — **Google Veo**, **Wan**, and similar
text-to-video / image-to-video systems — then organize, edit, and export them as
clean Markdown.

> Internal production tool, not a public SaaS. **No login.** Server-rendered,
> minimal JavaScript. Built on FastAPI + Jinja2 + HTMX + Tailwind + SQLite.

---

## What it does

```
Prompt (markdown)  →  Generate N variations  →  Edit / tag / status  →  Copy / export .md → Veo / Wan
```

- **Prompt library** — your reusable instruction prompts as `.md` files in
  `app/static/prompts/`; browse and preview them, no database.
- **Generate** — pick a prompt, upload a **first-frame image**, add an optional
  addendum and (for `{{COUNT}}` prompts) a count, and queue a job.
- **Queue** — an in-process worker sends each job to **Gemini** in the background;
  watch its status go `queued → running → done` live.
- **Script library** — search and filter by status, tag, and date; the scripts a
  job produces land here automatically.
- **Script detail** — view the markdown, edit it, **copy to clipboard**, and
  **export `.md`** (or download a whole run as a `.zip`).
- **Tags** — your canonical catalog of themes, models, and styles.

### Script lifecycle

`draft → ready → used → archived` — marking a script **used** stamps a "used
date" automatically.

---

## The generator

The generator calls **Google Gemini** (multimodal). A job pairs a prompt file
with an uploaded first-frame image (and an optional addendum); the assembled
prompt — `{{COUNT}}` substituted, addendum appended, plus an output contract — is
sent to Gemini by an **in-process background worker**. The response is parsed into
individual scripts (plus titles and a summary) and saved to the library.

Set `GEMINI_API_KEY` in `.env` to enable generation (get a free key at
[aistudio.google.com](https://aistudio.google.com)); without it, jobs queue and
then fail with a clear message. The single seam is
[`app/services/gemini_client.py`](app/services/gemini_client.py) — swap it for a
different provider without touching routes, parsing, the library, or export. Tests
mock it, so the suite never makes a live, paid call.

---

## Stack

| Layer        | Choice |
|--------------|--------|
| Web framework| **FastAPI** |
| Templating   | **Jinja2** (server-rendered HTML) |
| Interactivity| **HTMX** (AJAX/partials via HTML attributes) |
| Styling      | **Tailwind CSS** |
| Data         | **SQLAlchemy 2.0 + SQLite** |
| AI           | **Google Gemini** (`google-genai`, multimodal) |
| Tests        | **pytest + Playwright** |
| PWA          | manifest + service worker (installable, offline app-shell) |

No React/Vue/Svelte. No bundler. The only Node usage is compiling Tailwind.

---

## Setup (first time only)

> Running with **Docker**? Skip this whole section — go straight to
> [Quick start](#quick-start). The steps below install Python, Node, and the
> Playwright browser, and are only needed for **local development and the test
> suite** — the container needs none of them.

**Prerequisites:** Python 3.11+, Node 18+ (for Tailwind CSS), `make` (optional).

```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
make setup
```

`make setup` installs the Python + Node deps, downloads the Playwright test
browser, builds the CSS, and seeds sample data — equivalent to:

```bash
pip install -e ".[dev]"
npm install
python -m playwright install chromium
npm run css:build
# seed sample data (tags + scripts) — applies migrations first, so the schema is built
python -m scripts.seed
```

> **Just want to run the app, not the e2e tests?** Skip the (large) Playwright
> browser download — install everything except it:
>
> ```bash
> pip install -e ".[dev]"
> npm install
> npm run css:build
> make seed
> ```

---

## Quick start

Two ways to run it — pick one.

### Option A — Local (Python virtualenv)

After [Setup](#setup-first-time-only), this is all you need — **every time**:

```bash
source .venv/bin/activate
make dev
```

Open **http://localhost:8000**. There's **no login** — it drops you straight on
the dashboard. Stop the server with `Ctrl-C`.

**Hot-reload while developing:**

```bash
# terminal 1: rebuild Tailwind on template changes
make css-watch
# terminal 2: uvicorn --reload
make dev
# ...or both at once:
make dev-all
```

### Option B — Docker (single container)

No Python, virtualenv, Node, or Tailwind setup — just Docker and a `.env`. This
is the everyday way to run it as a background service:

```bash
# One-time: create your .env (defaults work; add your Gemini key to enable generation)
cp .env.example .env
# Build + start detached; then open http://localhost:9001
make docker-up
```

Open **http://localhost:9001** — same app, same dashboard, no login. The
container runs in the background with `restart: always`, so it survives closing
the terminal and **comes back automatically after a reboot** (as long as Docker
Desktop auto-starts — see [Start at login](#run-it-in-the-background-and-start-at-login)).

```bash
# Is it running? Prints a row when up, empty when down
docker compose ps --status running
# Follow the logs
make docker-logs
# Stop it but KEEP it (so it auto-starts again next login)
make docker-stop
# Remove it entirely (disables auto-start until you `make docker-up` again)
make docker-down
# Down for any reason? This brings it back (rebuilds if needed)
make docker-up
```

> **Page still loads with stale data but nothing responds?** The container is
> probably stopped — the PWA service worker keeps serving a cached shell. Run
> `make docker-up`, then hard-refresh (⌘⇧R). See [Docker](#docker) below for the
> full details, the single-image alternative, and changing the port.

---

## Project structure

```
app/
├── main.py                  # App factory + router wiring
├── config.py                # Typed settings from env (.env)
├── domain.py                # Controlled vocab + labels (script + job statuses, tag kinds)
├── database.py              # SQLAlchemy engine/session/Base + get_db
├── dependencies.py          # DbSession (no auth — internal tool)
├── templating.py            # Jinja2 setup, flash(), toast helpers, domain globals
├── models/                  # Job, Script, Tag
├── schemas/                 # Pydantic validation per entity
├── services/                # prompt_catalog, generation, gemini_client, output_parser,
│                            #   job_worker, uploads, job/script/tag services
├── routes/                  # prompt_catalog, jobs, scripts, tags, pages, settings, health, pwa
├── templates/
│   ├── pages/               # dashboard, prompt_catalog, scripts, script_detail, script_edit, jobs, job_new, job_detail, tags, settings
│   └── partials/            # HTMX fragments (jobs/_list, jobs/_status, scripts/_row, ...)
└── static/                  # css/js/icons + service worker
tests/{unit,integration,e2e}/
scripts/seed.py              # sample OnlyGainsTV data
```

### Naming conventions (same five files per entity)

| Concept | Location | Example |
|---------|----------|---------|
| Model   | `app/models/<entity>.py` | `class Script` |
| Schema  | `app/schemas/<entity>.py` | `ScriptCreate` |
| Service | `app/services/<entity>_service.py` | `create_script(db, ...)` |
| Router  | `app/routes/<feature>.py` | `scripts.router` |
| Templates | `templates/pages/<feature>.html` + `partials/<feature>/` | `pages/scripts.html` |

**The golden rule:** routes are thin (parse → call a service → render a
template). All DB access lives in services. All env access lives in `config.py`.

---

## Routes

| Area | Key routes |
|------|-----------|
| Dashboard | `GET /dashboard` (cards: queued / scripts / ready / used + recent), `GET /dashboard/stats` (polled) |
| Prompts | `GET /prompts` (file catalog), `GET /prompts/{slug}` (preview) |
| Jobs | `GET /jobs/new`, `POST /jobs`, `GET /jobs` (queue), `GET /jobs/{id}` (detail + live status), `GET /jobs/{id}/status`, `GET /jobs/{id}/export.zip` |
| Scripts | `GET /scripts` (filters), `/scripts/{id}` (detail), `/scripts/{id}/edit`, `POST /scripts/{id}`, `/scripts/{id}/export`, `/duplicate`, `/status`, `DELETE /scripts/{id}` |
| Tags | `GET /tags`, `POST /tags`, `DELETE /tags/{id}` |

---

## Configuration

All config is environment variables (see [.env.example](.env.example)), parsed
by [app/config.py](app/config.py).

| Variable | Purpose |
|----------|---------|
| `APP_NAME`, `APP_URL`, `APP_DESCRIPTION`, `BRAND_NAME` | Branding (UI + PWA manifest) |
| `ENVIRONMENT` | `development` / `production` / `test` |
| `DEBUG` | Verbose logging + interactive tracebacks |
| `SECRET_KEY` | Signs the session cookie (used only for flash messages) |
| `DATABASE_URL` | `sqlite:///./data/app.db` or a Postgres URL |
| `AUTO_MIGRATE` | Apply migrations on startup (dev); set `false` in prod and run `make migrate` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini auth + model for the generator (blank = generation disabled) |
| `BUILD_VERSION` | Build stamp shown in the footer + `/healthz`. Set by `make deploy` (`YYMMDD-HHMM`, US Eastern); blank locally = process-start time |
| `FEATURE_DARK_MODE`, `FEATURE_DASHBOARD` | Feature flags |

---

## Testing

```bash
# unit + integration (fast, no browser)
make test
# Playwright browser tests
make test-e2e
# everything
make test-all
# lint + typecheck + tests
make check
```

- **Unit** — services in isolation against a temp DB (prompt catalog, generation,
  output parsing, scripts, uploads, run export). Gemini is mocked.
- **Integration** — routes via FastAPI's `TestClient`, asserting on rendered HTML
  + HTMX headers (dashboard, prompt catalog, jobs, scripts, tags).
- **e2e** — a real browser drives a live server: dashboard, prompt catalog, the
  submit-a-job flow, a completed job's split scripts, and the script library.

---

## Docker

Run the whole app as a single container — no Python, virtualenv, Node, or Tailwind
setup required. You only need Docker and a `.env`.

```bash
# One-time: create your .env (defaults work; add your Gemini key to enable generation)
cp .env.example .env
# Build + run; then open http://localhost:9001
make docker-run
```

`make docker-run` is `docker compose up --build`. What the container does:

- **Migrations run on startup.** A fresh database gets the full schema; an existing one
  upgrades in place — no manual `make migrate` step.
- **Your real data is used.** The host `./data` is bind-mounted into the container, so it
  reads your existing SQLite database (`data/app.db`) and shoot image folders
  (`data/logline/...`), and anything the app writes persists straight back to `./data`.
  Data survives restarts and rebuilds. Want an isolated/throwaway instance instead? Swap
  the `./data:/app/data` line in [docker-compose.yml](docker-compose.yml) for a named volume.
- **Generation is optional at boot.** The app starts even without a Gemini key; the key in
  `.env` only enables the generate feature.

### Deploy a new build (and confirm which one is live)

`make deploy` rebuilds the image, recreates the container, and stamps it with a
**build version** — the date and time of the deploy in US Eastern (military) time,
e.g. `Build 260618-0935`:

```bash
make deploy   # prints the build number when it finishes
```

That stamp shows up in two places, so you always know exactly which build is running:

- the **sidebar footer** (bottom of the left nav), on every page, and
- `curl -s localhost:9001/healthz` → `"build":"260618-0935"`.

Running locally with `make dev` (no deploy)? The footer falls back to when the dev
server started. The Eastern timezone resolves inside the slim container via the
`tzdata` dependency.

### Run it in the background (and start at login)

`make docker-run` stays in your terminal. To run it as a background service that survives
closing the terminal and comes back after a reboot:

```bash
# Start detached (background); returns to the prompt
make docker-up
# Follow the logs when you want them
make docker-logs
# Stop it but KEEP the container (so it auto-starts again next login)
make docker-stop
# Remove the container entirely (your ./data is kept)
make docker-down
```

The container uses `restart: always`, so once started with `make docker-up` the Docker
daemon restarts it automatically whenever the daemon itself starts — including after a
reboot — and even if you'd `make docker-stop`ped it. This needs two things:

1. **Docker Desktop auto-starts.** Enable it one-time in **Docker Desktop → Settings →
   General → "Start Docker Desktop when you sign in to your computer."** (On macOS this is
   start-at-login, not pre-login boot.)
2. **The container still exists.** The daemon can only restart a container it knows about,
   so don't `make docker-down` it for routine stops — use `make docker-stop` instead.

> **Why not a LaunchAgent that runs `docker compose up -d` at login?** Tried it; macOS TCC
> blocks a `launchd` agent from reading the project under `~/Documents` ("Operation not
> permitted") unless you grant Full Disk Access to `/bin/bash` — broad and clunky. The
> `restart: always` policy needs none of that: the daemon restarts the container on its own,
> never touching the protected folder.

Check whether it's actually running — and bring it back if not:

```bash
# Up? Prints a row when running; empty when it's down
docker compose ps --status running
# Down for any reason? Re-run this (it rebuilds if needed)
make docker-up
```

Two gotchas worth knowing:

- **`make docker-down` disables auto-start.** It *removes* the container, and the daemon can
  only auto-restart a container that still exists — so after a `down` (or `docker rm`) the
  app stays down until you `make docker-up` again. For a routine stop that still comes back
  next login, use `make docker-stop`. If the app is unexpectedly unreachable, the
  `docker compose ps` check above is the first thing to run.
- **Prompt files are read live from the host.** `app/static/prompts/` is bind-mounted
  read-only into the container (alongside `./data`), so dropping or editing a `.md` brief in
  that folder shows up in the UI on the next refresh — no image rebuild needed. (The folder
  is still copied into the image at build time too, so the container also works standalone
  without the mount.)

Single-image alternative (mount `./data` yourself so data persists):

```bash
# Build the image
make docker-build
# Run it on http://localhost:9001, mounting your .env and ./data
docker run -p 9001:8000 --env-file .env -v "$(pwd)/data:/app/data" ogtv-writer
```

**Changing the port.** The container is published on **9001** by default. To use a
different host port, set `WEB_PORT` in your `.env` (e.g. `WEB_PORT=8080` → serves at
`http://localhost:8080`) and re-run `make docker-up` — no file edits needed. The container
always listens on `8000` internally; `WEB_PORT` only changes what the host publishes. (This
is separate from the app's own `PORT`, used by local `make dev`.)

> On native Linux, the container runs as a non-root user; if writes to a bind-mounted
> `./data` fail, match the host directory's ownership or relax its permissions. (On macOS
> Docker Desktop, bind mounts are permission-permissive, so this just works.)

---

## Extending it later

OGTV Writer is deliberately easy to grow into other OnlyGainsTV studio roles
(Editor, Publisher, …). See **[CUSTOMIZATION.md](CUSTOMIZATION.md)** for the
five-file recipe to add an entity, how to wire a real LLM into the generator,
and how to re-add login if you ever open it up to multiple operators.

---

## License

MIT — see [LICENSE](LICENSE).
