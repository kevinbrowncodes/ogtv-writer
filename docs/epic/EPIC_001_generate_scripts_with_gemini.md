# EPIC_001 — Generate Veo/Wan scripts from a prompt + image with Gemini

> Status: Done — all six stories shipped.

## Goal

Replace OGTV Writer's offline, deterministic script generator with a real,
multimodal **Google Gemini** pipeline that mirrors the operator's actual manual
workflow: pick a reusable **prompt file**, attach a **first-frame image**, add an
**optional addendum**, and let Gemini produce the script(s). Jobs are **queued** and
run in the background so the operator can submit many and walk away, instead of
doing them one at a time in a chat UI. Results land in the Script library, split
into individual scripts and ready to copy or export.

## Background — the manual workflow this replaces

Today the operator does this by hand in a chat UI, one at a time. Two representative
flows (both start from a reusable prompt `.md` + a first-frame image):

- **Workflow A — "prompt as reviewer" (Veo).** Prompt file `video-review-prompt.md`
  defines a Viral Video Strategist that scores a concept, critiques it, proposes a
  named upgrade, and rewrites it into a structured Veo prompt (anchor + HOOK /
  SETUP / CLIMAX / CAMERA). Produces **one** usable script.
- **Workflow B — "sequential arc" (Wan2.2).** Prompt file `260601-0000_wip-prompt.md`
  asks for **N sequential prompts** (`script1.txt`…`scriptN.txt`) that form one
  escalating narrative, plus a **`titles.txt`** (ranked titles) and a chat-style
  **summary** (per-script table + scene overview). Encodes its own hard constraints
  (locked camera, full-body framing, word counts, etc.).

**The defining insight:** the prompt file *is* the entire brief — role, task,
constraints, target model (Veo vs Wan vs …), **and how many outputs come back and in
what form.** The app must not impose a target model, output format, or fixed count;
it pairs *(prompt + image + optional addendum + count)* and captures **whatever that
prompt produces**, however many pieces.

## Key decisions (locked)

| Area | Decision |
|------|----------|
| Provider | Google **Gemini**, multimodal (prompt text + first-frame image). `google-genai` dep; `GEMINI_API_KEY` / `GEMINI_MODEL` in config + `.env`. |
| Old generator | **Replaced entirely** — no offline/deterministic fallback. App needs a valid key to generate. |
| Prompt catalog | **File-based**, read-only: `.md` files in `app/static/prompts/`, listed in the UI, edited on disk (git-tracked). |
| Per-job input | One prompt + one uploaded first-frame image (stored under `data/`) + optional **addendum** + a **count** (only when the prompt has a `{{COUNT}}` placeholder). |
| Count control | `{{COUNT}}` placeholder in prompts; app shows a number field and injects it at run time. Prompts without it have a fixed/implicit count. |
| Queue | A `jobs` table + an **in-process background worker**. No external broker. Pending jobs survive a restart; drained in order (sequential / small concurrency to respect rate limits). |
| Output handling | **Auto-split + attach extras** — parse the response into a **Run**: each `scriptN` → its own Script library entry; `titles.txt` + summary stored on the run. |
| Export / use | Per-script **copy to clipboard** + download the whole run as a **`.zip`** (`script1.txt`…`scriptN.txt` + `titles.txt`). |

### Assumed defaults (not blockers; revisit per story)

- `GEMINI_MODEL` defaults to a fast/cheap multimodal model (e.g. `gemini-2.5-flash`),
  swappable to a `pro` model for quality.
- **Reliable splitting:** the app wraps the prompt at send-time with a small,
  app-managed output contract (delimiters / structured output) so the reply parses
  cleanly — **without rewriting the operator's `.md` files**.
- Addendum is appended under a clear "Additional details for this job" delimiter.
- One image per job. A failed job is marked `failed` with the error for manual re-run
  (auto-retry on transient errors is a follow-on).

## Scope

**In scope**
- File-based prompt catalog with `{{COUNT}}` support.
- Job submission (prompt + image upload + addendum + count) and a queue.
- In-process worker calling Gemini (multimodal), with status tracking.
- Response parsing → Run with N split scripts + titles + summary.
- Per-script copy + run-level `.zip` export.
- Retiring the old deterministic generator and orphaned entities.

**Out of scope (candidate follow-on epics/stories)**
- Batch submit: one prompt × many images in a single action.
- Gemini cost / usage tracking and budget display.
- Auto-retry / backoff on transient errors and rate limits.
- In-app prompt editing (catalog stays file-based + read-only for now).
- Actually running Veo/Wan or chaining real generated frames between clips.

## Stories

Implemented in numeric order — lowest-numbered ships first, one at a time.

- [x] **STORY_001 — Browse your prompt library** — read `app/static/prompts/*.md`, list + preview in the UI, detect the `{{COUNT}}` placeholder. *(No API, no queue.)* ✅ Done.
- [x] **STORY_002 — Submit a generation job** — pick a prompt, upload a first-frame image, add optional addendum + count; persist to a `jobs` queue (image under `data/`). *(Worker not running yet.)* ✅ Done.
- [x] **STORY_003 — Generate with Gemini in the background** — config + multimodal Gemini call (mocked in tests) + an in-process worker that drains the queue and stores each job's raw result + status. **Removes the old deterministic generator.** ✅ Done.
- [x] **STORY_004 — Turn one response into organized scripts** — parse the reply into a Run: N individual scripts + `titles.txt` + summary. ✅ Done.
- [x] **STORY_005 — Copy and export results** — per-script copy button + download the whole run as a `.zip`. ✅ Done.
- [x] **STORY_006 — Retire the old model** — remove orphaned pieces (below) and clean up nav, seed data, README / CUSTOMIZATION. ✅ Done.

## What gets retired

Given "replace the generator entirely," these no longer fit the prompt-file model:

- **In STORY_003:** the deterministic generator internals (`VARIATION_LENSES`,
  `MODEL_GUIDANCE`, `FORMAT_TECH`, the `_FORMAT_BUILDERS`, `build_script_body()`) and the
  old deterministic `/generate` route + the `/scripts/{id}/variations` action that depend
  on it.
- **In STORY_006:** the `Prompt` DB inbox and the `ScriptTemplate` entity (superseded by
  the file catalog); the `target_model` / `output_format` controlled vocab and the
  `1·3·5·10` count (`domain.py`).

**Kept:** `Tag` (still organizes scripts). **Evolved:** `Script` gains job linkage, an
order index, source-prompt name, and an image reference; loses the old enums.

## Open Questions

- Exact default `GEMINI_MODEL` id and whether batch jobs run strictly sequentially or
  with a small concurrency cap (decide in STORY_003).
- Output-contract format for reliable splitting — delimiter convention vs Gemini
  structured output (decide in STORY_004; prototype in STORY_003).
- Whether the run summary is rendered as HTML in the app or kept as raw markdown.
