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

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.services.uploads import PROJECT_ROOT

_FRAME_EXTS = (".jpg", ".jpeg", ".png", ".webp")


_CONTEXT_FILE = "context.txt"  # saved per-shoot prompt addendum; reused on every run


@dataclass(frozen=True)
class Shoot:
    rel_dir: str  # relative to SOURCE_ROOT, e.g. "only-gains-tv/26-06-07-0100_brown"
    channel: str
    name: str
    frame: str | None  # "01.jpg" etc., or None when the folder has no 01.* frame
    status: str  # "done" (has a script), "pending" (frame, no script), or "no_frame"
    context: str  # saved extra prompt context (from context.txt), or "" when none


def _root() -> Path:
    p = Path(get_settings().source_root)
    return (p if p.is_absolute() else PROJECT_ROOT / p).resolve()


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


def _shoot_dirs(channel_dir: Path) -> Iterator[Path]:
    """Yield the leaf directories under a channel — the shoots, at any depth.

    A shoot folder holds one shoot's assets and no further subfolders, so a directory
    with no subdirectories is a shoot; one that *has* subdirectories is treated as a
    grouping level (e.g. a date) and recursed into. This finds shoots in both the flat
    (``<channel>/<shoot>/``) and grouped (``<channel>/<date>/<shoot>/``) layouts.
    """
    subdirs = sorted(p for p in channel_dir.iterdir() if p.is_dir())
    for sub in subdirs:
        if any(p.is_dir() for p in sub.iterdir()):
            yield from _shoot_dirs(sub)
        else:
            yield sub


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
    return Shoot(rel, channel, shoot_dir.name, frame, status, _read_context(shoot_dir))


def list_shoots() -> list[Shoot]:
    """Every shoot under SOURCE_ROOT that has an 01.* frame, sorted by channel/path."""
    root = _root()
    if not root.is_dir():
        return []
    shoots: list[Shoot] = []
    for channel_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for shoot_dir in _shoot_dirs(channel_dir):
            if _find_frame(shoot_dir):
                shoots.append(_shoot(shoot_dir))
    return shoots


def list_by_channel() -> dict[str, list[Shoot]]:
    """All shoots grouped by channel (including frameless ones), each with a status."""
    root = _root()
    if not root.is_dir():
        return {}
    by_channel: dict[str, list[Shoot]] = {}
    for channel_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        shoots = [_shoot(d) for d in _shoot_dirs(channel_dir)]
        if shoots:
            by_channel[channel_dir.name] = shoots
    return by_channel


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
