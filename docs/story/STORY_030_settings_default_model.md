# STORY_030 — Choose the default model in Settings

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** to pick which model the Model
pickers start on, from the Settings page, **so that** my usual choice (e.g. a
Pro model for multi-clip prompts, or the local DGX model) is pre-selected
everywhere instead of the `.env`-configured `gemini-2.5-flash`.

## Acceptance Criteria

- [x] The Settings page has a **Generation** card with a **Default model**
      select (the same grouped Gemini + Local options as the pickers, plus an
      "App default" option showing the `.env` model) and a **Save** button.
- [x] Saving persists the choice (database, survives restarts) and confirms
      with a toast; "App default" clears it.
- [x] The Model picker on the **Shoots** page and the **New generation job**
      page starts on the saved model.
- [x] A job submitted without a valid model falls back to the saved default
      (not the `.env` model) — the same effective default everywhere.
- [x] A saved model that is no longer selectable (e.g. the local provider was
      removed) falls back to the `.env` default instead of an invalid pick.
- [x] A submitted model that isn't selectable is rejected and nothing saved.

## Technical Notes

- [app/services/preference_service.py](../../app/services/preference_service.py)
  — new key `default_model` (reuses the STORY_028 `Preference` table; no
  schema/migration change).
- [app/services/generation_service.py](../../app/services/generation_service.py)
  — new `default_model(db)` resolver: the saved preference when it's still in
  `selectable_models()`, else `get_settings().gemini_model`.
- [app/routes/jobs.py](../../app/routes/jobs.py) /
  [app/routes/shoots.py](../../app/routes/shoots.py) — the four places that
  used `get_settings().gemini_model` as the picker default / submit fallback
  now call the resolver.
- [app/routes/settings.py](../../app/routes/settings.py) — page context gains
  the grouped model options + saved value; new `POST /settings/default-model`
  validating against `selectable_models()` (mirrors STORY_028's channel save).
- [app/templates/pages/settings.html](../../app/templates/pages/settings.html)
  — the Generation card.
- Config / `.env` additions: none (`GEMINI_MODEL` keeps its role as the
  app-level fallback). Domain vocab impact: none.

## Testing Plan

- **Unit** (`tests/unit/test_preference_service.py`): `default_model(db)` —
  unset → `.env` default; saved + selectable → saved; saved but no longer
  selectable → `.env` default.
- **Integration** (`tests/integration/test_settings.py`, Gemini status mocked
  to offer two models — no live calls): the Settings page renders the model
  select; saving persists and reopening shows it selected; an unknown model is
  rejected; clearing works; `/shoots` and `/jobs/new` pre-select the saved
  model; a stale saved model falls back to the `.env` default.
- **e2e** (`tests/e2e/test_smoke.py`, Playwright): the Generation card renders
  and Save round-trips. Depth is limited by design: the e2e server runs with a
  blank `GEMINI_API_KEY` (no paid calls allowed), so only the single fallback
  model is selectable there — multi-model selection is covered at the
  integration layer with a mocked model list.

## Estimated Complexity

S–M — a new preference key + resolver and one Settings form; all four pattern
pieces (preference, save route, card, picker default) already exist from
STORY_028.
