# STORY_029 — The Shoots page starts on today's date

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** the Shoots page's Date filter to
default to the current date **so that** opening the page shows today's shoots
first — the ones I'm actually working on — instead of every recent date.

## Acceptance Criteria

- [x] Opening `/shoots` with no explicit Date filter pre-selects **today's
      date** in the Date dropdown and shows only today's shoots — provided the
      current channel has a shoot folder dated today.
- [x] When there is no shoot folder for today (for the current channel), the
      page falls back to **All dates** instead of showing an empty list.
- [x] An explicit choice always wins: picking "All dates" (or any other date)
      on the page works exactly as before, and `?date=` in the URL is honored.
- [x] Works together with the saved default channel (STORY_028): the "is there
      a shoot today?" check applies to that channel's dates.

## Technical Notes

- [app/services/shoots.py](../../app/services/shoots.py) — new pure helper
  `today_label()` returning today in shoot-folder form (`YY-MM-DD`, matching
  `recent_dates()`; `today` injectable for deterministic tests).
- [app/routes/shoots.py](../../app/routes/shoots.py) — `GET /shoots` treats an
  **absent** `date` query param (`None`) as "today", mirroring the STORY_028
  channel default. No membership check needed in the route:
  `_list_context()` already clears a date the current channel doesn't offer,
  which yields exactly the "no shoots today → All dates" fallback.
- `GET /shoots/list` (HTMX swaps) is unaffected — those requests always carry
  the Date select via `hx-include`, so an explicit (possibly empty) value is
  always present.
- Existing e2e tests that asserted the old "everything visible on landing"
  state are updated to explicitly select "All dates" first — which is the real
  post-change user flow for seeing the full list.
- Routes added/changed: none new. Domain vocab / config impact: none.

## Testing Plan

- **Unit** (`tests/unit/test_shoots.py`): `today_label()` renders the injected
  date in `YY-MM-DD` form (and defaults to the real today).
- **Integration** (`tests/integration/test_shoots.py`): with a shoot folder
  dated today, `/shoots` pre-selects today and hides undated/other-date
  shoots; without one, no date is selected and everything shows; explicit
  `?date=` (empty) overrides the default; today existing only in a *different*
  channel than the filtered one still falls back to All dates.
- **e2e** (`tests/e2e/test_smoke.py`, Playwright): on load the Date dropdown
  holds today's date (the seed creates a today-dated youtube shoot) and the
  list shows only today's shoots; existing flows updated per the note above.

## Estimated Complexity

S — a one-line default in the route plus a tiny pure helper; most of the work
is test coverage.
