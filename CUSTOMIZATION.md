# Customizing the template for a new app

This is the checklist for turning **Hyperstack** into *your* app. The good news:
the Python import package is just `app/`, so most "renaming" is cosmetic config —
you don't have to move directories or rewrite imports.

---

## 0. Start your copy

- **GitHub:** click **“Use this template” → Create a new repository**, or
- **Fork/clone** and re-point the remote:
  ```bash
  git clone <this-repo> my-new-app && cd my-new-app
  rm -rf .git && git init
  ```

---

## 1. Rename the project

The string `hyperstack` / `Hyperstack` appears in a handful of config files
(`pyproject.toml`, `package.json`, README, Makefile/Docker image tag). Find them:

```bash
grep -ri "hyperstack" --exclude-dir=.git .
```

Replace them (pick your name). On **macOS**:

```bash
NEW=myapp
grep -rl "hyperstack" --exclude-dir=.git . | xargs sed -i '' "s/hyperstack/$NEW/g"
grep -rl "Hyperstack" --exclude-dir=.git . | xargs sed -i '' "s/Hyperstack/MyApp/g"
```

On **Linux**, use `sed -i` (no `''`):

```bash
grep -rl "hyperstack" --exclude-dir=.git . | xargs sed -i "s/hyperstack/myapp/g"
```

> You do **not** need to rename the `app/` package — keeping it generic means
> none of your imports (`from app...`) ever change between projects.

---

## 2. Set branding & config

Edit `.env` (copy from `.env.example` if you haven't):

- `APP_NAME`, `APP_URL`, `APP_DESCRIPTION` — shown in the UI, page titles, PWA manifest.
- `SECRET_KEY` — generate one: `python -c "import secrets; print(secrets.token_hex(32))"`.
- `SEED_USER_EMAIL` / `SEED_USER_PASSWORD` — your dev login.

Visuals:

- **Icon/logo:** replace `app/static/icons/icon.svg`.
- **Theme colors:** edit the CSS variables in `app/static/css/input.css`
  (`:root` for light, `.dark` for dark). You rarely need to touch `tailwind.config.js`.
- **Theme color meta / PWA bg:** `base.html` (`<meta name="theme-color">`) and
  `app/routes/pwa.py`.

---

## 3. Rename or remove the example "Items" feature

`Items` exists purely as a working blueprint. Two options:

**A) Rename it to your core entity** (e.g. `Project`):

- `app/models/item.py` → `project.py` (`class Item` → `class Project`, `__tablename__`)
- `app/schemas/item.py`, `app/services/item_service.py`, `app/routes/items.py`
- `app/templates/pages/items.html`, `app/templates/partials/items/`
- Update `app/models/__init__.py`, the router include in `app/main.py`, and the
  sidebar link.

**B) Delete it** and start fresh:

- Remove the files above, delete the `items` import/include in `app/models/__init__.py`
  and `app/main._register_routers()`, and remove the sidebar link + dashboard
  "recent items" section. Then add your own feature (§4).

Either way, update `scripts/seed.py` so it seeds your data.

---

## 4. Add your first feature (the 5-file recipe)

For an entity `Thing`:

| File | Purpose |
|------|---------|
| `app/models/thing.py` | ORM model (+ register in `app/models/__init__.py`) |
| `app/schemas/thing.py` | `ThingCreate` / `ThingUpdate` / `ThingRead` |
| `app/services/thing_service.py` | CRUD functions taking a `Session` |
| `app/routes/thing.py` | `router` with page + HTMX partial routes |
| `app/templates/pages/thing.html` (+ `partials/thing/`) | UI |

Then:
- include the router in `app/main._register_routers()` (`>>> INCLUDE ... <<<` marker),
- add a nav item in `app/templates/partials/_sidebar.html` (`>>> ADD NAV ... <<<` marker).

Copy the `Items` files as your starting point — the names line up exactly.

---

## 5. Database & migrations

SQLite is the default and is perfect for personal/single-instance apps.

**Switch to Postgres:**
```bash
# .env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/mydb
```
Add the driver to `pyproject.toml` dependencies: `"psycopg[binary]>=3.2"`.

**Adopt migrations (recommended before you have real data):**
```bash
pip install alembic
alembic init migrations
# point migrations/env.py at app.database.Base.metadata and app.config DATABASE_URL
alembic revision --autogenerate -m "init"
alembic upgrade head
```
Then make `init_db()` in `app/database.py` a no-op (or only run it in tests).

---

## 6. Common integrations (where they go)

- **Stripe / billing:** add keys to `config.py` + `.env`; create
  `app/services/billing_service.py` and `app/routes/billing.py`; add a webhook route.
- **AI (Anthropic/OpenAI):** add the SDK + API key to `config.py`; put calls in a
  service (e.g. `app/services/ai_service.py`) so routes stay thin.
- **Background jobs:** start with FastAPI `BackgroundTasks`; graduate to a queue
  (e.g. Redis + a worker) when needed.
- **Email:** add an `email_service.py`; render bodies with the same Jinja templates.

Every integration follows the same shape: **config → service → route → template.**

---

## 7. Ship it

See **README → Production deployment recommendations**. Minimum:
`ENVIRONMENT=production`, `DEBUG=false`, a real `SECRET_KEY`, HTTPS in front,
and Postgres + migrations if multi-user.

---

## Full customization checklist

```
[ ] Created repo from template / re-init git
[ ] Renamed "hyperstack"/"Hyperstack" in config files
[ ] Copied .env.example → .env and set APP_NAME / APP_URL / SECRET_KEY
[ ] Replaced app/static/icons/icon.svg
[ ] Tuned theme colors in app/static/css/input.css
[ ] Renamed or removed the Items example
[ ] Updated scripts/seed.py for your data
[ ] Added your first real feature (model/schema/service/route/templates)
[ ] Added nav links in _sidebar.html; cleaned up the dashboard
[ ] Updated/replaced tests for your feature
[ ] Chose a database (SQLite vs Postgres) and set up migrations if needed
[ ] Reviewed README's production + hardening notes
[ ] Updated this README's title/description; replaced LICENSE if needed
[ ] `make check` passes (lint + types + tests)
```

---

## Handy commands

```bash
make help        # list all tasks
make setup       # one-time: deps + browser + CSS + seed
make dev-all     # Tailwind watch + reloading server
make check       # lint + typecheck + tests (run before committing)
make seed        # (re)create demo user + sample data
make css         # build production CSS
make docker-run  # run in a container
```
