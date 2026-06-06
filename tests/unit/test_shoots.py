"""Unit tests for the shoots service (folder discovery + output writing)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.services import shoots


@pytest.fixture
def source_root(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _make_shoot(root: Path, channel: str, name: str, frame: str | None = "01.jpg") -> Path:
    d = root / channel / name
    d.mkdir(parents=True)
    if frame:
        (d / frame).write_bytes(b"img")
    return d


def test_list_shoots_finds_framed_folders_only(source_root):
    _make_shoot(source_root, "only-gains-tv", "26-brown", "01.jpg")
    _make_shoot(source_root, "only-gains-tv", "26-flex", frame=None)  # no frame
    seedonly = _make_shoot(source_root, "only-gains-tv", "26-seed", frame=None)
    (seedonly / "seed.jpg").write_bytes(b"x")  # seed.jpg is ignored
    _make_shoot(source_root, "youtube", "yt-1", "01.jpeg")

    rels = {s.rel_dir for s in shoots.list_shoots()}
    assert "only-gains-tv/26-brown" in rels
    assert "youtube/yt-1" in rels
    assert "only-gains-tv/26-flex" not in rels  # no frame
    assert "only-gains-tv/26-seed" not in rels  # only seed.jpg

    brown = next(s for s in shoots.list_shoots() if s.name == "26-brown")
    assert brown.channel == "only-gains-tv"
    assert brown.frame == "01.jpg"


def test_frame_is_01_only_other_images_ignored(source_root):
    d = _make_shoot(source_root, "ch", "s", "01.png")
    (d / "seed.jpg").write_bytes(b"x")
    shoot = shoots.resolve("ch/s")
    assert shoot is not None
    assert shoot.frame == "01.png"


def test_resolve_rejects_traversal_and_frameless(source_root):
    _make_shoot(source_root, "ch", "ok", "01.jpg")
    (source_root / "ch" / "noframe").mkdir(parents=True)
    assert shoots.resolve("ch/ok") is not None
    assert shoots.resolve("ch/noframe") is None  # no 01.* frame
    assert shoots.resolve("../escape") is None  # traversal
    assert shoots.resolve("") is None


def test_write_outputs_single_then_multi(source_root):
    d = _make_shoot(source_root, "ch", "s", "01.jpg")

    assert shoots.write_outputs("ch/s", ["solo"], [], "") == ["script.txt"]
    assert (d / "script.txt").read_text() == "solo"

    written = shoots.write_outputs("ch/s", ["a", "b"], ["T1", "T2"], "Scene summary.")
    assert written == ["script1.txt", "script2.txt", "titles.txt", "summary.md"]
    assert (d / "script2.txt").read_text() == "b"
    assert (d / "titles.txt").read_text() == "T1\nT2"
    assert (d / "summary.md").read_text() == "Scene summary."
