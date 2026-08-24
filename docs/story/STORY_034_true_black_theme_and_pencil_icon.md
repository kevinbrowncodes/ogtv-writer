# STORY_034 — A true-black dark theme and a black-and-white pencil icon

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** the dark theme to be actual black
(not dark navy) and the app icon to be a white pencil on black **so that** the
app looks the way I want it in my dock and on screen.

## Acceptance Criteria

- [x] In dark mode the page background is pure black (`#000000`) with neutral
      (untinted) near-black surfaces, borders, and grays — no blue cast.
- [x] The brand accent (violet buttons/highlights) and the light theme are
      unchanged.
- [x] The app icon is a **white pencil on a black** rounded square (still
      full-bleed, so it stays valid as a maskable PWA icon), used everywhere
      the old icon was (sidebar brand, favicon, installed-app icon).
- [x] The PWA chrome matches: manifest `background_color`/`theme_color`, the
      `<meta name="theme-color">`, and the offline/fallback pages use black
      instead of the old navy.

## Technical Notes

- [app/static/css/input.css](../../app/static/css/input.css) — only the
  `.dark` token block changes: `--color-bg` to `0 0 0`, surfaces/borders/grays
  to neutral near-blacks. Rebuild with `make css` (the built `app.css` stays
  git-ignored; CI/deploy rebuild it).
- [app/static/icons/icon.svg](../../app/static/icons/icon.svg) — redrawn: a
  black full-bleed rounded square, a white pencil rotated 45° (body, carved
  tip) and the white underline it just drew (keeps the "Writer" motif).
- [app/templates/base.html](../../app/templates/base.html),
  [app/routes/pwa.py](../../app/routes/pwa.py),
  [app/static/offline.html](../../app/static/offline.html),
  [app/static/service-worker.js](../../app/static/service-worker.js) — the
  hard-coded `#0b0f17` navy becomes `#000000`.
- Routes / domain vocab / config / schema impact: none.

## Testing Plan

- **Unit** (`tests/unit/`): N/A — colors and a static SVG asset; no logic to
  unit-test.
- **Integration** (`tests/integration/test_pwa_offline.py`): the manifest
  serves black `background_color`/`theme_color`; the served icon SVG is the
  black-with-white-pencil drawing (black rect fill, white glyphs, no old
  gradient); the page `<meta name="theme-color">` is black.
- **e2e** (`tests/e2e/test_smoke.py`, Playwright): with the browser emulating
  a dark color scheme, the rendered body's computed background is
  `rgb(0, 0, 0)`.

## Estimated Complexity

S — token values, one SVG, and four color literals; no behavior changes.
