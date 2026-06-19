# BUG_006 — Archived shoots leak into the live date views

> Status: Resolved

## Summary

Shoots filed under an `archive` folder (e.g. `youtube/archive/26-06-20-2000/`) show up
on the Shoots dashboard as if they were live shoots for that date — producing phantom
rows like `26-06-20-2000 / Done` under today's `youtube` view, even though no such
folder exists under `youtube/26-06-20/`.

## Steps to Reproduce

1. Have an archived shoot: `data/logline/youtube/archive/26-06-20-2000/01.jpeg` (with a
   `script.txt`, so it reads as Done).
2. Open `/shoots` and filter channel `youtube`, date `26-06-20`.

## Expected vs Actual Behaviour

- **Expected:** the `26-06-20` view lists only the live shoots under
  `youtube/26-06-20/`. Archived shoots are not shown.
- **Actual:** `26-06-20-2000 / Done` appears in the view (and other archived dates leak
  into the unfiltered list too). It maps to `youtube/archive/26-06-20-2000`, which is
  not a live shoot for that date.

## Root Cause

Two heuristics in [`app/services/shoots.py`](../../app/services/shoots.py) combine:
the channel is the **top-level** folder under SOURCE_ROOT, so everything beneath
`youtube/archive/…` is folded into the `youtube` channel; and a shoot's date is the
first `YY-MM-DD` chunk found **anywhere** in its relative path, so
`youtube/archive/26-06-20-2000` reports date `26-06-20`. The `archive` grouping level
was not excluded (only top-level channels named in `SHOOTS_EXCLUDED_CHANNELS`, which
defaulted to `wip`, were skipped — and only at the top level).

## Acceptance Criteria

- [x] An `archive` folder is hidden from the Shoots dashboard and the job picker,
      wherever it appears in the tree (not only as a top-level channel).
- [x] `archive` is excluded by default (the default `SHOOTS_EXCLUDED_CHANNELS` includes
      it) and documented in `.env.example`.
- [x] A regression test covers a nested `archive` folder being excluded (unit).

---

## Resolution

Fixed in [`app/services/shoots.py`](../../app/services/shoots.py): exclusion now applies
to a folder's name **at any depth** (not just top-level channels), so an `archive`
folder nested under a channel is skipped along with its descendants. The default
`shoots_excluded_channels` in [`app/config.py`](../../app/config.py) is now
`"wip,archive"` (mirrored in `.env.example`). Regression coverage added in
`tests/unit/test_shoots.py` (`test_*archive*`).
