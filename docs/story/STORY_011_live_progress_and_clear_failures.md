# STORY_011 — See what the worker is doing (live progress + clear failures)

> Epic: — (follow-on to [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md)) · Status: Done

**As** the OnlyGainsTV operator, **I want** the app to show me what's happening as jobs
run — and to tell me clearly when one comes back empty instead of silently calling it
"done" — **so that** I'm not staring at a stale "Pending" wondering if it's stuck.

This is driven by three real observations: the **Shoots dashboard never auto-refreshes**
(so completed jobs still showed "Pending"), and a **blocked/empty Gemini response was
silently marked `done`** with no script and no explanation (e.g. `big-chest` returned 0
characters — a safety block — yet looked finished).

## Acceptance Criteria

- [x] The **Shoots dashboard auto-refreshes** while any job is queued/running (statuses
      flip Pending → Done live), and stops polling once the queue is idle.
- [x] An **empty Gemini response (or 0 parsed scripts) marks the job `failed`** with a
      clear reason — e.g. *"Gemini returned no content — prompt blocked (SAFETY)"* —
      capturing the API's finish/block reason when available. No more silent "done with nothing".
- [x] The **job detail page** shows the failure reason and how long the job ran (elapsed).
- [x] The **Queue and Shoots pages show a small live indicator** while active — e.g.
      *"Generating… 2 running · 5 queued"* — so progress is visible at a glance.
- [x] Existing Queue polling and the happy path are unchanged; a genuinely successful job
      still completes and writes its scripts.

## Technical Notes

- **Auto-refresh Shoots:** extract the channel tables into `partials/shoots/_list.html`
  with a root `id="shoots-list"`; add `GET /shoots/list` returning it. The page wraps it
  in a poll (`hx-get="/shoots/list" hx-trigger="every 3s"`) that's active only when
  `job_service.count_jobs(status="queued") + count_jobs(status="running") > 0` (pass an
  `active` flag, same pattern as the Queue's `_list`). Status itself stays filesystem-derived.
- **Empty/blocked → failed:** in `gemini_client.generate`, when the response has no text,
  inspect `response.candidates[...].finish_reason` / `response.prompt_feedback` and raise a
  clear error (e.g. `GenerationError("Gemini returned no content — finish_reason=SAFETY")`).
  `run_job`'s existing `except` turns that into `status="failed"` + `error`. (Belt-and-braces:
  `run_job` also treats a blank `text` / empty parse as a failure.)
- **Insight indicator:** a tiny `_activity.html` partial (or inline) showing running/queued
  counts, polled alongside the list; the job detail already renders `job.error` and can show
  `finished_at - started_at`.
- No schema change required (uses existing `status` / `error` / timestamps).

## Testing Plan

~60/30/10. Gemini mocked.

- **Unit:** `gemini_client.generate` raises a clear error when the mocked response has empty
  text (with a finish_reason); `run_job` on an empty response → `status="failed"` with the
  reason (no scripts written, no `script.txt`).
- **Integration:** `GET /shoots` includes the poll attributes when a job is queued/running and
  omits them when idle; a processed empty-response job shows **Failed** + the reason on
  `GET /jobs/{id}`; a normal job still completes.
- **e2e:** the Shoots dashboard shows the live activity indicator with a seeded queued job.

Done when `make check` + `make test-e2e` are green and `ruff`/`mypy` are clean.

## Estimated Complexity

**M** — auto-refresh wiring (mirrors the Queue), the empty/blocked failure path + reason
capture, and a small activity indicator. No schema change.

## Open Question

- Capturing the exact block reason depends on what the `google-genai` response exposes for a
  filtered request; if it's not cleanly available we fall back to the generic
  "no content returned" message.

## Resolution

- **Auto-refresh Shoots:** extracted the channel tables into `partials/shoots/_list.html`
  (root `id="shoots-list"`) and added `GET /shoots/list`. The list polls every 3s only when
  `_queue_state(db)["active"]` (any queued/running job) and shows *"Generating… N running ·
  M queued (auto-refreshing)"*. It lives inside the page `<form>`, so the per-shoot Run
  buttons still submit the shared prompt/model/count picker.
- **Empty/blocked → failed:** `gemini_client.generate` now raises `GenerationError` when the
  response carries no text, with `_block_reason()` reading `prompt_feedback.block_reason` /
  `candidates[0].finish_reason`. `run_job`'s existing `except` turns it into `status="failed"`
  + reason. The "0 parsed scripts" case needs no extra guard: the parser falls back to the
  whole response whenever any text exists, so it can only yield 0 scripts on empty text — and
  that's now intercepted at the client boundary before parsing.
- **Insight:** the Queue `_list` gained the same activity line; the job detail shows
  *"ran for Ns"* (`finished_at − started_at`) once terminal.
- No schema change. Gate green: ruff/mypy clean, unit+integration pass, 6 e2e pass.
