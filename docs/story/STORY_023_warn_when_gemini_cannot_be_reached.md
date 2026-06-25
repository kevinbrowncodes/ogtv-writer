# STORY_023 — Warn me when Gemini can't be reached, instead of silently hiding models

> Epic: — (follow-on to [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md)) · Status: Done

**As** the OnlyGainsTV operator, **I want** the app to tell me clearly when it can't
reach Gemini (bad/rotated key, no key, or network) — right where I pick a model —
**so that** I'm not misled into thinking "flash is the only model" when the real
problem is a rejected API key and generation is actually broken.

This comes from a real incident: the Model dropdown on the Shoots picker showed only
`gemini-2.5-flash`. The cause was **not** a model restriction — the configured
`GEMINI_API_KEY` was being rejected by Google with `400 API_KEY_INVALID`, so
[`gemini_client.list_models`](../../app/services/gemini_client.py) hit its
`except Exception: return []` and [`available_models()`](../../app/services/generation_service.py)
fell back to the single configured default. Both the dropdown and live generation were
failing, but **nothing in the UI or logs said so** — the failure was completely silent.

STORY_007 added the live model dropdown with a *graceful* fallback; STORY_011 surfaced
*job-runtime* failures. This story closes the remaining gap: make the **fallback itself
visible**, and give the operator a one-command way to check the key.

## Acceptance Criteria

- [x] When the live model list **can't be fetched**, the Shoots picker **and** the
      New-job form show a clear warning beside the Model dropdown — e.g.
      *"Couldn't reach Gemini — showing the default model only. Generation will fail
      until this is fixed."* — with the **reason** when known (e.g. "API key rejected").
- [x] The warning distinguishes the **common cases**: no `GEMINI_API_KEY` configured
      vs. a **rejected key** (`API_KEY_INVALID` / `PERMISSION_DENIED`) vs. a generic
      network/API error — so the operator knows whether to add a key or replace a dead one.
- [x] When the list **is** fetched successfully, **no warning** appears and the full
      model list shows — existing happy-path behaviour is unchanged.
- [x] The fetch **failure reason is captured** from the SDK error rather than swallowed;
      the silent `except: return []` no longer discards the cause, and the failure is
      **logged** (visible in container logs).
- [x] A **successful** fetch is still cached (no re-fetch per page load); a **failed**
      fetch is **not** cached, so the warning clears on the next page load once the key
      is fixed (matches today's no-cache-on-failure behaviour — no code restart needed
      beyond the env reload).
- [x] A **`make gemini-check`** command prints whether the configured key is valid —
      `✅ valid (N models)` or `❌ rejected: <reason>` — using **only the free
      model-list call** (never a paid `generateContent`), and is safe to run against
      the running container.

## Technical Notes

- Entity / files touched (no new entity — this is service + route + template + a script):
  - **[app/services/gemini_client.py](../../app/services/gemini_client.py)** — add
    `probe_models(api_key) -> ModelProbe` (a small dataclass: `models: list[str]`,
    `ok: bool`, `reason: str`) that does **not** swallow the error — it maps the SDK
    exception to a short reason (e.g. read `API_KEY_INVALID` / `PERMISSION_DENIED` from
    the `google.genai` `ClientError`, else the exception class/message). Reimplement
    `list_models()` on top of it (`return probe_models(key).models`) so STORY_007's
    contract — `[]` on error — is preserved and its tests stay green.
  - **[app/services/generation_service.py](../../app/services/generation_service.py)** —
    add `gemini_status() -> GeminiStatus` (`models`, `ok`, `detail`) that wraps
    `probe_models` with the **existing caching rule**: cache only a successful, non-empty
    fetch; never cache a failure (so a fixed key recovers without a restart). Re-point
    `available_models()` at `gemini_status().models` so there's a single fetch path and
    no double API call per request. Log the failure `detail` here.
- Routes added/changed (method + path): no new routes. **[app/routes/shoots.py](../../app/routes/shoots.py)**
  `shoots_page` and **[app/routes/jobs.py](../../app/routes/jobs.py)** `job_new_page`
  pass `gemini_status` into their template context (keep routes thin — just call the
  service and hand the result to the template).
- Templates: a small shared warning partial (e.g. `partials/_gemini_warning.html`)
  rendered above the Model `<select>` in
  **[app/templates/pages/shoots.html](../../app/templates/pages/shoots.html)** and
  **[app/templates/pages/job_new.html](../../app/templates/pages/job_new.html)** when
  `not gemini_status.ok`.
- New operator command: **`scripts/gemini_check.py`** (calls `gemini_status()` and
  prints the ✅/❌ line) wired to a **`gemini-check`** target in the
  [Makefile](../../Makefile). Document it in README §run/troubleshooting.
- Domain vocab impact ([app/domain.py](../../app/domain.py)): none — the reason strings
  live next to where they're produced (the client mapping). No new controlled vocab.
- Config / `.env` additions: **none.** Uses the existing `GEMINI_API_KEY` /
  `GEMINI_MODEL`. No schema change.

## Testing Plan

~70/20/10. **Gemini is mocked — no live, paid calls** (the `make gemini-check` target is
a manual operator tool; its unit test mocks the client).

- **Unit** (`tests/unit/`):
  - `probe_models`: mocked `client.models.list` success → `ok=True`, names returned;
    mocked `ClientError(API_KEY_INVALID)` → `ok=False`, reason contains "API key";
    generic exception → `ok=False` with a fallback reason. `list_models()` still returns
    `[]` on error (regression guard for STORY_007).
  - `gemini_status()` / `available_models()`: success is cached (second call doesn't
    re-hit the client); a **failure is not cached** (a later success recovers); no key
    configured → `ok=False`, `detail` names the missing key, `models == [default]`.
  - `scripts.gemini_check` main: prints the ✅ line on a mocked-valid status and the ❌
    line (with reason) on a mocked-rejected status; never calls `generate`.
- **Integration** (`tests/integration/`, `gemini_status` patched):
  - `GET /shoots` and `GET /jobs/new` with a **failed** status → response HTML contains
    the warning text and the reason; the Model select still renders the default.
  - With an **ok** status (patched to a known model list) → **no** warning text, full
    list present (asserts the happy path is untouched).
- **e2e** (`tests/e2e/`, Playwright): on `/shoots` in the test env (no key configured)
  the **Gemini warning is visible** above the Model picker — validates the real
  rendered fallback path end-to-end. (Reuses the existing no-key test environment.)

Done when `make check` + `make test-e2e` are green and `ruff`/`mypy` are clean.

## Estimated Complexity

**M** — mostly plumbing a reason through a boundary that currently swallows it
(`probe_models`), a cache-only-on-success status wrapper, a shared warning partial in
two pages, and a small CLI/`make` helper. No schema change, no new config, no new route.
The fiddly part is mapping the `google-genai` error to a friendly reason without
breaking STORY_007's `list_models` → `[]` contract.
