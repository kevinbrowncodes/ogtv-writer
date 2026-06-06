# STORY_004 — Turn one response into organized scripts

> Epic: EPIC_001 · Status: Not started

**As** the OnlyGainsTV operator, **I want** a finished job's response broken into
individual scripts (plus its titles and summary), **so that** each script is its own
item I can read, copy, and export — instead of one wall of text.

Fourth slice of [EPIC_001](../epic/EPIC_001_generate_scripts_with_gemini.md). STORY_003
stores the **raw** Gemini response; this story **parses** it using the output contract and
materializes the pieces: N `Script` rows tied to the job, plus the job's `titles` and
`summary`.

## Acceptance Criteria

- [ ] When a job finishes, its raw response is parsed into the **individual scripts** the
      prompt produced (1 for the Veo reviewer, N for the Wan arc), each saved as its own
      `Script` linked to the job, in order.
- [ ] If the prompt produced a **`titles`** block and/or a **summary**, both are stored on
      the job and shown on its detail page.
- [ ] The **job-detail page** shows the ordered scripts, the titles, and the summary; the
      generated scripts also appear in the **Script library** (`/scripts`).
- [ ] Parsing is **robust:** a single-script response yields exactly one script (no empty
      titles/summary); a malformed/partial response does **not** crash — it stores what it
      can and the job is still marked `done` (with a note when the parsed count ≠ the requested count).
- [ ] Each generated `Script` records which **prompt** it came from and its **order index**.

## Technical Notes

- **Output contract (finalized here):** lock the delimiters `assemble_prompt` injects in
  STORY_003 — e.g. `<<<SCRIPT n>>> … <<<END SCRIPT>>>`, `<<<TITLES>>> … <<<END TITLES>>>`,
  `<<<SUMMARY>>> … <<<END SUMMARY>>>`. Document the exact format in `generation_service`.
  (If delimiter parsing proves flaky in practice, the fallback is Gemini structured/JSON
  output — note it but don't build it unless needed.)
- **`app/services/output_parser.py`** — `parse_response(raw: str) -> ParsedOutput` where
  `ParsedOutput` has `scripts: list[str]`, `titles: list[str]`, `summary: str`. Trims each
  script to "first char of the prompt" cleanliness (matches the operator's "no labels"
  requirement). Tolerant of missing blocks and stray whitespace.
- **`Job`** gains usage of its `summary` / `titles` columns (declared in STORY_002 — add
  them there if not already): store the parsed summary + titles (newline-joined).
- **`Script`** evolves: add `job_id` (FK → `jobs.id`, nullable, index), `order_index`
  (int, default 0), `source_prompt` (str — the prompt slug/filename). Keep the legacy
  `target_model`/`output_format` columns for now (removed in STORY_006). A generated
  script's `title` is derived (e.g. `"{prompt title} — {n}"`), `body` is the parsed text,
  `status` = `draft`, `tags` optional.
- **`app/services/generation_service.run_job`** (extend STORY_003): after storing
  `result_raw`, call `parse_response`, create the `Script` rows (via `script_service`),
  and set the job's `titles` / `summary`. All within the worker's job transaction.
- **`script_service`** — add a `create_generated_scripts(db, job, parsed) -> list[Script]`
  helper (or reuse `create_script`) so creation is unit-testable without the worker.
- **Templates:** extend `pages/job_detail` (or `pages/jobs.html` detail) to render the
  ordered scripts list, titles, and summary (summary shown as preformatted/markdown).
  Link each script to its library detail page.

**Out of scope:** copy buttons + zip export (STORY_005); retiring legacy Script columns (STORY_006).

## Testing Plan

~70/20/10. All layers apply.

- **Unit** (`tests/unit/test_output_parser.py`, `tests/unit/test_script_service.py`):
  - parse a multi-script contract sample → exactly N scripts in order, titles list, summary text.
  - parse a single-script sample → one script, empty titles/summary.
  - malformed sample (missing end markers / no titles) → best-effort, no exception.
  - `create_generated_scripts` writes N `Script` rows with correct `job_id`, `order_index`, `source_prompt`.
- **Integration** (`tests/integration/test_jobs_results.py`, Gemini mocked to return a
  known multi-part response):
  - create + process a job → job has `summary`/`titles`; N scripts created; `GET /jobs/{id}`
    shows them in order; the scripts appear at `GET /scripts`.
  - single-script prompt → one script, no titles/summary section rendered.
- **e2e** (`tests/e2e/`): open a completed job (seeded fixture with stored `result_raw` or a
  mocked run) and assert the split scripts + summary are visible and each script links out.

Done when `make check` + `make test-e2e` are green and `ruff`/`mypy` are clean.

## Estimated Complexity

**M–L** — the risk is parser robustness against real-world Gemini output drift; everything
else (new columns, Script creation, detail rendering) is routine.
