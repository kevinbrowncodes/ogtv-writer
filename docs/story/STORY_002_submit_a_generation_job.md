# STORY_002 — Submit a generation job

> Epic: EPIC_001 · Status: Not started

**As** the OnlyGainsTV operator, **I want** to create a generation job by picking a
prompt, uploading a first-frame image, and optionally adding an addendum and a count,
**so that** the work is captured in a queue I can build up and process later.

Second slice of [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md). This
introduces the **`Job`** entity, the submission form, and the **queue list**. No
Gemini call yet — submitting a job just persists it as `queued`; the worker arrives in
STORY_003.

## Acceptance Criteria

- [ ] A **New job** form (`GET /jobs/new`) lets me: choose a prompt from the catalog (STORY_001), **upload one image**, type an optional **addendum**, and set a **count**.
- [ ] The **count field only appears when the chosen prompt uses `{{COUNT}}`** (driven from the prompt picker); prompts without it hide/omit it.
- [ ] Submitting (`POST /jobs`) saves the uploaded image under `data/uploads/` and creates a `Job` with status **`queued`**, then redirects to the queue with a success flash.
- [ ] The **queue page** (`GET /jobs`) lists jobs newest-first with their prompt, a thumbnail or image filename, and status badge (`queued` for now).
- [ ] **Validation:** missing image, a non-image file, or an unknown prompt re-renders the form with a `422` and a clear message — no server error, nothing persisted.
- [ ] Uploaded images live only under `data/` (git-ignored); originals are never served from `app/static`.

## Technical Notes

Follows the five-file recipe (a real DB entity this time). Files added:

- **`app/models/job.py`** — `Job(Base, TimestampMixin)`: `id`, `prompt_slug` (str, the
  catalog filename stem), `prompt_filename` (str), `addendum` (Text, default ""),
  `count` (int | None), `image_path` (str, relative to repo root, e.g. `data/uploads/<uuid>.jpg`),
  `image_filename` (str, original name), `status` (str, default `"queued"`, index),
  `error` (Text, default ""), plus `started_at` / `finished_at` (nullable) and
  `result_raw` (Text, default "") — the last three are **populated in STORY_003**, declared
  now to avoid reshaping the model later. Register in `app/models/__init__.py`.
- **`app/schemas/job.py`** — `JobCreate` (`prompt_slug`, `addendum`, `count`). The image
  is handled as a FastAPI `UploadFile`, not part of the schema. Count is required + must be
  `> 0` only when the chosen prompt `has_count`; otherwise it's ignored/`None`.
- **`app/services/job_service.py`** — `create_job(db, *, prompt_slug, addendum, count, image_path, image_filename) -> Job`, `list_jobs(db, status: str | None = None)`, `get_job(db, id)`, `delete_job(db, job)`.
- **`app/services/uploads.py`** — `save_upload(file: UploadFile) -> tuple[str, str]`:
  validates content-type/extension against an allowlist (`jpg`/`jpeg`/`png`/`webp`),
  enforces a max size, writes to `data/uploads/<uuid>.<ext>` (creating the dir via
  `pathlib`, like `database.py` does for SQLite), returns `(relative_path, original_name)`.
  Rejects anything else with a `ValueError` the route turns into a 422.
- **`app/routes/jobs.py`** (`router`, `tags=["jobs"]`):
  - `GET /jobs/new` → `pages/job_new.html` (prompt `<select>` from `prompt_catalog.list_prompts()`).
  - `GET /jobs/new/count-field?slug=` → HTMX partial returning the count input when that
    prompt `has_count`, else empty — swapped in when the prompt selection changes.
  - `POST /jobs` (multipart: prompt_slug, addendum, count, image `UploadFile`) → validate,
    `save_upload`, `create_job`, `flash`, redirect `303 → /jobs`. On error, re-render form `422`.
  - `GET /jobs` → `pages/jobs.html` (the queue list).
- **Templates:** `pages/job_new.html`, `pages/jobs.html`, `partials/jobs/_row.html`,
  `partials/jobs/_count_field.html`, `partials/jobs/_status_badge.html`.
- **`app/main.py`** — include the `jobs` router. **`_sidebar.html`** — add "New job" + "Queue" nav.
- **`.gitignore`** already ignores `data/*` (keep `data/.gitkeep`); add `data/uploads/` is covered.

**Interim state:** the old deterministic `/generate` page still exists (removed in
STORY_003). Don't wire the new form to it.

**Out of scope:** running the job / calling Gemini (STORY_003), parsing output (STORY_004).

## Testing Plan

~70/20/10. All layers apply.

- **Unit** (`tests/unit/test_job_service.py`, `tests/unit/test_uploads.py`):
  - `create_job` persists with status `queued` and the given fields.
  - `save_upload` accepts allowed image types and writes a uniquely-named file under the
    target dir; **rejects** a non-image / disallowed extension / oversized file (raises).
  - count validation: required + positive when `has_count`, ignored otherwise.
  - `list_jobs(status=...)` filters; `get_job` returns/None.
- **Integration** (`tests/integration/test_jobs.py`, `TestClient`):
  - `GET /jobs/new` → 200, lists catalog prompts.
  - `GET /jobs/new/count-field?slug=` → returns the count input for a `{{COUNT}}` prompt,
    empty for one without.
  - `POST /jobs` with a tiny in-memory image fixture → 303 redirect, job shows on `GET /jobs` as `queued`, image file written under a temp `data/uploads`.
  - `POST /jobs` with **no image** / a **text file** / an **unknown prompt** → 422, form re-rendered, nothing persisted.
- **e2e** (`tests/e2e/`) — **required** (new visible flow): open New job, pick a prompt,
  upload an image fixture, submit, and see the job listed as `queued`.

Done when `make check` + `make test-e2e` are green and `ruff`/`mypy` are clean.

## Estimated Complexity

**M** — first multipart upload + a new entity + a dynamic (HTMX) count field. The fiddly
bits are upload validation/storage and the conditional count field.
