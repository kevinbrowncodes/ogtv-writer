# STORY_NNN — <Plain-English title a non-engineer understands at a glance>

> Epic: EPIC_NNN (or "—" if standalone) · Status: Not started | In progress | Done

**As** the OnlyGainsTV operator, **I want** <capability> **so that** <outcome>.

## Acceptance Criteria

- [ ] <observable, testable behaviour>
- [ ] <observable, testable behaviour>
- [ ] <edge case / error path is handled>

## Technical Notes

- Entity / files touched (five-file recipe — model / schema / service / route / templates):
- Routes added/changed (method + path):
- Domain vocab impact ([app/domain.py](../../app/domain.py)):
- Config / `.env` additions (must land in both `config.py` and `.env.example`):

## Testing Plan

Aim for a ~70/20/10 unit/integration/e2e split. If a layer is N/A, say so and why
— "no tests needed" is not acceptable without justification.

- **Unit** (`tests/unit/`): <service / pure-function cases against a temp DB>
- **Integration** (`tests/integration/`, `TestClient`): <routes — status codes, rendered HTML, HTMX headers, redirects, 422 validation>
- **e2e** (`tests/e2e/`, Playwright): <user-visible flow, or "N/A — no flow change because …">

## Estimated Complexity

S | M | L  — <one line of reasoning>
