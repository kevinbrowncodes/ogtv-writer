# STORY_035 — Remove the Generate button from the top bar

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** the topbar's Generate shortcut gone
**so that** the top bar stays minimal — my workflow runs through the Shoots
page, and the new-job form is still right there on the Queue page when I need
it.

## Acceptance Criteria

- [x] The topbar no longer shows the Generate button.
- [x] The theme toggle and Settings gear remain in the topbar; the hamburger
      stays on the left.
- [x] The new-job form (`/jobs/new`) is still reachable — the Queue page keeps
      its button and the route is unchanged.

## Technical Notes

- [app/templates/partials/_topbar.html](../../app/templates/partials/_topbar.html)
  — delete the `/jobs/new` quick-action anchor. Nothing else references it.
- Routes / JS / domain vocab / config impact: none.

## Testing Plan

- **Unit** (`tests/unit/`): N/A — a template element removal, no logic.
- **Integration** (`tests/integration/test_dashboard.py`): the topbar (header)
  no longer contains the `/jobs/new` shortcut, while the Queue page still
  links to it and `/jobs/new` renders.
- **e2e** (`tests/e2e/`): N/A — no workflow changes: the new-job flow is
  unchanged and already covered by `test_submit_generation_job`, which
  navigates to `/jobs/new` directly.

## Estimated Complexity

S — deleting one anchor plus one assertion.
