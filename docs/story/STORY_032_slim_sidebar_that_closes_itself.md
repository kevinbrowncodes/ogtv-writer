# STORY_032 — A slim sidebar that closes itself

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** the sidebar to hold only the pages
I actually navigate between (Shoots, Prompts, Queue) and to get out of the way
on its own **so that** the whole window is content, and navigation is a quick
open → pick → gone interaction instead of a permanently docked column.

## Acceptance Criteria

- [x] The sidebar lists only **Shoots**, **Prompts**, and **Queue** — the
      Dashboard, Scripts, Tags, and Settings entries are gone (Settings stays
      one click away via the top-right gear; the removed pages remain
      reachable at their URLs).
- [x] The sidebar is a slide-in drawer at **every** screen size — hidden by
      default, opened by the menu (hamburger) button, which is now always
      visible in the topbar.
- [x] It closes automatically: choosing a nav item, clicking outside it
      (the backdrop), or pressing Escape.
- [x] The environment + build stamp are still visible inside the opened
      drawer.

## Technical Notes

- [app/templates/partials/_sidebar.html](../../app/templates/partials/_sidebar.html)
  — remove the four nav entries; drop the `lg:static lg:translate-x-0` pin on
  the `<aside>` and the backdrop's `lg:hidden`, so the existing mobile drawer
  behaviour (already wired via `data-sidebar-open` / `data-sidebar-close` in
  [app.js](../../app/static/js/app.js)) applies everywhere.
- [app/templates/partials/_topbar.html](../../app/templates/partials/_topbar.html)
  — the hamburger loses its `lg:hidden`.
- No JS change needed: [app.js](../../app/static/js/app.js) already closes the
  drawer on nav-item click, backdrop click, and Escape.
- The `/dashboard`, `/scripts`, `/tags` routes and the `feature_dashboard`
  flag are untouched — this is navigation chrome only.
- Routes / domain vocab / config / schema impact: none.

## Testing Plan

- **Unit** (`tests/unit/`): N/A — template + one-line JS change, no service or
  pure-function logic; behaviour is covered by the layers below.
- **Integration** (`tests/integration/test_dashboard.py`): the sidebar block
  contains exactly the Shoots/Prompts/Queue links (Shoots first) and none of
  the removed ones; the topbar still links to Settings; the drawer markup is
  un-pinned (no `lg:static` on the aside, no `lg:hidden` on the hamburger).
- **e2e** (`tests/e2e/test_smoke.py`, Playwright, desktop viewport): the
  drawer starts closed; the hamburger opens it showing only the three items;
  clicking the backdrop closes it; opening it again and choosing a nav item
  navigates with the drawer closed afterwards.

## Estimated Complexity

S — deletions plus removing three responsive classes; the drawer logic
already exists.
