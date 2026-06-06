# STORY_012 — Retry a job a few times before giving up

> Epic: — (follow-on, pairs with [STORY_011](STORY_011_live_progress_and_clear_failures.md)) · Status: Done

**As** the OnlyGainsTV operator, **I want** a job to retry a few times before it's marked
failed, **so that** a transient hiccup (a rate-limit, a network blip, a one-off 5xx)
doesn't kill a run that would have worked on the second try.

## Approach (confirmed)

The worker retries a failing job up to **`MAX_ATTEMPTS` (default 3)** with a short backoff
before marking it `failed` with the last error. The job records how many attempts it took.

**What to retry (decided): transient errors only.** Network / rate-limit / 5xx / timeout
errors are retried; a **content block / empty response** (from STORY_011) is **terminal** —
it fails immediately, since the same prompt+frame blocks deterministically and retrying just
burns paid calls.

## Acceptance Criteria

- [x] A job that fails with a **transient** error is retried up to `MAX_ATTEMPTS` total, with a
      short backoff between tries; if it eventually succeeds, it's `done` as normal.
- [x] After exhausting attempts, the job is `failed` with the **last** error message.
- [x] The job records its **attempt count**, surfaced on the detail page (e.g. "failed after 3
      attempts") and usable by STORY_011's live view ("attempt 2 of 3").
- [x] A **content block / empty response is not retried** — it fails immediately with the
      clear reason from STORY_011.
- [x] Tests never make real calls and never actually sleep for the full backoff (backoff is
      injected/short in tests).

## Technical Notes

- **Config:** `max_attempts: int = 3` (+ `.env.example`); a small backoff helper (e.g.
  `2 ** (attempt - 1)` seconds, capped), overridable for tests.
- **`Job`:** add `attempts: int` (default 0) — needs a migration (`make migration`).
- **Classify errors:** mark which exceptions are transient vs terminal. Simplest: a
  `RetryableError` vs the content-block error from STORY_011 (terminal). The Gemini client
  raises the appropriate type; `run_job` retries only retryable ones.
- **Retry loop:** in `run_job` (or a thin wrapper), loop attempts: try → on retryable error,
  increment `attempts`, sleep backoff, retry; on terminal error or success, stop. Persist
  `attempts` and final status. Sequential worker, so the (short) backoff just delays that one job.
- Surface `attempts` on `job_detail` and in STORY_011's activity/indicator.

## Testing Plan

~70/20/10. Gemini mocked; backoff patched to ~0.

- **Unit:** `run_job` with a client that fails twice then succeeds → `done`, `attempts == 3`;
  a client that always fails (transient) → `failed` after `MAX_ATTEMPTS`, last error stored;
  a terminal (content-block) error → `failed` with `attempts == 1` (not retried).
- **Integration:** a job that needs a retry still ends up `done` and writes its scripts;
  the detail page shows the attempt count.
- **e2e:** N/A (retry/backoff is internal, no visible flow change) — justified per §3.

## Estimated Complexity

**M** — a retry loop + error classification + an `attempts` column/migration. The main care
is transient-vs-terminal classification and keeping tests fast (no real sleeps).

## Resolution

- **Config:** added `max_attempts: int = 3` (`app/config.py` + `.env.example` `MAX_ATTEMPTS`).
- **Classify (in `gemini_client`):** new `RetryableError` (transient) alongside the terminal
  `GenerationError`. `_is_transient(exc)` retries on HTTP 408/409/425/429/5xx or transport
  errors whose type name signals timeout/connection/unavailable/deadline/rate-limit; everything
  else (4xx, bad-config) is terminal. `generate()` wraps a transient SDK error as
  `RetryableError` and re-raises the rest.
- **Retry loop:** `generation_service._generate_with_retries()` loops up to `max_attempts`,
  bumping `job.attempts` and committing between tries (so STORY_011's live view shows
  "attempt N of M"), with `_backoff_seconds(n)` = 1,2,4,… capped at 30s via a patchable
  `_sleep()`. A content block raises immediately → `attempts == 1`, no retry.
- **Schema:** added `Job.attempts` (`Integer`, `server_default="0"`) + migration
  `c3f1a2b4d5e6_add_job_attempts` (applied to the dev DB; `alembic check` drift test passes).
- **UI:** the job detail status block shows "Retrying… attempt N of M" while running,
  "ran for Ns · N attempts" once done, and "Failed after N attempts." on the error.
- Gate green: ruff/mypy clean, unit+integration pass, 6 e2e pass. Backoff patched to zero in
  tests; Gemini mocked — no live calls, no real sleeps.
