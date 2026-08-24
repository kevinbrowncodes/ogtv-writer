# STORY_027 — The Shoots page gets a Refresh button so new folders show up without a reload

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** a Refresh button on the Shoots page
**so that** when I drop new shoot folders under the source root I can see them
immediately, without reloading the whole page (and losing my prompt/model/count
picks) and without waiting for a job to be running (today the list only
auto-refreshes while the queue is active).

## Acceptance Criteria

- [x] The Shoots page shows a **Refresh** button.
- [x] Clicking it re-scans the shoot folders and updates the list in place —
      newly added folders appear.
- [x] The shared picker (Prompt / Model / count) keeps its values across a
      refresh (same swap-only-the-list behaviour as BUG_004).
- [x] The current channel/date filter is preserved by the refresh.
- [x] A folder creating a brand-new **channel** also appears in the Channel
      dropdown (out-of-band swap, mirroring the STORY_017 date-dropdown
      pattern), not just in the tables.
- [x] With no shoots at all (empty state), the button still works as a plain
      link that reloads the page — revealing the picker once folders exist.

## Technical Notes

- Template-only + tests; the scan endpoint already exists (`GET /shoots/list`).
- Files touched:
  - [app/templates/pages/shoots.html](../../app/templates/pages/shoots.html) —
    header gains the Refresh control: an `<a href="/shoots">` (no-JS / empty-state
    fallback) enhanced with `hx-get="/shoots/list"` targeting `#shoots-list` and
    `hx-include`-ing the channel/date filters.
  - [app/templates/partials/shoots/_channel_filter.html](../../app/templates/partials/shoots/_channel_filter.html)
    (new) — the Channel `<select>` extracted so it can render inline **and**
    out-of-band, exactly like `_date_filter.html`.
  - [app/templates/partials/shoots/_list_response.html](../../app/templates/partials/shoots/_list_response.html)
    — additionally re-renders the Channel select OOB, so every list swap
    (refresh, filter change, run, poll) keeps its options current.
- Routes added/changed: none. Domain vocab impact: none. Config: none.

## Testing Plan

- **Unit** (`tests/unit/`): N/A — no service or pure-function change; folder
  scanning (`shoots.list_by_channel`) is already covered.
- **Integration** (`tests/integration/test_shoots.py`): the page renders the
  Refresh control wired to `/shoots/list`; a folder seeded after the first
  render appears in the next `/shoots/list` response; the response carries the
  Channel select out-of-band including a newly created channel.
- **e2e** (`tests/e2e/test_smoke.py`, Playwright): drop a new shoot folder
  under the live server's source root, click Refresh, and the new shoot appears
  in the list without a page navigation.

## Estimated Complexity

S — one template control + one extracted partial; the backend endpoint already exists.
