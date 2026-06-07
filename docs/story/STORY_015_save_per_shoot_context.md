# STORY_015 — Per-shoot context that sticks (saved with the shoot)

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** the extra context I write for a shoot to be
saved with that shoot **so that** I can reopen and edit it, see at a glance which shoots
have a note, and have every run of that shoot reuse it — instead of it vanishing each
time I close the editor.

Supersedes the one-time behaviour added in
[STORY_014](STORY_014_extra_prompt_context_on_the_shoots_dashboard.md): the note now
persists per shoot rather than applying to a single run.

## Acceptance Criteria

- [x] A shoot's context is stored with the shoot (a `context.txt` in its folder) and survives closing/reopening the editor and page reloads.
- [x] Reopening **✎ Context** shows the saved text, pre-filled and editable; saving empty clears it (removes the file).
- [x] A shoot that has context shows a visible indicator (badge) and its button reads **✎ Context** (vs **+ Context** when none).
- [x] Saving happens in the modal (a **Save** button) without leaving the page; on save the dashboard reflects the new badge and the modal closes.
- [x] **Run**, **Re-run**, and **Run all pending** automatically use each shoot's saved context as the job `addendum` (so a batch run gives every shoot its own note). No context form field is submitted by the run buttons.
- [x] Over-long context (> 20000 chars, the `JobCreate.addendum` bound) is prevented in the editor (`maxlength`) and rejected server-side; nothing is saved.
- [x] Path-safety is preserved — context can only be saved for a shoot that resolves inside `SOURCE_ROOT` and has an `01.*` frame.

## Technical Notes

- Entity / files touched: service + route + templates (no model/schema/domain/config changes).
  - [app/services/shoots.py](../../app/services/shoots.py): `Shoot` gains `context: str`; `_read_context()` reads `context.txt` and `_shoot()` populates it; new `write_context(rel_dir, text) -> bool` (path-safe via `resolve()`, writes or deletes `context.txt`). `context.txt` is ignored by frame/script detection, so status is unaffected.
  - [app/routes/shoots.py](../../app/routes/shoots.py): `GET /shoots/context` renders the editor pre-filled from `shoot.context` (no longer needs picker fields); new `POST /shoots/context` saves and returns the re-rendered list + an OOB close of `#modal` + a toast; `_queue_shoot()` now reads `shoot.context` for the addendum (drop the `addendum` form field on `POST /shoots/run`).
  - [app/templates/partials/shoots/_context_modal.html](../../app/templates/partials/shoots/_context_modal.html): becomes a Save editor — textarea pre-filled with `shoot.context`, `maxlength`, Save (`hx-post=/shoots/context`) + Cancel.
  - [app/templates/partials/shoots/_list.html](../../app/templates/partials/shoots/_list.html): context badge on rows with a note; button label **+ Context** / **✎ Context**.
  - [app/templates/partials/shoots/_context_saved.html](../../app/templates/partials/shoots/) (new): wraps `_list.html` + the OOB `#modal` clear for the save response.
- Routes added/changed: `POST /shoots/context` (new); `GET /shoots/context` simplified; `POST /shoots/run` drops its `addendum` field.
- Reuse: `assemble_prompt()` still appends the addendum; `#modal` + `[data-modal-close]` + `toast_trigger()` already exist. The editor lives in `#modal` (outside the 3s-polling `#shoots-list`), so typing isn't wiped.

## Testing Plan

Service + route change — unit for the new persistence helper, integration for the flow.

- **Unit** (`tests/unit/test_shoots.py`): `write_context()` writes/clears `context.txt` and `resolve()`/`_shoot()` carry `context`; saving empty removes the file; `write_context()` rejects a frameless/traversal path; `context.txt` does not change a shoot's status (still pending/done).
- **Integration** (`tests/integration/test_shoots.py`, `TestClient`): `GET /shoots/context` pre-fills saved text; `POST /shoots/context` persists it and the response closes the modal (OOB) + re-renders the list with a badge; over-long context is rejected (nothing saved); **Run** and **Run-all** put each shoot's saved context on the created job(s); a row with context shows **✎ Context** + badge. (Update the STORY_014 tests that assumed a one-time `addendum` form field on `/shoots/run`.)
- **e2e** (`tests/e2e/`): **N/A — covered by integration.** No new browser-level interaction beyond the existing modal pattern.

## Estimated Complexity

M — one new persistence helper + a dataclass field in the service, a save route with an OOB modal-close response, and editor/list template updates; runs switch from a form field to the saved note.
