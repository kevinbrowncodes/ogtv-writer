"""Shoot folders under SOURCE_ROOT (data/logline/<channel>/.../<shoot>/).

A *shoot* is a **leaf directory** (a folder with no subfolders) under a channel — it
holds one shoot's assets and no further subfolders. Leaves are discovered at any depth,
so both a flat layout (``<channel>/<shoot>/``) and a grouped one
(``<channel>/<date>/<shoot>/``) work (see BUG_001 / STORY_013). A shoot's first frame is
named strictly ``01.<ext>`` (jpg/jpeg/png/webp) — any other image (e.g. ``seed.jpg``) is
ignored, no fallback. Folder-based jobs read the frame from a shoot and write the
produced scripts back into it.

Paths a job stores: ``source_dir`` is **relative to SOURCE_ROOT** (e.g.
``only-gains-tv/26-06-07-0100_brown`` or ``youtube/26-06-07/26-06-07-0000``); the frame's
path is absolute. Everything is confined to SOURCE_ROOT.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from app.config import get_settings
from app.services.uploads import PROJECT_ROOT

_FRAME_EXTS = (".jpg", ".jpeg", ".png", ".webp")


_CONTEXT_FILE = "context.txt"  # saved per-shoot prompt addendum; reused on every run

# A shoot's date is a YY-MM-DD chunk in its path — either the date-prefixed flat name
# ("26-06-07-0100_brown") or a date-group segment ("youtube/26-06-07/…"). First match wins.
_DATE_RE = re.compile(r"\d{2}-\d{2}-\d{2}")


@dataclass(frozen=True)
class Shoot:
    rel_dir: str  # relative to SOURCE_ROOT, e.g. "only-gains-tv/26-06-07-0100_brown"
    channel: str
    name: str
    frame: str | None  # "01.jpg" etc., or None when the folder has no 01.* frame
    status: str  # "done" (has a script), "pending" (frame, no script), or "no_frame"
    context: str  # saved extra prompt context (from context.txt), or "" when none
    date: str  # "YY-MM-DD" derived from the path, or "" when the path has no date


def _root() -> Path:
    p = Path(get_settings().source_root)
    return (p if p.is_absolute() else PROJECT_ROOT / p).resolve()


def _excluded_channels() -> set[str]:
    """Channel folders to hide from the dashboard (from SHOOTS_EXCLUDED_CHANNELS)."""
    raw = get_settings().shoots_excluded_channels
    return {c.strip() for c in raw.split(",") if c.strip()}


def _shoot_date(rel_dir: str) -> str:
    """The first YY-MM-DD chunk in the relative path, or "" when there is none."""
    match = _DATE_RE.search(rel_dir)
    return match.group(0) if match else ""


def _find_frame(directory: Path) -> str | None:
    for ext in _FRAME_EXTS:
        if (directory / f"01{ext}").is_file():
            return f"01{ext}"
    return None


def _has_script(directory: Path) -> bool:
    return any(directory.glob("script*.txt"))


def _read_context(directory: Path) -> str:
    path = directory / _CONTEXT_FILE
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _shoot_dirs(parent: Path, excluded: set[str]) -> Iterator[Path]:
    """Yield the shoot directories under ``parent`` — at any depth.

    A directory that holds an ``01.*`` frame **is** a shoot and is yielded without
    recursing into it, so a stray subfolder left inside a shoot can't hide it
    (BUG_005). A frameless directory that *has* subdirectories is a grouping level
    (e.g. a date, or ``archive``) and is recursed into; a frameless leaf is yielded so
    the dashboard can flag it ``needs 01.*``. This finds shoots in both the flat
    (``<channel>/<shoot>/``) and grouped (``<channel>/<date>/<shoot>/``) layouts.

    Folders whose name is in ``excluded`` are skipped wherever they appear in the tree,
    so e.g. an ``archive`` grouping nested under a channel is hidden (BUG_006).
    """
    subdirs = sorted(p for p in parent.iterdir() if p.is_dir())
    for sub in subdirs:
        if sub.name in excluded:
            continue
        if _find_frame(sub) is not None:
            yield sub  # has a frame → a shoot; never recurse into stray subfolders
        elif any(p.is_dir() for p in sub.iterdir()):
            yield from _shoot_dirs(sub, excluded)  # grouping level → recurse
        else:
            yield sub  # frameless leaf → surfaced as "needs 01.*"


def _shoot(shoot_dir: Path) -> Shoot:
    rel = str(shoot_dir.resolve().relative_to(_root()))
    channel = Path(rel).parts[0]  # first segment — the channel, even when nested
    frame = _find_frame(shoot_dir)
    if _has_script(shoot_dir):
        status = "done"
    elif frame:
        status = "pending"
    else:
        status = "no_frame"
    return Shoot(
        rel, channel, shoot_dir.name, frame, status, _read_context(shoot_dir), _shoot_date(rel)
    )


def list_shoots() -> list[Shoot]:
    """Every shoot under SOURCE_ROOT that has an 01.* frame, sorted by channel/path.

    Excluded folders (``SHOOTS_EXCLUDED_CHANNELS``) are skipped at any depth, so e.g.
    an ``archive`` grouping never reaches the job picker.
    """
    root = _root()
    if not root.is_dir():
        return []
    excluded = _excluded_channels()
    shoots: list[Shoot] = []
    for channel_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if channel_dir.name in excluded:
            continue
        for shoot_dir in _shoot_dirs(channel_dir, excluded):
            if _find_frame(shoot_dir):
                shoots.append(_shoot(shoot_dir))
    return shoots


def list_by_channel() -> dict[str, list[Shoot]]:
    """All shoots grouped by channel (including frameless ones), each with a status.

    Channels listed in SHOOTS_EXCLUDED_CHANNELS (e.g. ``wip``) are skipped entirely.
    """
    root = _root()
    if not root.is_dir():
        return {}
    excluded = _excluded_channels()
    by_channel: dict[str, list[Shoot]] = {}
    for channel_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if channel_dir.name in excluded:
            continue
        shoots = [_shoot(d) for d in _shoot_dirs(channel_dir, excluded)]
        if shoots:
            by_channel[channel_dir.name] = shoots
    return by_channel


def recent_dates(
    by_channel: dict[str, list[Shoot]], today: date | None = None, days: int = 7
) -> list[str]:
    """Distinct recent + upcoming shoot dates, newest first.

    Pure (operates on an already-fetched grouping). A date is kept when it parses as
    ``YY-MM-DD`` (``20YY-MM-DD``) and is **on or after** ``today - (days - 1)`` — ``days``
    bounds only the *past* window (so ancient history is hidden), while today and future
    dates always pass (shoots are often pre-created for upcoming days, see STORY_017).
    ``today`` defaults to ``date.today()`` (injectable for deterministic tests).
    """
    today = today or date.today()
    earliest = today - timedelta(days=days - 1)
    found: set[str] = set()
    for shoot_list in by_channel.values():
        for s in shoot_list:
            if not s.date:
                continue
            try:
                parsed = datetime.strptime(s.date, "%y-%m-%d").date()
            except ValueError:
                continue
            if parsed >= earliest:
                found.add(s.date)
    return sorted(found, reverse=True)


def filter_shoots(
    by_channel: dict[str, list[Shoot]], channel: str | None = None, date: str | None = None
) -> dict[str, list[Shoot]]:
    """Narrow a grouping by channel and/or date. Pure (no filesystem access).

    A blank/``None`` channel or date means "all". Channels left with no matching shoots
    after a date filter are dropped, so empty tables never render.
    """
    result: dict[str, list[Shoot]] = {}
    for name, shoot_list in by_channel.items():
        if channel and name != channel:
            continue
        matches = [s for s in shoot_list if not date or s.date == date]
        if matches:
            result[name] = matches
    return result


def resolve(rel_dir: str) -> Shoot | None:
    """Path-safe lookup by SOURCE_ROOT-relative dir; must be inside the root + have a frame."""
    if not rel_dir:
        return None
    root = _root()
    path = (root / rel_dir).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    if path == root or not path.is_dir() or _find_frame(path) is None:
        return None
    return _shoot(path)


def frame_abspath(shoot: Shoot) -> str:
    return str((_root() / shoot.rel_dir / (shoot.frame or "")).resolve())


def write_context(rel_dir: str, text: str) -> bool:
    """Save (or, when blank, clear) a shoot's extra prompt context. Path-safe.

    Returns False when the shoot doesn't resolve (bad path / no frame); otherwise writes
    ``context.txt`` into the folder, or deletes it when ``text`` is empty.
    """
    if resolve(rel_dir) is None:
        return False
    path = (_root() / rel_dir).resolve() / _CONTEXT_FILE
    if text.strip():
        path.write_text(text, encoding="utf-8")
    elif path.exists():
        path.unlink()
    return True


def write_outputs(rel_dir: str, scripts: list[str], titles: list[str], summary: str) -> list[str]:
    """Write the produced scripts (+ titles/summary) into the shoot folder; return filenames."""
    if resolve(rel_dir) is None:
        return []
    directory = (_root() / rel_dir).resolve()
    written: list[str] = []
    multiple = len(scripts) > 1
    for index, body in enumerate(scripts, start=1):
        name = f"script{index}.txt" if multiple else "script.txt"
        (directory / name).write_text(body, encoding="utf-8")
        written.append(name)
    if titles:
        (directory / "titles.txt").write_text("\n".join(titles), encoding="utf-8")
        written.append("titles.txt")
    if summary.strip():
        (directory / "summary.md").write_text(summary, encoding="utf-8")
        written.append("summary.md")
    return written
