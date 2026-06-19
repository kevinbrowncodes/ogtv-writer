# BUG_005 — A stray subfolder inside a shoot hides it (and shows a phantom "needs 01.*" row)

> Status: Resolved

## Summary

If a shoot folder that has a valid `01.*` frame *also* contains any subfolder (e.g. a
stray empty `untitled folder` left behind in Finder), the Shoots dashboard stops
listing that shoot and instead lists its subfolder as a frameless `needs 01.*` row.
The real, runnable shoot silently disappears and can never be run.

## Steps to Reproduce

1. Have a valid shoot: `data/logline/youtube/26-06-20/26-06-20-0800/01.jpeg`.
2. Create any subfolder inside it (e.g. `…/26-06-20-0800/untitled folder/`).
3. Open `/shoots` and filter to that channel/date.

## Expected vs Actual Behaviour

- **Expected:** `26-06-20-0800` lists as a Pending, runnable shoot (it has `01.jpeg`).
- **Actual:** `26-06-20-0800` is gone; a row `untitled folder — No frame / needs 01.*`
  appears in its place. The shoot can't be run. (Matches the operator's screenshot:
  the `youtube/26-06-20` view showed `untitled folder` where `0800` should be.)

## Root Cause

[`app/services/shoots.py`](../../app/services/shoots.py) `_shoot_dirs()` decided "is
this a shoot?" purely by *"does it have no subdirectories?"* (a leaf). A folder with a
subdirectory was always treated as a **grouping level** (like a date) and recursed
into. So a real shoot that happened to contain a stray subfolder was reclassified as a
grouping level — it was never yielded as a shoot, and its empty child was surfaced as a
frameless leaf instead.

## Acceptance Criteria

- [x] A shoot folder containing an `01.*` frame is listed as a runnable shoot even when
      it also contains one or more subfolders; the stray subfolder is not listed.
- [x] The flat and date-grouped layouts (BUG_001 / STORY_013) keep working unchanged.
- [x] A regression test covers a frame-bearing folder with a stray subfolder (unit).

---

## Resolution

Fixed in [`app/services/shoots.py`](../../app/services/shoots.py): `_shoot_dirs()` now
treats *a directory that holds an `01.*` frame* as a shoot and never recurses into it,
so a stray subfolder can no longer hide the shoot. Frameless directories with
subdirectories are still recursed into (grouping levels); frameless leaves are still
yielded so the dashboard can flag `needs 01.*`. Regression coverage added in
`tests/unit/test_shoots.py` (`test_*stray_subfolder*`).
