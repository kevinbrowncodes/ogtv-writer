"""File-based prompt catalog.

OGTV Writer's prompts are reusable markdown briefs that live as ``.md`` files in
``app/static/prompts/``. This module is the read-only catalog over that folder: it
lists the prompts, reads one by slug, and flags whether a prompt expects a
``{{COUNT}}`` placeholder (so a later story's job form knows when to show a count
field).

There is no database here — the filesystem is the source of truth. Add a prompt by
dropping a ``.md`` file into the folder; it shows up automatically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Prompts live at app/static/prompts/ (resolved off this file, so it works no matter
# what the process's working directory is).
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "static" / "prompts"

# Matches the count placeholder, tolerating inner whitespace: {{COUNT}}, {{ COUNT }}.
_COUNT_RE = re.compile(r"\{\{\s*COUNT\s*\}\}")


@dataclass(frozen=True)
class CatalogPrompt:
    """One prompt file in the catalog."""

    slug: str  # filename without ".md"; also the URL id
    filename: str  # e.g. "video-review-prompt.md"
    title: str  # human-readable, derived from the filename
    has_count: bool  # True when the body uses a {{COUNT}} placeholder
    body: str = ""  # full text; only populated by get_prompt()


def _title_from_slug(slug: str) -> str:
    """Turn a filename stem into a title: ``my-cool_prompt`` -> ``My Cool Prompt``."""
    words = [w for w in re.split(r"[-_]+", slug.strip()) if w]
    return " ".join(w[:1].upper() + w[1:] for w in words) or slug


def _resolve_dir(directory: Path | None) -> Path:
    return directory if directory is not None else PROMPTS_DIR


def list_prompts(directory: Path | None = None) -> list[CatalogPrompt]:
    """Return every ``.md`` prompt in the folder (without bodies), sorted by filename."""
    base = _resolve_dir(directory)
    if not base.is_dir():
        return []
    prompts: list[CatalogPrompt] = []
    for path in sorted(base.glob("*.md")):
        if not path.is_file() or path.name.startswith("."):
            continue
        text = path.read_text(encoding="utf-8")
        prompts.append(
            CatalogPrompt(
                slug=path.stem,
                filename=path.name,
                title=_title_from_slug(path.stem),
                has_count=bool(_COUNT_RE.search(text)),
            )
        )
    return prompts


def get_prompt(slug: str, directory: Path | None = None) -> CatalogPrompt | None:
    """Return the prompt for ``slug`` with its full body, or ``None``.

    Path-traversal safe: only a bare filename stem is accepted, and the resolved file
    must live directly inside the prompts folder.
    """
    base = _resolve_dir(directory)
    # Reject anything that isn't a plain stem (no separators, traversal, or empties).
    if not slug or slug != Path(slug).name or slug in {".", ".."}:
        return None
    path = (base / f"{slug}.md").resolve()
    try:
        if path.parent != base.resolve() or not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return CatalogPrompt(
        slug=slug,
        filename=path.name,
        title=_title_from_slug(slug),
        has_count=bool(_COUNT_RE.search(text)),
        body=text,
    )
