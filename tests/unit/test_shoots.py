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


def test_list_by_channel_groups_and_classifies_status(source_root):
    done = _make_shoot(source_root, "only-gains-tv", "26-brown", "01.jpg")
    (done / "script1.txt").write_text("x")  # has a script → done
    _make_shoot(source_root, "only-gains-tv", "26-orange", "01.jpg")  # frame, no script → pending
    _make_shoot(source_root, "only-gains-tv", "26-noframe", frame=None)  # no frame
    _make_shoot(source_root, "youtube", "yt-1", "01.jpeg")  # pending

    by_channel = shoots.list_by_channel()

    assert set(by_channel) == {"only-gains-tv", "youtube"}
    statuses = {s.name: s.status for s in by_channel["only-gains-tv"]}
    assert statuses == {"26-brown": "done", "26-orange": "pending", "26-noframe": "no_frame"}
    assert by_channel["youtube"][0].status == "pending"


def _make_nested_shoot(root: Path, *parts: str, frame: str | None = "01.jpeg") -> Path:
    """Create a shoot at an arbitrary depth, e.g. youtube/26-06-07/26-06-07-0000/."""
    d = root.joinpath(*parts)
    d.mkdir(parents=True)
    if frame:
        (d / frame).write_bytes(b"img")
    return d


def test_nested_shoots_discovered_under_grouping_folder(source_root):
    # Flat channel + date-grouped channel coexist in one tree.
    _make_shoot(source_root, "only-gains-tv", "26-brown", "01.jpg")  # flat, depth 1
    _make_nested_shoot(source_root, "youtube", "26-06-07", "26-06-07-0000")  # grouped, depth 2
    _make_nested_shoot(source_root, "youtube", "26-06-07", "26-06-07-0400")

    rels = {s.rel_dir for s in shoots.list_shoots()}
    assert "only-gains-tv/26-brown" in rels  # flat layout still works
    assert "youtube/26-06-07/26-06-07-0000" in rels  # nested shoot found
    assert "youtube/26-06-07/26-06-07-0400" in rels
    assert "youtube/26-06-07" not in rels  # the date folder is not itself a shoot

    nested = next(s for s in shoots.list_shoots() if s.name == "26-06-07-0000")
    assert nested.channel == "youtube"  # channel = top-level folder, not the date
    assert nested.frame == "01.jpeg"


def test_list_by_channel_groups_nested_shoots_under_channel(source_root):
    done = _make_nested_shoot(source_root, "youtube", "26-06-07", "26-06-07-0000")
    (done / "script.txt").write_text("x")  # has a script → done
    _make_nested_shoot(source_root, "youtube", "26-06-07", "26-06-07-0400")  # frame → pending
    _make_nested_shoot(  # no frame → no_frame
        source_root, "youtube", "26-06-07", "26-06-07-0800", frame=None
    )

    by_channel = shoots.list_by_channel()

    assert set(by_channel) == {"youtube"}  # grouped under the channel, not the date
    statuses = {s.name: s.status for s in by_channel["youtube"]}
    assert statuses == {
        "26-06-07-0000": "done",
        "26-06-07-0400": "pending",
        "26-06-07-0800": "no_frame",
    }


def test_resolve_handles_nested_rel_dir_rejects_grouping_folder(source_root):
    _make_nested_shoot(source_root, "youtube", "26-06-07", "26-06-07-0000")

    shoot = shoots.resolve("youtube/26-06-07/26-06-07-0000")
    assert shoot is not None
    assert shoot.channel == "youtube"
    assert shoot.frame == "01.jpeg"
    assert shoots.resolve("youtube/26-06-07") is None  # date folder has no 01.* frame


def test_write_context_saves_reads_and_clears(source_root):
    _make_shoot(source_root, "ch", "s", "01.jpg")

    assert shoots.resolve("ch/s").context == ""  # none yet

    assert shoots.write_context("ch/s", "Make it spicy.") is True
    assert (source_root / "ch" / "s" / "context.txt").read_text() == "Make it spicy."
    assert shoots.resolve("ch/s").context == "Make it spicy."  # carried on the Shoot

    # Saving blank removes the file (clears the context).
    assert shoots.write_context("ch/s", "   ") is True
    assert not (source_root / "ch" / "s" / "context.txt").exists()
    assert shoots.resolve("ch/s").context == ""


def test_write_context_rejects_frameless_and_traversal(source_root):
    (source_root / "ch" / "noframe").mkdir(parents=True)
    assert shoots.write_context("ch/noframe", "x") is False  # no 01.* frame
    assert shoots.write_context("../escape", "x") is False  # traversal
    assert shoots.write_context("", "x") is False


def test_context_file_does_not_change_status(source_root):
    _make_shoot(source_root, "ch", "s", "01.jpg")
    shoots.write_context("ch/s", "note")  # context.txt is not a script
    assert shoots.resolve("ch/s").status == "pending"  # still pending, not "done"


def test_write_outputs_single_then_multi(source_root):
    d = _make_shoot(source_root, "ch", "s", "01.jpg")

    assert shoots.write_outputs("ch/s", ["solo"], [], "") == ["script.txt"]
    assert (d / "script.txt").read_text() == "solo"

    written = shoots.write_outputs("ch/s", ["a", "b"], ["T1", "T2"], "Scene summary.")
    assert written == ["script1.txt", "script2.txt", "titles.txt", "summary.md"]
    assert (d / "script2.txt").read_text() == "b"
    assert (d / "titles.txt").read_text() == "T1\nT2"
    assert (d / "summary.md").read_text() == "Scene summary."
