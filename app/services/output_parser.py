"""Parse a Gemini response into individual scripts, titles, and a summary.

``generation_service`` wraps each part of the response in markers (the "output
contract"):

    <<<SCRIPT n>>> ... <<<END SCRIPT>>>
    <<<TITLES>>>   ... <<<END TITLES>>>
    <<<SUMMARY>>>  ... <<<END SUMMARY>>>

Parsing is deliberately tolerant: if the model ignores the script markers entirely,
the whole response is treated as a single script, so a job still yields something
usable rather than nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_SCRIPT_RE = re.compile(r"<<<SCRIPT\s*\d+>>>(.*?)<<<END SCRIPT>>>", re.DOTALL)
_TITLES_RE = re.compile(r"<<<TITLES>>>(.*?)<<<END TITLES>>>", re.DOTALL)
_SUMMARY_RE = re.compile(r"<<<SUMMARY>>>(.*?)<<<END SUMMARY>>>", re.DOTALL)


@dataclass
class ParsedOutput:
    scripts: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    summary: str = ""


def parse_response(raw: str) -> ParsedOutput:
    """Split a raw Gemini response into its scripts, titles, and summary."""
    text = raw or ""

    scripts = [body.strip() for body in _SCRIPT_RE.findall(text)]
    scripts = [s for s in scripts if s]
    if not scripts:
        # Model didn't honor the contract — fall back to the whole response.
        whole = text.strip()
        scripts = [whole] if whole else []

    titles: list[str] = []
    titles_match = _TITLES_RE.search(text)
    if titles_match:
        titles = [line.strip() for line in titles_match.group(1).splitlines() if line.strip()]

    summary_match = _SUMMARY_RE.search(text)
    summary = summary_match.group(1).strip() if summary_match else ""

    return ParsedOutput(scripts=scripts, titles=titles, summary=summary)
