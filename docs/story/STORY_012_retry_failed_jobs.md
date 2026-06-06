# STORY_012 — Retry a job a few times before giving up

> Epic: — (follow-on, pairs with [STORY_011](STORY_011_live_progress_and_clear_failures.md)) · Status: Not started

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

- [ ] A job that fails with a **transient** error is retried up to `MAX_ATTEMPTS` total, with a
      short backoff between tries; if it eventually succeeds, it's `done` as normal.
- [ ] After exhausting attempts, the job is `failed` with the **last** error message.
- [ ] The job records its **attempt count**, surfaced on the detail page (e.g. "failed after 3
      attempts") and usable by STORY_011's live view ("attempt 2 of 3").
- [ ] A **content block / empty response is not retried** — it fails immediately with the
      clear reason from STORY_011.
- [ ] Tests never make real calls and never actually sleep for the full backoff (backoff is
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
