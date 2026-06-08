# STORY_017 — Date filter follows the chosen channel (and includes upcoming dates)

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** the Shoots date filter to list the dates that actually exist for the chosen channel — including upcoming ones — **so that** I only ever pick a date that channel really has, instead of a shared list that mixes channels and hides days I've planned ahead.

> Background: STORY_016 added the date filter but (a) capped it to a trailing 7-day window that **excluded future-dated folders**, and (b) built the options from **all channels at once**. In practice each channel has its own dates (some days simply have no folder for a given channel), and shoots are often pre-created for upcoming days. This story makes the date options channel-aware and lets future dates through. Everything else from STORY_016 stays.

## Acceptance Criteria

- [x] The **Date** dropdown options are derived from the **currently selected channel's** folders. Picking `youtube` shows only youtube's dates (e.g. `26-06-09`, `26-06-07`); a date only `only-gains-tv` has (e.g. `26-06-08`) does **not** appear while youtube is selected.
- [x] With **"All channels"** selected, the Date dropdown shows the **union** of every (non-excluded) channel's dates.
- [x] The dropdown includes **today and future-dated** shoots (e.g. `26-06-09` while today is `26-06-08`); dates **older than 7 days ago** are still excluded. Ordering stays newest-first (upcoming dates at the top).
- [x] Changing the **Channel** dropdown updates the **Date** dropdown options live (HTMX), and if the previously-selected date isn't one the new channel has, the Date filter resets to **"All dates"**. The list re-renders to match.
- [x] On a full page load of `/shoots?channel=…&date=…`, the date options and any stale-date reset behave the same as the live path (no divergence between first render and HTMX render).
- [x] All other STORY_016 behaviour is unchanged: channel filter, run-all scoping to the visible subset, sticky filter through the live poll / context save / post-run redirect, and the empty-filter message.

## Technical Notes

- Entity / files touched:
  - [app/services/shoots.py](../../app/services/shoots.py) — in `recent_dates()`, drop the `parsed <= today` upper bound so future dates pass (keep the `parsed >= today - (days - 1)` past floor; `days` now bounds only the past). Update the docstring.
  - [app/routes/shoots.py](../../app/routes/shoots.py) — in `_list_context()`, compute `date_options` from the **channel-scoped** set: `recent_dates(filter_shoots(all_channels, channel=channel))`. If the incoming `date` isn't in those options, clear it to `""` (stale date for this channel) before filtering the list. `/shoots/list` must also re-render the Date `<select>` out-of-band so a channel change updates its options.
  - [app/templates/partials/shoots/_date_filter.html](../../app/templates/partials/shoots/_date_filter.html) — **new** partial rendering the Date `<select id="shoot-date-filter">` from `date_options`/`selected_date`, with an `oob` flag that adds `hx-swap-oob="true"` for the HTMX path.
  - [app/templates/partials/shoots/_list_response.html](../../app/templates/partials/shoots/_list_response.html) — **new** wrapper used by `/shoots/list`: the `_list.html` swap plus the OOB `_date_filter.html`.
  - [app/templates/pages/shoots.html](../../app/templates/pages/shoots.html) — render the Date field via the new `_date_filter.html` include (no `oob`) instead of the inline `<select>`.
- Routes added/changed: `GET /shoots/list` now returns the list **and** an OOB Date select (no new path). `GET /shoots` unchanged in signature.
- Domain vocab impact: none.
- Config / `.env` additions: none.

## Testing Plan

- **Unit** ([tests/unit/test_shoots.py](../../tests/unit/test_shoots.py)): update `test_recent_dates_window_dedupes_and_sorts_newest_first` so a future date is now **included** and sorted at the top, while a date older than the window is still excluded; keep the dedupe-across-channels assertion. (Channel scoping is `recent_dates(filter_shoots(...))` — both already unit-covered — so it's verified at the route layer below.)
- **Integration** ([tests/integration/test_shoots.py](../../tests/integration/test_shoots.py), `TestClient`):
  - Seed channel `youtube` with date `D1` and `only-gains-tv` with a different date `D2` (both within window; use real `date.today()` offsets so it's deterministic and one is in the future). `GET /shoots?channel=youtube` lists `D1` as a Date option and **not** `D2`.
  - `GET /shoots/list?channel=youtube` returns the channel-filtered list **and** an out-of-band Date select (`hx-swap-oob`) containing youtube's dates.
  - `GET /shoots/list?channel=youtube&date=<D2>` (a date youtube lacks) resets to "All dates" and lists all of youtube (stale-date reset).
  - A future-dated seeded shoot appears as a Date option on `/shoots`.
- **e2e** ([tests/e2e/test_smoke.py](../../tests/e2e/test_smoke.py), Playwright): the live-server seed gains dated folders in both channels (one future-dated); a test selects `youtube` and asserts the Date dropdown now lists youtube's date and drops the only-gains-tv-only date — the visible channel→date interaction.

## Estimated Complexity

M — `recent_dates()` is a one-line change, but channel-scoped date options need the route to recompute + reset a stale date and to push the Date select back via an out-of-band HTMX swap, plus a small template refactor (extract the Date select into a reusable partial).
