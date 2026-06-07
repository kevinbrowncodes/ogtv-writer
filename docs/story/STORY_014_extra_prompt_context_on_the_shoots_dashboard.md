# STORY_014 — Add extra prompt context when running a shoot

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** a per-shoot button that lets me type extra
prompt context and run that shoot with it **so that** I can steer one shoot's generation
without editing the catalog prompt or affecting the others — the same "addendum" the
single-job Generate page already supports.

Per-shoot and one-time: the note applies to that single run only and is not stored.

## Acceptance Criteria

- [x] Each runnable shoot row (Pending or Done) shows a **+ Context** button next to its Run / Re-run.
- [x] Clicking **+ Context** opens a modal (in the global `#modal`) with a textarea, showing which shoot, prompt, and model the run will use.
- [x] Submitting the modal queues a folder job for **that one shoot** with the typed text as the job's `addendum`, then returns to the dashboard with a "Job queued." flash (the page reload closes the modal).
- [x] The note is appended to the prompt by the existing `assemble_prompt()` (under "## Additional details for this job") — no new generation logic.
- [x] The plain one-click **Run** / **Re-run** and **Run all pending** are unchanged (no context).
- [x] Over-long context (> 20000 chars, the existing `JobCreate.addendum` bound) queues nothing and flashes a clear error.
- [x] The modal carries the picker's current Prompt / Model / Count, so the contextual run honours the same selections.

## Technical Notes

- Entity / files touched: route + templates only — no model/schema/domain/config/service changes.
  - [app/routes/shoots.py](../../app/routes/shoots.py):
    - Add `GET /shoots/context` → render the modal partial for a resolved shoot, echoing the picker's `prompt_slug` / `model` / `count` (passed in via HTMX `hx-include`) as hidden fields.
    - Add an `addendum` form field to `POST /shoots/run`; thread it through `_queue_shoot()` into `job_service.create_job(addendum=…)` (currently hardcoded `""`); reject over-long text with a clear message (bound mirrors `JobCreate.addendum`, 20000).
    - `POST /shoots/run-all` is unchanged (batch runs carry no context, since context is one-time per shoot).
  - [app/templates/partials/shoots/_context_modal.html](../../app/templates/partials/shoots/) (new): the dialog — a plain `<form method="post" action="/shoots/run">` with hidden `source_dir`/`prompt_slug`/`model`/`count` + a `name="addendum"` textarea; closes via the existing `[data-modal-close]` / Escape and the post-submit page reload.
  - [app/templates/partials/shoots/_list.html](../../app/templates/partials/shoots/_list.html): add the **+ Context** button (`type="button"`, `hx-get="/shoots/context"`, `hx-include` the picker fields, `hx-target="#modal"`) to each Pending/Done row.
- Routes added/changed: `GET /shoots/context` (new); `POST /shoots/run` gains an optional `addendum` field.
- Reuse: `assemble_prompt()` already appends the addendum; `JobCreate.addendum` already bounds it; the `#modal` infra + `[data-modal-close]` already exist in `shell.html` / `app.js`. No new client JS.
- Live-refresh safety: the editor lives in `#modal`, which sits outside the 3s-polling `#shoots-list`, so typing is never wiped by the auto-refresh.

## Testing Plan

Route + template change, so weighted toward integration.

- **Unit** (`tests/unit/`): **N/A — no new service/pure function.** This story only renders a modal and threads an existing field through a route. The addendum's effect on the prompt is already covered by `test_generation_service.py::test_assemble_prompt_appends_addendum`, and `create_job` persistence by `test_job_service.py`.
- **Integration** (`tests/integration/test_shoots.py`, `TestClient`): `/shoots` rows render a **+ Context** button; `GET /shoots/context` renders the modal (textarea, hidden `source_dir`, the carried prompt/model); `POST /shoots/run` with an addendum persists it on the created job; an over-long addendum queues nothing and redirects with an error flash; a blank/absent addendum still works (existing run tests).
- **e2e** (`tests/e2e/`): **N/A — covered by integration.** The change is one button + a modal on an existing flow; no new browser-level interaction warrants a Playwright test.

## Estimated Complexity

S–M — one new render route, one modal partial, a button per row, and an optional field threaded through the existing run route; all downstream plumbing (`addendum` → `assemble_prompt` → job) already exists.
