# STORY_026 — Multi-script prompts default to 6 scripts instead of 8

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** the "Number of scripts" field to
default to 6 when I pick a multi-script (`{{COUNT}}`) prompt **so that** the
usual batch size is pre-filled and I don't have to lower it from 8 every time.

## Acceptance Criteria

- [x] When a prompt with a `{{COUNT}}` placeholder is selected on the new-job
      form, the count input is pre-filled with **6**.
- [x] A value the operator already typed is preserved on re-render (validation
      errors don't reset the field to the default).
- [x] Prompts without `{{COUNT}}` are unaffected (no count field shown).

## Technical Notes

- Entity / files touched: template-only —
  [app/templates/partials/jobs/_count_field.html](../../app/templates/partials/jobs/_count_field.html)
  (the `or 8` fallback becomes `or 6`).
- Routes added/changed: none.
- Domain vocab impact: none.
- Config / `.env` additions: none.

## Testing Plan

- **Unit** (`tests/unit/`): N/A — no service or pure-function change; the
  default lives only in the rendered template.
- **Integration** (`tests/integration/`, `TestClient`): extend the existing
  count-field test to assert the rendered input carries `value="6"` for a
  `{{COUNT}}` prompt.
- **e2e** (`tests/e2e/`, Playwright): N/A — no flow change; the same field
  renders in the same place, only its pre-filled value differs, which the
  integration layer already asserts.

## Estimated Complexity

S — a one-character template default plus one integration assertion.
