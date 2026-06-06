# STORY_007 — Choose which Gemini model a job uses

> Epic: — (follow-on to [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md)) · Status: Done

**As** the OnlyGainsTV operator, **I want** to pick which Gemini model a job runs
on, from the models my API key can actually access, **so that** I can trade speed
and cost against quality per run (e.g. `flash` for a quick batch, `pro` for a hero
script) without editing `.env`.

Today the model is a single `GEMINI_MODEL` env value used for every job. This adds a
**Model** picker to the New-job form, populated by **pulling the live model list**
from the Gemini API, with **reference token pricing** shown per model, and records
the chosen model on the job so the worker uses it.

## Approach (confirmed)

**Per-job** selection — a Model dropdown on `/jobs/new`. The configured `GEMINI_MODEL`
is **always pre-selected as the default**, so you only change it when you want to; the
choice is stored on each `Job`. (A single global default on the Settings page was
considered and set aside as less granular.)

> **Pricing caveat:** the Gemini API does **not** expose pricing, so prices can't be
> pulled live. We show a **hand-maintained reference table** (per-model $/1M tokens),
> clearly labelled as approximate — the operator verifies current numbers against
> [ai.google.dev/pricing](https://ai.google.dev/gemini-api/docs/pricing). The model
> *list* is live; only the *prices* are static.

## Acceptance Criteria

- [x] The New-job form shows a **Model** dropdown listing the Gemini models the
      configured key can use, with `GEMINI_MODEL` pre-selected as the default.
- [x] The list is **pulled live** from the Gemini API and limited to models that
      support text generation (`generateContent`) — i.e. ones this app can use.
- [x] Each model shows **reference token pricing** (input / output per 1M tokens)
      from a hand-maintained table, labelled "approx · verify"; a model with no known
      price shows "—" (and is still selectable).
- [x] The chosen model is **stored on the job** and used by the worker for that
      job's Gemini call (overriding the env default); the job detail page shows it.
- [x] **Graceful fallback:** if the list can't be fetched (no key / API error /
      offline), the form still renders with at least the configured default
      selectable — it never errors out.
- [x] The model list is **cached** (not re-fetched from the API on every form load).
- [x] A submitted model not in the available set is rejected (422, form re-rendered)
      or falls back to the default — never passed blindly to the API.

## Technical Notes

- **`app/services/gemini_client.py`** — add `list_models(api_key: str) -> list[str]`:
  lazy-import the SDK, `genai.Client(api_key=api_key).models.list()`, keep models
  whose supported actions include `generateContent`, return their bare names (e.g.
  `gemini-2.5-flash`). Tolerant: return `[]` on any error (caller handles fallback).
- **`app/services/generation_service.py`** (or a small `model_catalog` helper) —
  `available_models() -> list[str]`: returns a **cached** list (process-lifetime or a
  short TTL; models change rarely). On empty/failure, fall back to a list containing
  at least `settings.gemini_model`. Provide a way to bypass/refresh in tests.
- **Pricing** — a hand-maintained `GEMINI_PRICING` table in `app/domain.py`
  (`{model: {"input": float, "output": float}}`, USD per 1M tokens) plus a
  `price_label(model) -> str` helper (e.g. `"$0.30 in / $2.50 out · per 1M tok"`, or
  `"—"` when unknown). Seed it from
  [ai.google.dev/pricing](https://ai.google.dev/gemini-api/docs/pricing) and treat it
  as reference-only. The form receives `(model, price_label(model))` pairs.
- **`Job`** — add a `model` column (`String(60)`, default `""`). `run_job` uses
  `job.model or get_settings().gemini_model` for the Gemini call.
- **`app/routes/jobs.py`**:
  - `job_new_page` passes `models = available_models()` and `default_model = settings.gemini_model`.
  - `jobs_create` accepts a `model` form field; validate it against `available_models()`
    (fall back to the default if blank, reject/whitelist otherwise); pass to `create_job`.
  - `job_detail` / `_status.html` surface the model used.
- **Templates** — add the Model `<select>` to `pages/job_new.html`, each option
  labelled `"{model} — {price_label}"` with the default pre-selected; show the chosen
  model (and its price) on the job detail, with the "approx · verify" caveat near it.
- **Config** — `GEMINI_MODEL` stays the default/fallback. No new env var required.

**Out of scope:** a global default-model setting on the Settings page; **live /
programmatic pricing** (the API doesn't expose it — the table is hand-maintained);
**estimated per-run cost** (needs token estimates); per-model quota display;
non-Gemini providers.

## Testing Plan

~70/20/10. Gemini is mocked — no live, paid calls.

- **Unit** (`tests/unit/`):
  - `gemini_client.list_models` (mock `client.models.list`): filters to `generateContent`
    models, returns names; returns `[]` on exception.
  - `available_models()`: returns the fetched list; **falls back to `[default]`** when
    the fetch is empty/raises; caches (second call doesn't re-hit the client).
  - `run_job` uses `job.model` when set, else the env default (extend the existing
    `run_job` test with a mocked client asserting the model passed through).
  - `price_label`: formats a known model's price; returns "—" for an unknown model.
- **Integration** (`tests/integration/`, `available_models` patched to a known list):
  - `GET /jobs/new` → the Model `<select>` lists the models, default pre-selected,
    with a known model's reference price shown.
  - `POST /jobs` with a valid chosen model → stored on the job; worker (run via
    `process_next_job`, Gemini mocked) uses it; `GET /jobs/{id}` shows it.
  - `POST /jobs` with an unknown model → 422 (or documented fallback), nothing bad sent.
- **e2e** (`tests/e2e/`): on `/jobs/new` the **Model dropdown is present** with the
  default option (in the test env there's no key, so it falls back to the default —
  which validates the graceful-fallback path in a real browser).

Done when `make check` + `make test-e2e` are green and `ruff`/`mypy` are clean.

## Estimated Complexity

**M** — a live "list models" call + caching + graceful fallback, a new `Job.model`
column, and form/validation wiring. The fiddly parts are caching and never breaking
the form when the API is unavailable.
