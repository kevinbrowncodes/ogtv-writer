# STORY_028 — Choose a default channel for the Shoots page in Settings

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** to pick which channel the Shoots
page's Channel dropdown starts on, from the Settings page, **so that** the
channel I work in most is pre-selected on every visit instead of "All channels".

## Acceptance Criteria

- [x] The Settings page has a **Shoots** card with a **Default channel** select
      (the discovered channels + "All channels") and a **Save** button.
- [x] Saving persists the choice (survives restarts — stored in the database,
      not the browser) and confirms with a toast.
- [x] Opening `/shoots` with no explicit filter pre-selects the saved channel
      in the dropdown and shows only that channel's shoots.
- [x] Explicitly choosing "All channels" (or any other channel) on the Shoots
      page still works — the saved default only sets the starting point.
- [x] A saved default whose folder no longer exists falls back to
      "All channels" instead of showing an empty filtered view.
- [x] A submitted channel that isn't one of the discovered channels is
      rejected with an error and nothing is saved.

## Technical Notes

- New lightweight entity **Preference** — a key/value table for studio-wide
  operator preferences (this story uses one key: `default_channel`):
  - [app/models/preference.py](../../app/models/preference.py) (+ registered in
    [app/models/__init__.py](../../app/models/__init__.py)), with an Alembic
    migration (`make migration`) creating the `preferences` table.
  - [app/services/preference_service.py](../../app/services/preference_service.py)
    — `get_preference` / `set_preference` (all DB access stays in services).
- [app/routes/settings.py](../../app/routes/settings.py) — the page gains a DB
  dependency + channel options; new `POST /settings/default-channel` validates
  the choice against the discovered channels, saves, flashes, redirects (303).
- [app/routes/shoots.py](../../app/routes/shoots.py) — `GET /shoots` treats an
  **absent** `channel` query param (`None`) as "use the saved default"
  (sanitized against the current folder scan); an explicit `channel=` (empty)
  still means "All channels". HTMX list requests always carry the select via
  `hx-include`, so they are unaffected.
- [app/templates/pages/settings.html](../../app/templates/pages/settings.html)
  — the new card + form (plain POST → redirect; flash renders as the toast).
- No schema module needed: the input is a single `<select>` validated against
  the live channel list in the route.
- Config / `.env` additions: none. Domain vocab impact: none.

## Testing Plan

- **Unit** (`tests/unit/test_preference_service.py`): get returns the default
  when unset; set → get roundtrip; set overwrites an existing value.
- **Integration** (`tests/integration/test_settings.py`): the Settings page
  lists channel options; saving persists + redirects with a flash; an unknown
  channel is rejected and nothing saved; saving "All channels" clears the
  default; `/shoots` pre-selects a saved default and filters the list;
  `?channel=` (explicit empty) overrides the default; a stale default (folder
  gone) falls back to all channels.
- **e2e** (`tests/e2e/test_smoke.py`, Playwright): pick a default channel in
  Settings, Save, open Shoots — the dropdown starts on it and the list is
  filtered to it.

## Estimated Complexity

M — a new (tiny) model + service and touches to two routes/pages, but each
piece follows an existing pattern.
