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

- **Prompt inbox** — paste markdown prompts, save drafts, tag by theme/model/style.
- **Generate** — pick a source prompt, a target model (Veo / Wan / Generic), an
  output format, and how many scripts to make (1, 3, 5, 10). Get that many
  distinct, structured drafts in your library.
- **Script library** — search and filter by model, status, theme/tag, and date.
- **Script detail** — view the markdown, edit it, **copy to clipboard**,
  **export `.md`**, **duplicate**, and **create more variations**.
- **Templates** — reusable script/prompt patterns (Veo cinematic, Wan motion,
  shot structures) that drop straight into the generator.
- **Tags** — your canonical catalog of themes, models, and styles.

### Script lifecycle

`draft → ready → used → archived` — marking a script **used** stamps a "used
date" automatically.

---

## The generator

The generator is **offline and deterministic** — no API key, no network. For
each variation it layers a rotating cinematic "lens" (camera / lighting / mood)
over a model- and format-specific pattern, producing distinct, paste-ready
markdown with a **Master prompt**, a **Structure** breakdown, **Tech** notes
(aspect ratio / duration), and an **Avoid** list tuned per model.

Want a real LLM later? [`app/services/generation_service.py`](app/services/generation_service.py)
is the single seam: keep `create_scripts()` and swap the body of
`build_script_body()` for a Claude/OpenAI call (add the key in
[`app/config.py`](app/config.py)). Routes, library, and export don't change.

---

## Stack

| Layer        | Choice |
|--------------|--------|
| Web framework| **FastAPI** |
| Templating   | **Jinja2** (server-rendered HTML) |
| Interactivity| **HTMX** (AJAX/partials via HTML attributes) |
| Styling      | **Tailwind CSS** |
| Data         | **SQLAlchemy 2.0 + SQLite** |
| Tests        | **pytest + Playwright** |
| PWA          | manifest + service worker (installable, offline app-shell) |

No React/Vue/Svelte. No bundler. The only Node usage is compiling Tailwind.

---

## Setup (first time only)

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
# sample prompts, scripts, templates, tags
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

Once setup is done, this is all you need — **every time**:

```bash
source .venv/bin/activate
make dev
```

Open **http://localhost:8000**. There's **no login** — it drops you straight on
the dashboard. Stop the server with `Ctrl-C`.

### Hot-reload while developing

```bash
# terminal 1: rebuild Tailwind on template changes
make css-watch
# terminal 2: uvicorn --reload
make dev
# ...or both at once:
make dev-all
```

---

## Project structure

```
app/
├── main.py                  # App factory + router wiring
├── config.py                # Typed settings from env (.env)
├── domain.py                # Controlled vocab + labels (models, formats, statuses)
├── database.py              # SQLAlchemy engine/session/Base + get_db
├── dependencies.py          # DbSession (no auth — internal tool)
├── templating.py            # Jinja2 setup, flash(), toast helpers, domain globals
├── models/                  # Prompt, Script, ScriptTemplate, Tag
├── schemas/                 # Pydantic validation per entity
├── services/                # Business logic (incl. generation_service)
├── routes/                  # prompts, generate, scripts, script_templates, tags, pages, settings
├── templates/
│   ├── pages/               # dashboard, prompts, scripts, script_detail, script_edit, generate, templates, tags, settings
│   └── partials/            # HTMX fragments (_list, _row, _form, _status_badge, ...)
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
| Dashboard | `GET /dashboard` (cards: prompts / scripts / ready / used + recent), `GET /dashboard/stats` (polled) |
| Prompts | `GET /prompts`, `/prompts/search`, `POST /prompts`, `PUT /prompts/{id}`, `DELETE /prompts/{id}` |
| Generate | `GET /generate` (prefill via `?prompt_id=` / `?template_id=`), `POST /generate` |
| Scripts | `GET /scripts` (filters), `/scripts/{id}` (detail), `/scripts/{id}/edit`, `POST /scripts/{id}`, `/scripts/{id}/export`, `/duplicate`, `/variations`, `/status`, `DELETE /scripts/{id}` |
| Templates | `GET /templates`, `/templates/search`, `POST /templates`, `PUT /templates/{id}`, `DELETE /templates/{id}` |
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

- **Unit** — services in isolation against a temp DB (prompt/script/generation).
- **Integration** — routes via FastAPI's `TestClient`, asserting on rendered
  HTML + HTMX headers (prompts, scripts, generate, templates, tags, dashboard).
- **e2e** — a real browser drives a live server: dashboard, create-prompt modal,
  the generate flow, and the script library.

---

## Docker

```bash
# http://localhost:8000
docker compose up --build
# or
make docker-build && docker run -p 8000:8000 --env-file .env ogtv-writer
```

---

## Extending it later

OGTV Writer is deliberately easy to grow into other OnlyGainsTV studio roles
(Editor, Publisher, …). See **[CUSTOMIZATION.md](CUSTOMIZATION.md)** for the
five-file recipe to add an entity, how to wire a real LLM into the generator,
and how to re-add login if you ever open it up to multiple operators.

---

## License

MIT — see [LICENSE](LICENSE).
