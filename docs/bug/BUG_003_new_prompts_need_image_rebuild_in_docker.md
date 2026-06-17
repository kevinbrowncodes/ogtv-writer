# BUG_003 — New prompt files don't appear in the Dockerized app without an image rebuild

> Status: Resolved

## Summary

The Prompt library UI tells the operator "Drop a `.md` file in that folder to add one,"
and the file-based catalog ([prompt_catalog.py](../../app/services/prompt_catalog.py))
reads `app/static/prompts/` live on every request. But when the app runs in Docker — the
everyday way it's deployed — a newly dropped prompt never shows up, because the container
serves a copy of the folder baked into the image at build time, not the host folder.

## Steps to Reproduce

1. Run the app in Docker: `make docker-up` (serves http://localhost:9001).
2. Drop a new brief into the host folder, e.g. `app/static/prompts/cosmos-scene.md`.
3. Open **Prompts** in the UI and hard-refresh.

## Expected vs Actual Behaviour

- **Expected:** the new prompt appears in the library on refresh, matching the in-app
  hint "Drop a `.md` file in that folder to add one."
- **Actual:** the new prompt is absent. `docker exec ogtv-writer-web-1 ls
  /app/app/static/prompts/` shows only the files that existed when the image was last
  built; the host's new file is not there.

## Root Cause

The [Dockerfile](../../Dockerfile) copies the source tree in at build time
(`COPY app ./app`), and [docker-compose.yml](../../docker-compose.yml) only bind-mounts
`./data`. The container's `app/static/prompts/` is therefore a frozen, build-time snapshot
— the host folder and the container folder are two different directories. The catalog
reads live, but it reads the *container's* copy, which never changes until the image is
rebuilt. The fix is a config change, not new code, so it stays a bug ticket (no story).

## Acceptance Criteria

- [x] The prompts folder is bind-mounted into the container so the host folder is the
      single source of truth at runtime.
- [x] After `make docker-up`, dropping a `.md` into `app/static/prompts/` makes it appear
      in the UI on refresh — no image rebuild.
- [x] The mount is read-only (the app only reads prompts), so the container can never
      modify host prompt files.
- [x] README's "prompt files are baked into the image" gotcha is corrected to reflect the
      live mount. _(Test layers — unit/integration/e2e — are N/A: this is an
      infra/compose-only change with zero Python delta; the catalog's existing coverage
      already exercises reading the folder. Verified operationally instead, below.)_

---

## Resolution

Added a read-only bind mount of the host prompts folder to the `web` service in
[docker-compose.yml](../../docker-compose.yml):

```yaml
- ./app/static/prompts:/app/app/static/prompts:ro
```

This shadows the image's build-time copy with the live host directory, so the file-based
catalog reads the same files the operator edits. Recreated the container with
`make docker-up` and verified end-to-end: with the container already running, dropping a
new `.md` into `app/static/prompts/` made it appear in `GET /prompts` and inside the
container (`docker exec … ls`) with **no rebuild**; removing the file made it disappear
again. The README Docker section was updated to describe the live mount instead of the old
"rebuild after every prompt edit" workaround. No automated test layer added — the change
is in Compose configuration, not app code (same rationale as BUG_002).
