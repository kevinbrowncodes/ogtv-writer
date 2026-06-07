# BUG_001 — Shoots nested under a date folder are not discovered

> Status: Resolved

## Summary

The Shoots dashboard only finds shoots laid out as `<channel>/<shoot>/`. A channel
whose shoots are grouped under an extra folder (e.g. a date) — `<channel>/<date>/<shoot>/`
— shows a single bogus "No frame" row instead of its real shoots, so those shoots can
never be run.

## Steps to Reproduce

1. Lay out a channel flat: `data/logline/only-gains-tv/26-06-07-0100_brown/01.jpg`.
2. Lay out another channel date-grouped: `data/logline/youtube/26-06-07/26-06-07-0000/01.jpeg` (and `…-0400`, `…-0800`, `…-1200`, `…-1600`, `…-2000`, each with an `01.*`).
3. Open `/shoots`.

## Expected vs Actual Behaviour

- **Expected:** the `youtube` channel lists all six time-slot shoots (`26-06-07-0000` … `26-06-07-2000`), each Pending and runnable.
- **Actual:** the `youtube` channel shows a single row `26-06-07` with status **No frame / needs 01.\*** — the six real shoots one level deeper are never discovered. The flat `only-gains-tv` channel works fine.

## Root Cause

[`app/services/shoots.py`](../../app/services/shoots.py) assumed a fixed two-level
layout: `list_shoots()` / `list_by_channel()` iterated each channel's *immediate*
subdirectories and treated each as a shoot. For the date-grouped layout the immediate
subdirectory is the date folder (`26-06-07`), which has no `01.*` frame of its own
(the frames live one level deeper), so it was reported as a single `no_frame` shoot and
its children were never scanned. `_shoot()` also derived the channel as
`shoot_dir.parent.name`, which would have been the date folder rather than the channel.

The fix needs meaningful new code (recursive discovery + channel derivation), so it is
tracked by [STORY_013](../story/STORY_013_find_shoots_in_nested_folders.md).

## Acceptance Criteria

- [x] A date-grouped channel (`<channel>/<date>/<shoot>/01.*`) lists every nested shoot, each runnable.
- [x] A flat channel (`<channel>/<shoot>/01.*`) keeps working unchanged.
- [x] A regression test covers nested discovery (unit + integration).

---

## Resolution

Fixed in [STORY_013](../story/STORY_013_find_shoots_in_nested_folders.md).
[`app/services/shoots.py`](../../app/services/shoots.py) now treats a **leaf directory**
(a folder with no subdirectories) under a channel as a shoot, discovered at any depth,
and derives the channel from the first segment of the shoot's root-relative path. Both
the flat (`only-gains-tv`) and date-grouped (`youtube/26-06-07/…`) layouts are
discovered; verified against live data (all six `youtube` shoots now list as Pending).
Regression coverage: `tests/unit/test_shoots.py` (nested discovery, grouping, status,
`resolve()`) and `tests/integration/test_shoots.py` (dashboard lists + runs a nested
shoot).
