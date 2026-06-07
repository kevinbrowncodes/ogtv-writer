# STORY_013 — Find shoots in nested (date-grouped) folders

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** the Shoots dashboard to find shoots whether
they sit flat under a channel or grouped under an extra folder (like a date) **so that**
every channel's shoots show up and can be run, regardless of how I organise its folders.

Fixes [BUG_001](../bug/BUG_001_nested_shoot_folders_not_discovered.md).

## Acceptance Criteria

- [x] A flat channel (`<channel>/<shoot>/01.*`) lists its shoots exactly as before.
- [x] A date-grouped channel (`<channel>/<date>/<shoot>/01.*`) lists every nested shoot under that channel, each with the right Pending/Done/No-frame status and a working Run.
- [x] The intermediate grouping folder (e.g. the date folder) is **not** itself shown as a shoot.
- [x] A nested shoot groups under its channel (the top-level folder), not the intermediate folder.
- [x] "Run" and "Run all pending" queue jobs for nested shoots using their full root-relative path; outputs are written back into the correct nested folder.
- [x] Path-safety is preserved — `resolve()` still rejects traversal and frameless folders.

## Technical Notes

- Entity / files touched: service only — [app/services/shoots.py](../../app/services/shoots.py). No model/schema/route/template changes (the template already renders `s.name` / `s.rel_dir` / `s.status`, which work for nested paths).
- Approach: a **shoot is a leaf directory** (a folder with no subdirectories) under a channel, discovered at any depth. This handles both the flat and date-grouped layouts without hard-coding a "date level." Derive `channel` from the first segment of the shoot's root-relative path (not `shoot_dir.parent.name`).
- `resolve()`, `frame_abspath()`, `write_outputs()` already accept arbitrary root-relative paths and stay path-confined to `SOURCE_ROOT`; they benefit from the channel fix automatically.
- Assumption (documented in code): a shoot folder holds one shoot's assets and contains no further subfolders, so leaves are the shoots.
- Routes added/changed: none.
- Domain vocab impact ([app/domain.py](../../app/domain.py)): none.
- Config / `.env` additions: none.

## Testing Plan

Service-layer change, so weighted toward unit tests.

- **Unit** (`tests/unit/test_shoots.py`): nested discovery — `list_shoots()` / `list_by_channel()` find `<channel>/<date>/<shoot>/01.*` at depth 2, the intermediate date folder is not a shoot, nested shoots group under the channel, status (done/pending/no_frame) is correct, flat + nested coexist in one tree, and `resolve()` works for a nested rel_dir and rejects the date folder. Existing flat-layout tests must keep passing unchanged.
- **Integration** (`tests/integration/test_shoots.py`, `TestClient`): with a nested shoot on disk, `/shoots` renders the nested shoot's name and a Run carrying its full rel_dir; `/shoots/run` queues a folder job with the nested `source_dir`.
- **e2e** (`tests/e2e/`): **N/A — no flow change.** The visible workflow (pick prompt/model, Run / Run all) is unchanged; only folder discovery changed, which is fully covered by unit + integration tests.

## Estimated Complexity

S — one service file: swap two-level iteration for a leaf-directory walk and fix channel derivation; behaviour-preserving for the existing flat layout.
