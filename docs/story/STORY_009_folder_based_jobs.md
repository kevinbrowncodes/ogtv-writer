# STORY_009 — Run jobs from a shoot folder and save scripts back into it

> Epic: — (follow-on to [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md)) · Status: Done

**As** the OnlyGainsTV operator, **I want** to point a job at a shoot folder that already
holds the first frame and have the generated script(s) written **back into that same
folder** — while still being able to upload a one-off frame when I want — **so that** my
files live where I organize them
(`data/logline/only-gains-tv/<shoot>/01.jpg` → `…/<shoot>/script.txt`).

This **adds a source-folder mode alongside the existing upload**. A folder job reads the
frame from the folder and writes the produced scripts to disk in it (mirroring the manual
workflow — `01.jpg` in, `script.txt` / `script1..N.txt` + `titles.txt` out). An uploaded
job behaves exactly as today (stored in the library, downloadable). **Upload is kept, not
removed.**

## Approach (confirmed)

**Two input modes, your pick per job.** A configured root (`SOURCE_ROOT`, default
`data/logline`) holds one folder per shoot, each containing a frame (`01.jpg`). On the
New-job form you choose **Upload** (as today) or **Source folder**. For a folder job the
worker reads the frame from the folder and writes the outputs back into it; an upload job
keeps today's behavior (image copied to `data/uploads/`, no disk write-back).

## Acceptance Criteria

- [x] The New-job form offers an **image source** choice: **Upload an image** (as today)
      or a **Source folder** picker listing shoot folders under `SOURCE_ROOT` that contain
      a frame (the detected frame is shown).
- [x] An **upload** job behaves exactly as today — image saved under `data/uploads/`,
      scripts in the library and downloadable; nothing regresses.
- [x] A **folder** job reads the frame **from the folder** (no copy) and, on completion,
      writes the script(s) **into that folder**: one → `script.txt`; N → `script1.txt …
      scriptN.txt`; plus `titles.txt` / `summary.md` when present. Re-running overwrites them.
- [x] The frame is `01.<ext>` (jpg/jpeg/png/webp) **only** — a folder with no `01.*` is
      not a valid source; other images (e.g. `seed.jpg`) are ignored, no fallback.
- [x] Path safety: a chosen folder must resolve **inside `SOURCE_ROOT`**; traversal, an
      outside-root path, or a folder with no frame → `422`, nothing queued, nothing written
      outside the root.
- [x] The job detail page shows the source (uploaded image, or the folder + the files
      written there); the library + copy + `.zip` download are unchanged for both modes.
- [x] If `SOURCE_ROOT` has no eligible folders, the folder picker shows a clear empty
      state — and Upload still works.

## Technical Notes

- **Config:** add `source_root: str = "data/logline"` to `Settings` + `.env.example`,
  resolved under the repo root (reuse `uploads.PROJECT_ROOT`).
- **`app/services/shoots.py`** (new):
  - `list_shoots() -> list[Shoot]` — scan `SOURCE_ROOT` for leaf dirs containing a frame;
    `Shoot = (rel_dir, frame_name)`, `rel_dir` repo-relative (e.g.
    `data/logline/only-gains-tv/26-06-07-0100_brown`).
  - `resolve(rel_dir) -> Shoot | None` — path-traversal safe (must be inside `SOURCE_ROOT`),
    returns the shoot + resolved frame or `None`; `_find_frame` matches `01.<ext>` only (no fallback).
  - `write_outputs(rel_dir, scripts, titles, summary) -> list[str]` — write
    `script.txt`/`scriptN.txt` (+ `titles.txt`, `summary.md`) into the folder; return the
    filenames written.
- **`Job`:** add `source_dir: str` (repo-relative folder; `""` for upload jobs) and
  `output_files: str` (newline-joined, set for folder jobs). `image_path` is the upload
  copy (upload mode) or the resolved frame inside the shoot folder (folder mode).
- **`app/services/uploads.py`:** **kept** — upload mode still uses `save_upload`.
- **`app/routes/jobs.py`:** the form provides both controls (toggled by an `image_source`
  radio). `POST /jobs` accepts either an uploaded `image` or a `source_dir`; validate that
  exactly one is supplied and valid (folder via `shoots.resolve`), else 422.
- **`generation_service.run_job`:** unchanged generation; after creating the Script rows,
  **if `job.source_dir`** → `shoots.write_outputs(...)` and store `job.output_files`.
- **Templates:** an `image_source` radio on `job_new.html` toggling the file input vs the
  Source-folder `<select>` (HTMX swap or a touch of JS); show the source + any written
  files on `job_detail.html`.

**Out of scope:** an in-browser folder *browser* (a `<select>` of discovered folders is
enough); a filesystem watcher that auto-runs jobs; writing anywhere outside `SOURCE_ROOT`.

## Testing Plan

~60/30/10. Gemini mocked; file I/O against a `tmp_path` `SOURCE_ROOT`.

- **Unit:**
  - `tests/unit/test_shoots.py`: `list_shoots` finds leaf dirs with a frame and ignores
    those without; `_find_frame` prefers `01.jpg`, falls back to first image; `resolve`
    rejects traversal / outside-root / frameless folders; `write_outputs` → `script.txt`
    for one, `script1..N.txt` for many, `titles.txt`/`summary.md` only when present, and
    overwrites on re-run.
  - Keep `tests/unit/test_uploads.py` (upload mode unchanged).
  - Extend `run_job` tests: a folder job writes files into the shoot folder + sets
    `output_files`; an upload job writes nothing to a shoot folder.
- **Integration** (`tests/integration/test_jobs.py`, `SOURCE_ROOT` monkeypatched to a tmp
  dir with a seeded shoot):
  - `GET /jobs/new` shows both the upload control and the folder picker (lists the shoot).
  - Upload path: existing happy/invalid cases still pass (no regression).
  - Folder path: `POST /jobs` with a valid `source_dir` → queued; unknown/empty/traversal
    folder → 422; processing (Gemini mocked) writes scripts into the folder; detail shows them.
- **e2e** (`tests/e2e/`): seed a shoot under the e2e `SOURCE_ROOT`; `/jobs/new` shows the
  source toggle + folder picker; submit a folder job (stays queued, worker off) — file
  writing is covered by unit/integration.

Done when `make check` + `make test-e2e` are green and `ruff`/`mypy` are clean.

## Estimated Complexity

**L** — adds a second input mode (folder) with filesystem scanning + safe output writing,
new `Job.source_dir`/`output_files`, a form toggle, and tests for both modes — without
disturbing the existing upload path. The fiddly parts are path-safety and the output
filename scheme.
