# STORY_033 — Jobs stuck in "Running" recover when the app starts

> Epic: — · Status: Done · Fixes: [BUG_007](../bug/BUG_007_stuck_running_job_never_recovers_after_restart.md)

**As** the OnlyGainsTV operator, **I want** a job that was left mid-run by a
crash or redeploy to be closed out automatically on the next startup **so
that** the queue reflects reality — no phantom "Generating… 1 running" banner
polling forever (job #6 has shown that since Aug 15).

## Acceptance Criteria

- [x] On worker startup, every job still marked `running` is moved to
      `failed` with a clear error note saying it was interrupted by a restart.
- [x] Recovery **never re-queues** the job automatically — re-running spends
      paid model calls, so that stays an explicit operator action (e.g. the
      shoot's Re-run button).
- [x] The Queue/Shoots "Generating…" banner clears once the orphan is
      recovered; the job's detail page shows the failed state and the note.
- [x] Genuinely queued/done/failed jobs are untouched, and recovery is a
      no-op when there is nothing to recover.

## Technical Notes

- Why startup is safe to judge this: there is exactly **one** worker and it
  lives in this process ([app/services/job_worker.py](../../app/services/job_worker.py)),
  so at `start()` time a `running` row cannot actually be running — its
  process died (BUG_007's root cause).
- [app/services/job_service.py](../../app/services/job_service.py) — new
  `recover_orphaned_running_jobs(db)` marking orphans `failed` with the note
  and a `finished_at`, mirroring how `run_job` fails a job.
- [app/services/job_worker.py](../../app/services/job_worker.py) — `start()`
  runs the recovery synchronously (own session, exception-guarded) before the
  polling thread spawns. Tests never start the worker, so nothing changes
  under test unless a test calls `start()` deliberately.
- Routes / templates / domain vocab / config / schema impact: none (the
  existing `failed` state + error display do the rendering).

## Testing Plan

- **Unit** (`tests/unit/test_job_service.py`): a `running` job is failed with
  the note and a `finished_at`; `queued`/`done` jobs are untouched; the count
  is returned; a second run recovers nothing.
- **Integration** (`tests/integration/test_jobs.py`): with an orphaned
  `running` job seeded, `job_worker.start()` (stopped again immediately)
  recovers it — the queue page stops reporting a running job and shows Failed,
  and the detail page surfaces the interruption note.
- **e2e**: N/A — reproducing the trigger means killing and restarting the app
  process mid-suite, which the shared session-scoped live server can't do; the
  recovery logic is fully covered above and the UI it feeds (queue banner,
  failed badge, error note) is already exercised by existing e2e/integration
  tests.

## Estimated Complexity

S — one service function + three guarded lines in `start()`; the failure
rendering already exists.
