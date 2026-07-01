# STORY_025 — Generate with a local model on the DGX Spark, not just Gemini

> Epic: EPIC_001 (Generate scripts with Gemini) · Status: Done

**As** the OnlyGainsTV operator, **I want** to pick my own local model running on the
DGX Spark (over the LAN) from the same model dropdown as Gemini **so that** I can run
shoots against a self-hosted vision model without paying per-token for Gemini — and
still fall back to Gemini whenever I want.

## Background

Today the only generation backend is Google Gemini ([app/services/gemini_client.py](../../app/services/gemini_client.py)),
selected via a single model dropdown on the Shoots dashboard and the New-Job form. The
DGX Spark ("AEON") exposes an **OpenAI-compatible** API (`/v1/chat/completions`,
`/v1/models`) on the LAN. We want that endpoint to be a second provider the operator can
choose per shoot/job, alongside Gemini. A shoot always supplies a first-frame image
(`01.<ext>`), so the local model must be **vision-capable**; we send the frame as a
base64 `image_url` data part in the OpenAI messages format.

**Confirmed against the live endpoint** (Mac Studio → DGX Spark, verified end-to-end):

- **Base URL:** `http://spark-1.local:8003/v1` — reach it by **hostname** (`spark-1.local`), port **8003**.
- **API key:** none required; send the placeholder `"not-needed"` (the SDK requires a non-empty string).
- **`/v1/models` returns 5 near-identical aliases** over the same underlying weights (`aeon-ultimate`, `aeon-fast`, `aeon-deep`, `qwen36-ultimate`, `aeon-ultimate-xs`) — sampling/speculative presets, not distinct models. The operator curates a couple of these rather than exposing all five.
- **Context window:** 256k — no truncation concerns.
- **Vision: confirmed working** with the OpenAI `image_url` base64 data-part format.
- Responses include a separate `message.reasoning` field alongside `message.content`, and `content` can lead with `\n\n`.
- **AEON is assumed always online for this pass** — runtime offline/self-heal handling and a STORY_023-style live connectivity warning for the local provider are **out of scope** (see the last acceptance criterion). Reachability stays verifiable via `make local-check`.

## Acceptance Criteria

