# docs/ — the ticket workflow

This directory holds the work-tracking artifacts that gate code in OGTV Writer.
See [CLAUDE.md](../CLAUDE.md) §3 for the rules. **No story file → no code.**

| Folder | What it holds | Naming | Template |
|--------|---------------|--------|----------|
| [story/](story/) | The spec for each feature. Implemented one at a time, in numeric order. | `STORY_NNN_slug.md` | [story/_TEMPLATE.md](story/_TEMPLATE.md) |
| [bug/](bug/) | Broken-behaviour tickets. Never deleted — resolved by status. | `BUG_NNN_slug.md` | [bug/_TEMPLATE.md](bug/_TEMPLATE.md) |
| [epic/](epic/) | Groups of related stories. | `EPIC_NNN_slug.md` | [epic/_TEMPLATE.md](epic/_TEMPLATE.md) |
| [backlog/](backlog/) | Not-yet-ready ideas. Promote to a story before any code. | `BACKLOG_NNN_slug.md` | [backlog/_TEMPLATE.md](backlog/_TEMPLATE.md) |

Numbers are three-digit zero-padded (`001`, `002`, …); slugs are snake_case.
Headings use plain-English titles a non-engineer understands — no function names or jargon.
