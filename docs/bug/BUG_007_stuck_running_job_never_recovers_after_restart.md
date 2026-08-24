# BUG_007 — A job stuck in "Running" never recovers after a restart

> Status: Resolved

## Summary

If the app (or its Docker container) dies or is redeployed while a generation job
is `running`, that job stays `running` in the database forever. The Queue and
Shoots pages then show "Generating… 1 running · 0 queued (auto-refreshing)"
permanently and poll every 3 seconds, and the job never completes or fails.

Observed live on 2026-08-24: job **#6** had been "Running" since **Aug 15** —
nine days — and survived a `make deploy` container recreation still marked
running.

## Steps to Reproduce

1. Queue a job and wait for the worker to mark it `running`.
2. Kill the process / recreate the container before the job finishes
   (`make deploy` or `docker compose up -d --force-recreate`).
3. Open the Queue or Shoots page after the restart.

## Expected vs Actual Behaviour

- **Expected:** on startup the app notices the orphaned `running` job (its
  worker thread no longer exists) and re-queues it — or marks it failed with a
  clear error — so the queue banner reflects reality.
- **Actual:** the job stays `running` forever; the "Generating… 1 running"
  banner and 3-second HTMX polling never stop.

## Root Cause

The single in-process worker
([app/services/job_worker.py](../../app/services/job_worker.py)) only ever
claims the oldest **`queued`** job. Nothing at startup (or anywhere else)
resets rows left in `running` by a dead process, so an orphaned running job is
unreachable: the worker skips it and no UI action can retry or fail it.

Since there is exactly one worker and it lives in this process, any job found
`running` at startup is by definition orphaned — safe to re-queue (or fail)
during app startup / worker start.

## Acceptance Criteria

- [x] On startup, jobs left in `running` are recovered (re-queued or marked
      failed with a note) — the steps above no longer leave a phantom job.
- [x] The Queue/Shoots banner reflects the recovered state without manual
      database surgery.
- [x] A regression test covers recovery (unit: worker/startup recovery
      function; integration: a seeded `running` job is recovered when the app
      starts).

---

## Resolution

Fixed by [STORY_033](../story/STORY_033_stuck_running_jobs_recover_on_startup.md):
`job_worker.start()` now runs `job_service.recover_orphaned_running_jobs()`
before the polling thread spawns, marking any `running` job **failed** with a
clear "interrupted by an app restart" note (never re-queued — re-running spends
paid model calls, so that stays an explicit operator action). Covered by three
unit tests and one integration test. Deploying this build recovered job #6
(stuck since Aug 15) and cleared the phantom "Generating… 1 running" banner.