- [x] Three new config settings drive the local provider — `local_model_base_url` (OpenAI-compatible base URL, e.g. `http://spark-1.local:8003/v1`), `local_model_api_key` (optional bearer; blank when the server needs none), and `local_model_names` (comma-separated curated model list). All default to `""` (local provider **disabled** when the base URL is blank), and all three land in **both** [app/config.py](../../app/config.py) and [.env.example](../../.env.example) with the confirmed values documented.
- [x] `local_model_names` acts as a **curated allowlist**: when it's set, the picker shows exactly those models (as namespaced `local:<name>` values); when it's blank, the picker falls back to the full live `/v1/models` list. This keeps the dropdown to a couple of sane choices instead of AEON's five cryptic aliases.
- [x] A new `app/services/local_client.py` (mirroring `gemini_client`'s tiny boundary) exposes `generate(*, prompt, image_bytes, image_mime, model, base_url, api_key, ...) -> str` and `probe_models(base_url, api_key) -> ModelProbe`, talking to the OpenAI-compatible endpoint. It raises the **same** `RetryableError` / `GenerationError` classes the worker already understands.
- [x] `local_client.generate()`:
  - Builds one user message: `{"type": "text", "text": prompt}` + `{"type": "image_url", "image_url": {"url": "data:<mime>;base64,<b64>"}}`, and calls `client.chat.completions.create(...)`.
  - Passes an **explicit request timeout** (180s) so a slow (~37 tok/s) long generation doesn't surface as a spurious `RetryableError`.
  - Passes an **explicit `max_tokens` ceiling and `temperature`** (module-level defaults) so local output length doesn't drift versus the Gemini path.
  - Reads **only** `choices[0].message.content` (ignores the model's separate `message.reasoning` field) and `.strip()`s it **before** the empty check, so a leading `\n\n` never false-triggers a `GenerationError`.
- [x] `local_client` **error mapping** is: timeout / connection / 429 / 5xx → `RetryableError`; **4xx except 429** (e.g. 400 BadRequest — context overflow, malformed image part) → `GenerationError` (terminal, not retried); empty/whitespace content → `GenerationError`.
- [x] The model dropdown on the **Shoots dashboard** and the **New-Job form** lists both providers, grouped so it's obvious which is which — a "Gemini" `<optgroup>` and a "Local (DGX Spark)" `<optgroup>`. Local models only appear when `local_model_base_url` is set.
- [x] Selecting a local model and running a shoot/job routes the generation call to `local_client` (not Gemini); selecting a Gemini model still routes to `gemini_client`. Routing is deterministic and does **not** depend on the local endpoint being reachable at submit time (local option values are namespaced, e.g. `local:<name>`; un-namespaced values remain Gemini, so existing jobs keep working).
- [x] Generation is allowed when **at least one** provider is configured; the old hard requirement of `GEMINI_API_KEY` is relaxed to "the *selected* provider is configured." A job for a provider that isn't configured fails with a clear operator-readable error (no crash, worker keeps running).
- [x] `make local-check` (backed by `scripts/local_check.py`, mirroring `make gemini-check`) reports whether the configured local endpoint is reachable and how many models it offers — free, no generation.
- [x] Provider ids and their display labels ("Gemini" / "Local (DGX Spark)") live in [app/domain.py](../../app/domain.py) as centralized vocab, not hard-coded in templates or services.
- [x] **Out of scope this pass:** runtime offline/self-heal handling and a STORY_023-style live connectivity warning for the local provider — AEON is assumed always online. (Reachability is still checkable on demand via `make local-check`.)

## Technical Notes

- **New provider client — [app/services/local_client.py](../../app/services/local_client.py):**
  - Uses the `openai` Python SDK (lazy-imported, same pattern as the `google-genai` import in `gemini_client`), constructed with `base_url` and an explicit `timeout`. When `local_model_api_key` is blank, pass the placeholder `"not-needed"`.
  - `generate()` signature carries `max_tokens` / `temperature` params with module-level defaults; it passes `timeout=` and those params through to `chat.completions.create`.
  - Content extraction reads `resp.choices[0].message.content` only, `.strip()`ped; `reasoning` is ignored. Empty → `GenerationError`.
  - Error mapping helper distinguishes retryable vs terminal by HTTP status (429/5xx/408 → retry; other 4xx → terminal) and by transport-exception name (timeout/connection → retry), reusing the same spirit as `gemini_client._is_transient` but with the 4xx-terminal rule made explicit.
  - `probe_models()` calls `client.models.list()` (GET `/v1/models`) and returns the ids as a `ModelProbe`; on failure returns `ok=False` with a short operator-readable reason.
- **Shared error types:** extract `RetryableError` / `GenerationError` / `ModelProbe` into a small `app/services/llm_errors.py`; have both `gemini_client` and `local_client` import them, and update `generation_service` to catch the shared `RetryableError`. Keep the change mechanical so `gemini_client`'s public surface is unchanged (re-export from `gemini_client` if any external caller imports them there).
- **Routing / model list — [app/services/generation_service.py](../../app/services/generation_service.py):**
  - Add a `local_models()` helper that returns namespaced `local:<name>` values: the curated `local_model_names` when set, else the live `probe_models` list. (No self-heal cache needed — always-online assumption.)
  - Replace/extend `available_models()` with `selectable_models()` (flat list of valid option **values**, Gemini + `local:` ones) for the existing `chosen_model = model if model in models else default` validation in [app/routes/shoots.py](../../app/routes/shoots.py) and [app/routes/jobs.py](../../app/routes/jobs.py), plus a new `model_options()` returning structured entries `(value, label, provider, price)` for the grouped `<optgroup>` rendering.
  - In `_generate_with_retries()`, parse the job's model value: `local:` prefix → strip it and call `local_client.generate(..., base_url=..., api_key=...)`; otherwise `gemini_client.generate(...)` as today. Relax the `run_job()` config guard to "selected provider configured."
- **Routes added/changed:** no new paths. [app/routes/shoots.py](../../app/routes/shoots.py) and [app/routes/jobs.py](../../app/routes/jobs.py) change to pass `model_options` into the template context (the Gemini `gemini_status` warning stays as-is for the Gemini group).
- **Templates:** [app/templates/pages/shoots.html](../../app/templates/pages/shoots.html) and [app/templates/pages/job_new.html](../../app/templates/pages/job_new.html) render two `<optgroup>`s from `model_options`. No new local warning partial this pass.
- **Domain vocab — [app/domain.py](../../app/domain.py):** add `PROVIDERS` / `PROVIDER_LABELS` (`gemini` → "Gemini", `local` → "Local (DGX Spark)"). `price_label()` stays Gemini-only; local options show "self-hosted" / "—".
- **Config / `.env` additions (both `config.py` and `.env.example`):** `local_model_base_url`, `local_model_api_key`, `local_model_names` (all default `""`). Document the confirmed values in `.env.example`:
  ```dotenv
  LOCAL_MODEL_BASE_URL=http://spark-1.local:8003/v1
  LOCAL_MODEL_API_KEY=
  LOCAL_MODEL_NAMES=aeon-ultimate,aeon-fast,aeon-deep,qwen36-ultimate
  ```
- **Dependency:** add `openai>=1.0` to `[project.dependencies]` in [pyproject.toml](../../pyproject.toml) (lazy-imported so the app still boots without it).
- **Model column:** `Job.model` is `String(60)` — `local:<name>` values fit; no migration needed.

## Testing Plan

Aim for a ~70/20/10 unit/integration/e2e split. No live calls to Gemini **or** the DGX
Spark from tests — mock both clients at their boundary (Key Rule 7 / §3).

- **Unit** (`tests/unit/`):
  - `local_client`: request shape (image encoded as a `data:<mime>;base64,…` `image_url` part; correct `model`, `base_url`, `timeout`, `max_tokens`, `temperature`), content parsing (reads `content`, `.strip()`s it, **ignores `reasoning`**; leading `\n\n` does not raise), and error mapping — timeout / connection / 429 / 5xx → `RetryableError`, **400 / other 4xx → `GenerationError`**, empty content → `GenerationError` — all with the `openai` client patched (no network).
  - `generation_service`: `run_job` with `job.model="local:aeon-fast"` calls `local_client.generate` and **not** `gemini_client.generate` (both mocked); a Gemini model still calls `gemini_client`. `local_models()` / `selectable_models()` / `model_options()` behaviour with `local_model_names` set (curated allowlist) vs blank (probe fallback) vs base URL blank (no local group), and the config-guard error when the selected provider is unconfigured.
- **Integration** (`tests/integration/`, `TestClient`): Shoots page and New-Job form render a "Local (DGX Spark)" `<optgroup>` with the curated names when `local_model_base_url` + `local_model_names` are set (probe monkeypatched) and omit the group when the base URL is blank; posting a run/job with a `local:` model persists that value on the created job (client mocked so no generation runs).
- **e2e** (`tests/e2e/`, Playwright): **N/A for the backend routing / live local call** — CI has no DGX Spark endpoint, and Key Rule 7 forbids live model calls from tests; the visible flow (pick model → run) is unchanged in shape and the new grouped picker rendering is fully covered at the integration layer. Optionally extend one existing Shoots e2e assertion to confirm the picker exposes a local `<optgroup>` when the app is started with `LOCAL_MODEL_BASE_URL` + `LOCAL_MODEL_NAMES` set.

## Estimated Complexity

L — a second generation backend touches config, a new SDK dependency, a new client
module, provider-aware routing in the generation service, and grouped model pickers in
two templates, with tests across the unit and integration layers. No new routes, no DB
migration, and (this pass) no runtime self-heal, which keeps it from being XL.
