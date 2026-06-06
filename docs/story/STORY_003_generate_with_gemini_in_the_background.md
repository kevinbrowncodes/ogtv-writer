# STORY_003 — Generate with Gemini in the background

> Epic: EPIC_001 · Status: Done

**As** the OnlyGainsTV operator, **I want** queued jobs to be sent to Gemini
automatically in the background, **so that** I can submit a batch and walk away while my
scripts get written.

Third slice of [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md), and the one
that makes the queue real. It wires up the **Gemini multimodal call**, an **in-process
worker** that drains the queue, and stores each job's **raw response** + status. It also
**removes the old deterministic generator** (and the routes that depend on it). Parsing
the response into individual scripts is the next story (STORY_004) — here we just capture
the raw text.

## Acceptance Criteria

- [x] A queued job is picked up automatically, sent to **Gemini** with the assembled
      prompt **and the uploaded image**, and its raw text response + status are stored.
- [x] Status moves `queued → running → done` on success, or `→ failed` (with the error
      message saved) on failure; `started_at` / `finished_at` are recorded.
- [x] The **assembled prompt** = catalog prompt body, with `{{COUNT}}` replaced by the
      job's count (when present), the **addendum** appended under a clear delimiter, and a
      small app output-contract wrapper (prototype for STORY_004's parser).
- [x] The **queue and job-detail pages reflect status live** (HTMX polling) without a manual refresh.
- [x] **Tests never make a live Gemini call** — the client is mocked at the boundary.
- [x] With **no `GEMINI_API_KEY` set**, the app still starts; jobs fail fast with a clear
      "no API key configured" error rather than crashing the worker.
- [x] The old deterministic generator and the `/generate` page + `/scripts/{id}/variations`
      action are removed; the app, `ruff`, and `mypy` stay green afterward.

## Technical Notes

- **Config** (`app/config.py` + `.env.example`): add `gemini_api_key: str = ""` and
  `gemini_model: str = "gemini-2.5-flash"`. Dependency: add `google-genai` to
  `pyproject.toml` runtime deps.
- **`app/services/gemini_client.py`** — the only thing that touches the SDK. A thin
  `generate(*, prompt: str, image_bytes: bytes, image_mime: str, model: str) -> str`
  that builds the request (text part + inline image part) and returns the response text.
  Keep it tiny so tests patch this one function / a module-level client object.
- **`app/services/generation_service.py`** — **replace** its deterministic internals with:
  - `assemble_prompt(body: str, *, count: int | None, addendum: str) -> str` — `{{COUNT}}`
    substitution, addendum under `\n\n## Additional details for this job\n…`, and the
    app output contract (e.g. wrap each script in `<<<SCRIPT n>>> … <<<END SCRIPT>>>`,
    titles in `<<<TITLES>>>…`, summary in `<<<SUMMARY>>>…`). Finalized in STORY_004.
  - `run_job(db, job) -> None` — load prompt body from `prompt_catalog`, read the image
    from `job.image_path`, `assemble_prompt`, call `gemini_client.generate`, store
    `result_raw` + flip status/timestamps. Catch exceptions → `failed` + `error`.
- **Worker** (`app/services/job_worker.py`): an in-process background worker started in
  `main.py`'s `lifespan`. A daemon `threading.Thread` loops: claim the oldest `queued`
  job (mark `running` in its own `SessionLocal()`), call `run_job`, sleep briefly, repeat;
  stop on a shutdown `threading.Event`. **Sequential (concurrency = 1)** for v1 to respect
  rate limits. Keep the unit of work (`process_next_job(db)`) a plain function so tests
  call it directly; **do not start the polling thread during tests** (guard on
  `settings.is_testing`).
- **Routes** (`app/routes/jobs.py`): add `GET /jobs/{id}` (detail: status + raw result)
  and `GET /jobs/{id}/status` (HTMX polled partial). The queue rows poll for status too.
- **Removals (per epic):** delete the lens/format machinery, `build_script_body()`,
  `app/routes/generate.py` + `pages/generate.html`, and the `/scripts/{id}/variations`
  handler (+ its UI control). Drop their includes/links and the obsolete
  `tests/integration/test_generate.py` / `tests/unit/test_generation_service.py` (replaced
  by the new tests below). `Script`'s `target_model`/`output_format` columns stay until STORY_006.

**Out of scope:** splitting `result_raw` into scripts/titles/summary (STORY_004), retries
(follow-on), Script creation from output.

## Testing Plan

~70/20/10. All layers apply; **e2e of the live call is N/A** (see below).

- **Unit** (`tests/unit/test_generation_service.py`, `tests/unit/test_job_worker.py`):
  - `assemble_prompt`: `{{COUNT}}` → number; addendum appended; no-count + no-addendum case;
    output-contract wrapper present.
  - `run_job` with a **mocked** `gemini_client.generate`: stores `result_raw`, status `done`,
    timestamps set; when the client raises → status `failed`, `error` populated.
  - missing `GEMINI_API_KEY` → job fails with the clear message, worker keeps running.
  - `process_next_job` claims the oldest queued job and is a no-op when the queue is empty.
- **Integration** (`tests/integration/test_jobs_processing.py`, `TestClient`, Gemini mocked):
  - create a job, run `process_next_job`, assert `GET /jobs/{id}` shows `done` + raw result;
    `GET /jobs/{id}/status` returns the right partial.
  - assert **no live network call** (the mock is the only boundary that's hit).
- **e2e** (`tests/e2e/`): the job-detail/status **page renders** for a job (status badge,
  polling element present). **The actual generation is N/A for e2e** — it needs a live,
  paid Gemini key and would violate the CLAUDE.md cost rule; covered by mocked integration
  tests instead. Stated here per §3.

## Estimated Complexity

**L** — first external API integration **and** a background worker **and** removal of the
old generator. Threading + a clean test seam (mock the client, don't run the loop in tests)
are the main risks.
