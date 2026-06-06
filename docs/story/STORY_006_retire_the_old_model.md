# STORY_006 — Retire the old model

> Epic: EPIC_001 · Status: Not started

**As** the OnlyGainsTV operator, **I want** the leftover pieces of the old starter app
removed, **so that** the codebase only reflects how OGTV Writer actually works now —
prompts, jobs, and scripts — with no dead routes, nav links, or confusing concepts.

Final slice of [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md). Pure
teardown + cleanup — no new behaviour. The deterministic generator and old `/generate`
flow already went in STORY_003; this removes the orphaned **entities** and **controlled
vocab**, and brings docs/seed/nav in line.

## Acceptance Criteria

- [ ] The `Prompt` DB inbox (model, schema, service, router, templates) and the
      `ScriptTemplate` entity (model, schema, service, router, templates) are removed.
- [ ] The `target_model` / `output_format` controlled vocab and the `1·3·5·10`
      `GENERATION_COUNTS` are removed from `app/domain.py`, along with the now-unused
      `Script` columns and any template/form fields that referenced them.
- [ ] No **dead routes** remain (old paths 404) and **no dead nav links** point at removed pages.
- [ ] **Remaining pages still work:** dashboard, prompt catalog, new-job/queue/job-detail,
      script library/detail/edit, and tags all return 200.
- [ ] `scripts/seed.py` seeds only what still exists (drop prompt/template/old-script seeding).
- [ ] `README.md` and `CUSTOMIZATION.md` reflect the new entity set and flows (no `Prompt`
      inbox, no `ScriptTemplate`, no `output_format`/`target_model`, no deterministic generator).
- [ ] `make check` (`ruff` + `mypy` + tests) and `make test-e2e` are green.

## Technical Notes

Mechanical deletion — lean on `mypy`, `ruff`, and the test suite to surface every dangling
reference. Remove:

- **Files:** `app/models/prompt.py`, `app/schemas/prompt.py`, `app/services/prompt_service.py`,
  `app/routes/prompts.py`, `app/templates/pages/prompts.html`, `app/templates/partials/prompts/`;
  and the `script_template` equivalents (`models/`, `schemas/`, `services/script_template_service.py`,
  `routes/script_templates.py`, `pages/templates.html`, `partials/templates/`).
- **`app/models/__init__.py`** — drop the removed models from the registry.
- **`app/domain.py`** — remove `TARGET_MODELS` / `MODEL_LABELS`, `OUTPUT_FORMATS` /
  `FORMAT_LABELS`, `TEMPLATE_CATEGORIES` / labels, `GENERATION_COUNTS`. Keep `TAG_KINDS`,
  `SCRIPT_STATUSES`, `parse_tags`. (Reassess `PROMPT_STATUSES` — gone with the inbox.)
- **`app/templating.py`** — drop the removed label globals so templates don't reference missing names.
- **`app/models/script.py`** — drop `target_model`, `output_format`, and `prompt_source`
  (superseded by `source_prompt` + `job_id` from STORY_004). Update `scripts.py` +
  `script_edit.html` / `script_detail.html` to remove those fields.
- **`app/main.py`** `_register_routers()` — remove the `script_templates` include (the
  `prompts` include was already swapped to the catalog in STORY_001).
- **`_sidebar.html`** — remove the `Templates` (and any leftover old-Prompts) nav items.
- **`scripts/seed.py`** — remove prompt/template/old-script seeding; seed only example
  `Tag`s (and optionally a couple of standalone scripts) if useful.
- **Tests:** delete `tests/integration/test_templates.py` (and any remaining old-entity
  tests); confirm nothing imports the removed modules.
- **Docs:** update `README.md` (entity table, routes table, project structure) and
  `CUSTOMIZATION.md` (five-file recipe examples, "add a new entity") to the current reality.

**Out of scope:** any of the follow-on epic ideas (batch submit, cost tracking, retries,
in-app prompt editing).

## Testing Plan

~70/20/10 — mostly integration (this is a removal).

- **Unit:** update/trim `tests/unit/` so nothing imports removed modules; assert
  `app.domain` no longer exposes the removed names (or simply that the suite imports clean).
- **Integration** (`tests/integration/`): old paths (`POST /prompts`, `/templates`, old
  `/generate`) → 404; remaining pages (dashboard, `/prompts` catalog, `/jobs`, `/scripts`,
  `/tags`) → 200; rendered nav contains no link to a removed page.
- **e2e** (`tests/e2e/`): a smoke pass clicking through the trimmed nav (dashboard → prompts
  → new job → queue → scripts → tags) with no broken page.
- **Manual sanity:** `make dev`, click every nav item, confirm no 404s or template errors.

Done when `make check` + `make test-e2e` are green, `ruff`/`mypy` are clean, and the README
matches the app.

## Estimated Complexity

**M** — broad but mechanical. The risk is missed references; the type-checker and tests are
the safety net, so run them continuously while deleting.
