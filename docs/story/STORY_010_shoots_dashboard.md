# STORY_010 — Run pending shoots from a channel dashboard

> Epic: — (follow-on, **depends on** [STORY_009](STORY_009_folder_based_jobs.md)) · Status: Done

**As** the OnlyGainsTV operator, **I want** a view that shows my logline shoots grouped
by channel and lets me **Run** the ones that don't have a script yet — picking the
prompt/model at that moment — **so that** I can clear my pipeline without hand-creating a
job for each folder.

Builds on STORY_009's folder-based job engine. A new **Shoots** page scans
`data/logline/<channel>/<shoot>/`, marks each shoot Done / Pending / No-frame, and turns
each pending shoot into a one-click **Run** (which creates a folder job that writes the
script back into the shoot folder).

## Approach (confirmed)

- **Channels = the folder level** under `SOURCE_ROOT` (e.g. `only-gains-tv`, `youtube`);
  **shoots = the dirs inside them** (e.g. `26-06-07-0200_orange-phone`).
- **Status per shoot:** *Done* if the folder already has a script file
  (`script.txt`/`script1.txt`…), *Pending* if it has a frame but no script, *No-frame* if
  there's no `01.<ext>` image (shown but not runnable).
- **Choose at run time:** a prompt + model + count picker (pre-filled with sensible
  defaults) sits on the page; **Run** (per shoot) and **Run all pending** use the current
  selection. Nothing fires on its own — you hit the buttons.
- Each Run creates a STORY_009 folder job for that shoot → generates → writes the
  script(s) back into the folder → the shoot flips to Done.

## Acceptance Criteria

- [x] A **Shoots** page (new nav item) lists shoot folders under `SOURCE_ROOT`, **grouped
      by channel**, each showing its frame name and status (Done / Pending / No-frame).
- [x] A **prompt + model + count** picker (defaults pre-filled) controls what Run uses;
      the count field appears only for `{{COUNT}}` prompts (as on the New-job form).
- [x] **Pending** shoots show a **Run** button; each channel (and/or the page) has a **Run
      all pending** that queues a folder job for every pending shoot with the current picker.
- [x] Hitting Run **creates a folder job** (STORY_009) for that shoot — it appears in the
      queue, generates, and writes the script(s) into the shoot folder; the shoot becomes Done.
- [x] **No-frame** shoots are shown but not runnable (clear "needs a frame" state); a
      **Done** shoot shows it already has a script (with a way to re-run if wanted).
- [x] The page reflects status changes (a manual refresh is fine; live update is a bonus).
- [x] Path-safe: only shoots inside `SOURCE_ROOT` are listed/runnable.

## Technical Notes

- **`app/services/shoots.py`** (extends STORY_009): `list_by_channel() -> dict[str,
  list[Shoot]]` where `Shoot` carries `rel_dir`, `channel`, `name`, `frame` (or `None`),
  and `status` (`done` / `pending` / `no_frame`). Status: *done* if a `script*.txt` exists,
  *pending* if a frame exists and no script, else *no_frame*.
- **`app/routes/shoots.py`** (new): `GET /shoots` (the dashboard), `POST /shoots/run`
  (one shoot — body: `source_dir`, `prompt_slug`, `model`, `count`), `POST /shoots/run-all`
  (all pending in a channel/page with the current picker). Each validates the shoot via
  `shoots.resolve` and creates a folder job through `job_service.create_job` (reusing the
  STORY_009 path), then redirects/refreshes.
- **Picker** reuses `prompt_catalog.list_prompts()` + `generation_service.available_models()`
  + `price_label`; the count field reuses `partials/jobs/_count_field.html` logic.
- **Nav:** add a **Shoots** item in `_sidebar.html`.
- No new Job fields beyond STORY_009 (`source_dir` / `output_files`); a "Done" shoot is
  simply one whose folder already has a script file.
- **Frame:** the frame is `01.<ext>` (jpg/jpeg/png/webp) **only**; other images like
  `seed.jpg` are ignored, so a folder with no `01.*` is *No-frame* (not runnable).

## Testing Plan

~60/30/10. Gemini mocked; filesystem against a `tmp_path` `SOURCE_ROOT`.

- **Unit** (`tests/unit/test_shoots.py`, extending STORY_009's): `list_by_channel` groups
  by channel and classifies status — *done* (folder has `script1.txt`), *pending* (frame,
  no script), *no_frame* (only `seed.jpg`). A re-run on a Done shoot is allowed.
- **Integration** (`tests/integration/test_shoots.py`, `SOURCE_ROOT` → tmp with seeded
  channels/shoots):
  - `GET /shoots` lists channels + shoots with correct statuses.
  - `POST /shoots/run` for a pending shoot → a queued folder job for that `source_dir`;
    processing (Gemini mocked) writes the script into the folder and the shoot reads Done.
  - `POST /shoots/run-all` queues one job per pending shoot; Done/No-frame shoots are skipped.
  - A No-frame shoot can't be run (422 / not offered).
- **e2e** (`tests/e2e/`): seed channels/shoots under the e2e `SOURCE_ROOT`; `/shoots` shows
  them grouped with statuses, the picker is present, and a pending shoot's Run queues a job.

Done when `make check` + `make test-e2e` are green and `ruff`/`mypy` are clean.

## Estimated Complexity

**M–L** — mostly a new read-only dashboard + run actions on top of STORY_009's engine.
The work is the status classification, channel grouping, the run/run-all actions, and the
picker wiring.

## Open Questions

- Should **Run all** use one picker selection for the whole batch (proposed), or allow a
  per-shoot prompt/model override? (Per-shoot override is a likely later refinement.)
