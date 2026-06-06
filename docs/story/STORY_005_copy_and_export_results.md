# STORY_005 — Copy and export results

> Epic: EPIC_001 · Status: Not started

**As** the OnlyGainsTV operator, **I want** to copy any single script to my clipboard and
download a whole run as a `.zip`, **so that** I can paste scripts straight into Veo/Wan or
archive the full set the way I do today with `script1.txt … scriptN.txt`.

Fifth slice of [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md). The scripts
exist (STORY_004); this story makes them easy to *use*.

## Acceptance Criteria

- [ ] Every generated script has a **Copy** button that puts its exact body on the
      clipboard and shows a confirmation toast.
- [ ] A job/run has a **Download `.zip`** action producing `script1.txt … scriptN.txt`
      (ordered, body-only, first char = first char of the script) plus `titles.txt` when present.
- [ ] The zip's filename is derived from the prompt + job (e.g. `video-review-prompt_job12.zip`).
- [ ] Downloading a run with a **single script** yields a one-file zip (`script1.txt`,
      plus `titles.txt` only if titles exist); an unknown job → 404.
- [ ] Copy works from both the **job-detail** page and the **Script library**.

## Technical Notes

- **Per-script copy:** a small button using the existing toast infra. If `app.js` has no
  clipboard helper yet, add one (`navigator.clipboard.writeText` + dispatch the existing
  `toast` event). The button carries the script body (e.g. in a `data-` attribute or copies
  from a hidden node); reuse `toast_trigger`'s client side. No new route required for copy.
- **Run zip export** (`app/routes/jobs.py`): `GET /jobs/{id}/export.zip` → build an
  in-memory zip with Python `zipfile` over a `io.BytesIO`, return a `Response`/
  `StreamingResponse` with `media_type="application/zip"` and a `Content-Disposition:
  attachment; filename="…"` header. Entries: `scriptN.txt` in `order_index` order
  (1-based), then `titles.txt` if the job has titles. Reuse the `_slugify` helper from
  `scripts.py` (or lift it into `routes/common.py`) for the filename.
- **`app/services/job_service.py`** (or a small `export` helper): `build_run_zip(job) ->
  tuple[bytes, str]` returning the zip bytes + filename, so zip assembly is unit-testable
  without the HTTP layer.
- **Templates:** add the Copy button to the script rows/cards (job detail + library) and a
  "Download .zip" button on the job-detail page.

**Out of scope:** per-script individual `.txt` download (zip covers archiving; copy covers
daily use) — add later only if wanted.

## Testing Plan

~70/20/10. All layers apply.

- **Unit** (`tests/unit/test_run_export.py`):
  - `build_run_zip` for a multi-script job → zip contains `script1.txt … scriptN.txt` in
    order with exact bodies, plus `titles.txt`; filename slug correct.
  - single-script job → `script1.txt` only (+ `titles.txt` only if titles present).
- **Integration** (`tests/integration/test_jobs_export.py`, `TestClient`):
  - `GET /jobs/{id}/export.zip` → 200, `application/zip`, `Content-Disposition: attachment`;
    open the returned bytes with `zipfile` and assert the entries/contents.
  - unknown job → 404.
  - (Copy is client-side; assert the Copy button + payload are present in the rendered HTML.)
- **e2e** (`tests/e2e/`) — **required**: on a completed job, click **Copy** on a script
  (assert the toast appears; read the clipboard via Playwright where supported) and click
  **Download .zip** (assert the download is triggered).

Done when `make check` + `make test-e2e` are green and `ruff`/`mypy` are clean.

## Estimated Complexity

**M** — straightforward zip building + a clipboard button; the only nuance is the e2e
clipboard/download assertions.
