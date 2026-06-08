# STORY_016 — Filter the Shoots dashboard by channel and date

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** to filter the Shoots dashboard by channel and by date **so that** I can focus on one channel's shoots for a given day instead of scrolling the whole list.

## Acceptance Criteria

- [x] Two new dropdowns sit on the Shoots picker, immediately **after the Model dropdown**: a **Channel** filter then a **Date** filter (to its right).
- [x] The **Channel** dropdown lists the channel folders found under `SOURCE_ROOT` (e.g. `only-gains-tv`, `youtube`) plus an **"All channels"** option selected by default. The `wip` channel is **excluded** — and `wip` is hidden from the shoots **list** as well, not just the dropdown.
- [x] The **Date** dropdown lists the distinct shoot dates (`YY-MM-DD`, e.g. `26-06-08`, `26-06-07`) **within the last 7 days**, newest first, plus an **"All dates"** option selected by default. Dates older than 7 days (and future-dated folders) are not offered.
- [x] Changing either dropdown narrows the shoots list to the matching channel and/or date (via HTMX, no full reload). "All channels" + "All dates" shows everything (minus `wip`).
- [x] When a filter is active, **"Run all pending"** queues only the pending shoots in the **currently visible (filtered) subset** — not every pending shoot.
- [x] The filter survives the dashboard's live auto-refresh (the 3s poll while jobs run) and a context save — neither resets the selected channel/date.
- [x] Edge cases: when a filter matches no shoots, the list area shows a friendly "no shoots match" message **but the picker and both dropdowns remain visible** so the filter can be cleared. When `SOURCE_ROOT` has no shoots at all, the existing "No shoots found" empty state still shows.

## Technical Notes

- Entity / files touched (no new entity — extends the existing Shoots feature):
  - [app/config.py](../../app/config.py) — new setting `shoots_excluded_channels` (default `"wip"`, comma-separated) controlling which channel folders are hidden from this page; mirrored in [.env.example](../../.env.example).
  - [app/services/shoots.py](../../app/services/shoots.py):
    - Add a derived `date: str` field to the `Shoot` dataclass — the first `YY-MM-DD` (`\d{2}-\d{2}-\d{2}`) match in `rel_dir`, or `""` when none (covers both the date-prefixed flat name `26-06-07-0100_brown` and the date-group segment `youtube/26-06-07/…`).
    - `list_by_channel()` excludes the configured channels (so `wip` disappears from both the dropdown source and the list).
    - New pure helper `recent_dates(by_channel, today=None, days=7) -> list[str]` — distinct shoot dates within the trailing `days`-day window ending `today` (defaults to `date.today()`; injectable for deterministic tests), sorted newest-first.
    - New pure helper `filter_shoots(by_channel, channel=None, date=None) -> dict[str, list[Shoot]]` — narrows the grouped dict by channel and/or date; empty string / `None` means "all"; channels left with no matching shoots are dropped.
  - [app/routes/shoots.py](../../app/routes/shoots.py):
    - Shared `_list_context(db, channel, date)` helper builds `channels` (filtered), `channel_options`, `date_options`, the selected values, and queue state from a single `list_by_channel()` scan.
    - `GET /shoots` passes the filter options + selections (empty by default) and a `has_shoots` flag.
    - `GET /shoots/list` accepts `channel` and `date` query params and filters accordingly (HTMX swap target + poll target).
    - `POST /shoots/context` re-renders the list honouring the active `channel`/`date` (so saving context doesn't reset the filter).
    - `POST /shoots/run-all` reads `channel`/`date` form fields and scopes the pending set to the filtered subset.
  - [app/templates/pages/shoots.html](../../app/templates/pages/shoots.html) — add the two `<select>`s after Model (`name="channel"` / `name="date"`, each with an "All …" option), wired with `hx-get="/shoots/list"`, `hx-target="#shoots-list"`, `hx-swap="outerHTML"`, `hx-trigger="change"`, `hx-include` of both selects. Restructure so the picker + dropdowns always render when any shoots exist (only the truly-empty `SOURCE_ROOT` case hides them).
  - [app/templates/partials/shoots/_list.html](../../app/templates/partials/shoots/_list.html) — its polling element adds `hx-include="#shoot-channel-filter, #shoot-date-filter"` so each auto-refresh keeps the filter; render a "no shoots match this filter" message when `channels` is empty.
- Routes added/changed (method + path): `GET /shoots/list` (now takes `channel`, `date`); `POST /shoots/run-all` (now reads `channel`, `date`); `POST /shoots/context` (filter-aware re-render). No new paths.
- Domain vocab impact ([app/domain.py](../../app/domain.py)): none — channels and dates are discovered from the filesystem, not controlled vocabulary.
- Config / `.env` additions: `shoots_excluded_channels` in both [app/config.py](../../app/config.py) (typed, default `"wip"`) and [.env.example](../../.env.example).

## Testing Plan

Aim for a ~70/20/10 unit/integration/e2e split.

- **Unit** ([tests/unit/test_shoots.py](../../tests/unit/test_shoots.py)):
  - `Shoot.date` derives `26-06-07` from a flat date-prefixed name, from a nested `…/26-06-07/26-06-07-0000` shoot, and is `""` for a non-dated folder name.
  - `list_by_channel()` omits a channel listed in `shoots_excluded_channels` (e.g. `wip`) while keeping the others.
  - `recent_dates()` with an injected `today` returns distinct dates inside the 7-day window, newest-first, and excludes both older and future dates; deduplicates dates shared across channels.
  - `filter_shoots()` narrows by channel only, by date only, by both, drops channels with no match, and returns everything when channel/date are blank/`None`.
- **Integration** ([tests/integration/test_shoots.py](../../tests/integration/test_shoots.py), `TestClient`):
  - `GET /shoots` renders the Channel + Date selects with an "All …" option, includes `only-gains-tv`/`youtube`, and does **not** render `wip` anywhere.
  - `GET /shoots/list?channel=youtube` returns only youtube shoots; `…?date=<recent>` returns only that date's shoots; both together intersect.
  - `POST /shoots/run-all` with `channel`/`date` queues only the pending shoots in that subset (assert via `job_service`).
  - A filter that matches nothing returns the "no shoots match" message while the page still shows the dropdowns; the existing "No shoots found" path (empty `SOURCE_ROOT`) is unaffected.
- **e2e** ([tests/e2e/test_smoke.py](../../tests/e2e/test_smoke.py), Playwright): the live-server seed gains a second channel (and a recent-dated shoot); a test loads `/shoots`, selects a channel in the dropdown, and asserts the list narrows to that channel (and back to all). Date-window math is covered deterministically by the unit `recent_dates` test (injected `today`) rather than wall-clock-sensitive e2e.

## Estimated Complexity

M — no new entity or migration; it's filter plumbing across the shoots service, three existing routes, and two templates, plus one config flag. The fiddly parts are date extraction across both folder layouts and keeping the filter sticky through the live poll and context save.
