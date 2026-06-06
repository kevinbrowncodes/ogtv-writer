# STORY_001 — Browse your prompt library

> Epic: EPIC_001 · Status: Done

**As** the OnlyGainsTV operator, **I want** to see all my reusable prompt files
listed in the app and preview any one of them, **so that** I can pick the right
brief for a generation job without digging through the filesystem.

This is the foundational slice of [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md):
a **file-based, read-only prompt catalog**. No Gemini, no image upload, no queue —
those come in later stories. It just turns `app/static/prompts/` into a browsable
library and surfaces whether a prompt expects a `{{COUNT}}`.

## Acceptance Criteria

- [x] A **Prompts** page at `GET /prompts` lists every `.md` file in `app/static/prompts/`, each showing a human-readable **title** and its **filename**.
- [x] Each entry indicates whether the prompt uses a **`{{COUNT}}`** placeholder (a small badge/flag), so a later story knows when to show a count field.
- [x] Selecting a prompt shows its **full raw text** as a preview, without leaving the catalog (HTMX panel or a `/prompts/{slug}` view).
- [x] An **unknown or unsafe** prompt name (e.g. `../config`) returns a **404** — never a 500, never a file outside the folder.
- [x] When the folder has **no `.md` files**, the page shows a clear **empty state** explaining how to add a prompt (drop a `.md` into `app/static/prompts/`).
- [x] The **sidebar "Prompts" nav** points to this catalog; the old DB-inbox prompts page is no longer reachable from the UI.
- [x] The folder **ships with the operator's example prompts** (`video-review-prompt.md`, `260601-0000_wip-prompt.md`) so the catalog isn't empty on a fresh clone.

## Technical Notes

This feature is **not** a full five-file entity — there's no model or schema. It's a
filesystem-backed service + router + templates. Files touched/added:

- **New — `app/services/prompt_catalog.py`**
  - `PROMPTS_DIR = Path(app/static/prompts)` module constant (resolved off `__file__`).
  - `list_prompts(directory: Path | None = None) -> list[CatalogPrompt]` — globs `*.md`
    only (ignores dotfiles/subdirs), sorted by filename. `CatalogPrompt` is a small
    dataclass/`NamedTuple`: `slug` (filename stem), `filename`, `title`, `has_count`.
  - `get_prompt(slug: str, directory: Path | None = None) -> CatalogPrompt | None` —
    returns the prompt **with `body`** (full text), or `None`. **Path-traversal safe:**
    reject any slug that isn't a plain stem (no `/`, no `..`); resolve and confirm the
    file is inside `directory` before reading.
  - `title` derivation: from the filename stem (replace `-`/`_` with spaces, title-case).
    The example files don't have reliable headings, so filename is the stable source.
  - `has_count`: regex `r"\{\{\s*COUNT\s*\}\}"` (tolerates `{{ COUNT }}`).
  - The optional `directory` arg exists so unit tests can point at a `tmp_path`.
- **New — `app/routes/prompt_catalog.py`** (`router`, `tags=["prompts"]`):
  - `GET /prompts` → `pages/prompt_catalog.html` (list).
  - `GET /prompts/{slug}` → preview: full page, or `partials/prompt_catalog/_preview.html`
    when `is_htmx(request)`. Unknown/unsafe slug → `raise HTTPException(404)`.
- **New templates** (named `prompt_catalog*` to avoid clobbering the old inbox templates,
  which are deleted in STORY_006): `pages/prompt_catalog.html`, `partials/prompt_catalog/_card.html`,
  `partials/prompt_catalog/_preview.html`. Show the body in a `<pre>` block (these are
  plain-text briefs; raw is clearer than rendered markdown). Respect the theme; no inline styles.
- **`app/main.py`** — in `_register_routers()`, **replace** the old `prompts` include with
  `prompt_catalog`. (The old `app/routes/prompts.py` + `Prompt` model/service/inbox
  templates stay on disk as dead code until STORY_006 deletes them.)
- **`app/templates/partials/_sidebar.html`** — point the existing "Prompts" link at the catalog.
- **`app/static/prompts/`** — create the folder and commit the two example prompts.

**Interim state (expected, documented for STORY_006):** `generate.py` / `scripts.py`
and the seed still reference the DB `Prompt` inbox; those flows are replaced in their own
stories. STORY_001 must not break them — it only repurposes `/prompts` and the nav.

**Out of scope:** editing prompts in-app, injecting `{{COUNT}}` (just *detect* it here),
any Gemini call, image upload.

## Testing Plan

~70/20/10. All layers apply.

- **Unit** (`tests/unit/test_prompt_catalog.py`, against a `tmp_path` dir):
  - `list_prompts()` returns one entry per `.md`, ignores non-`.md` files and subdirs, sorted.
  - title derivation from filename (`my-cool_prompt.md` → "My Cool Prompt").
  - `has_count` true for `{{COUNT}}` / `{{ COUNT }}`, false when absent.
  - `get_prompt(slug)` returns full `body`; unknown slug → `None`.
  - traversal guard: `get_prompt("../config")` (and similar) → `None`, reads nothing outside the dir.
  - empty dir → `[]`.
- **Integration** (`tests/integration/test_prompt_catalog.py`, `TestClient`):
  - `GET /prompts` → 200, lists the seeded example prompts, renders the `{{COUNT}}` badge correctly.
  - `GET /prompts/{slug}` → 200 and contains the prompt body; HTMX request returns the
    partial (no full `<html>` shell).
  - unknown slug → 404; traversal slug (`/prompts/..%2Fconfig`) → 404, not 500.
  - **Retire** the obsolete `tests/integration/test_prompts_htmx.py` (the DB inbox at
    `/prompts` no longer exists) so the suite stays green.
- **e2e** (`tests/e2e/`, Playwright) — **required** (new visible page): open `/prompts`,
  assert the example prompts are listed, click one, assert its preview text appears.

A story is Done only when `make check` is green (and `make test-e2e` for the flow above),
and `ruff` / `mypy` are clean.

## Estimated Complexity

**S–M** — one new service + router + a page and preview partial, plus a one-line router
swap and a nav tweak. No DB, no external API. The only subtlety is the path-traversal
guard and retiring the old inbox test.
