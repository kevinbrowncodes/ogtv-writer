"""Unit tests for the shoots service (folder discovery + output writing)."""

from __future__ import annotations

from datetime import date
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


def test_stray_subfolder_does_not_hide_a_framed_shoot(source_root):
    # BUG_005: a shoot that has its 01.* frame but also a stray subfolder must still be
    # listed as the shoot — and the stray subfolder must not appear in its place.
    shoot = _make_nested_shoot(source_root, "youtube", "26-06-20", "26-06-20-0800")
    (shoot / "untitled folder").mkdir()  # stray empty subfolder left in Finder
    (shoot / "seed.jpeg").write_bytes(b"x")  # an extra (ignored) image alongside it

    by_channel = shoots.list_by_channel()
    names = {s.name: s.status for s in by_channel["youtube"]}
    assert names == {"26-06-20-0800": "pending"}  # the shoot, runnable
    assert "untitled folder" not in names  # the stray subfolder is never surfaced

    rels = {s.rel_dir for s in shoots.list_shoots()}
    assert "youtube/26-06-20/26-06-20-0800" in rels
    assert all("untitled folder" not in r for r in rels)


def test_stray_subfolder_inside_flat_shoot_also_handled(source_root):
    # BUG_005, flat layout: frame + stray subfolder at depth 1 still lists as the shoot.
    shoot = _make_shoot(source_root, "only-gains-tv", "26-brown", "01.jpg")
    (shoot / "scratch").mkdir()

    by_channel = shoots.list_by_channel()
    assert {s.name: s.status for s in by_channel["only-gains-tv"]} == {"26-brown": "pending"}


def test_archive_excluded_by_default():
    # BUG_006: the shipped default hides "archive" (and "wip"). Asserted against the
    # field default so it's independent of any developer's local .env.
    from app.config import Settings

    default = str(Settings.model_fields["shoots_excluded_channels"].default)
    assert "archive" in default.split(",")
    assert "wip" in default.split(",")


def test_excluded_folder_setting_matches_nested_names(source_root, monkeypatch):
    # BUG_006: an archived shoot nested under a channel must not leak into the live
    # views — the exclusion applies at any depth, not just to top-level channels.
    monkeypatch.setenv("SHOOTS_EXCLUDED_CHANNELS", "archive")
    get_settings.cache_clear()
    _make_nested_shoot(source_root, "youtube", "26-06-20", "26-06-20-0000")  # live shoot
    done = _make_nested_shoot(source_root, "youtube", "archive", "26-06-20-2000")
    (done / "script.txt").write_text("x")  # archived + done

    names = {s.name for s in shoots.list_by_channel()["youtube"]}
    assert names == {"26-06-20-0000"}  # only the live shoot; the archived one is hidden

    rels = {s.rel_dir for s in shoots.list_shoots()}  # the job picker hides it too
    assert all("archive" not in r for r in rels)


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


# --- STORY_016: date derivation + channel/date filtering ---------------------


def _shoot(rel_dir: str, *, date: str = "", status: str = "pending") -> shoots.Shoot:
    """A lightweight Shoot for the pure filter/date helpers (no filesystem)."""
    return shoots.Shoot(
        rel_dir=rel_dir,
        channel=rel_dir.split("/")[0],
        name=rel_dir.split("/")[-1],
        frame="01.jpg",
        status=status,
        context="",
        date=date,
    )


def test_shoot_date_derived_from_flat_prefix_nested_and_undated(source_root):
    _make_shoot(source_root, "only-gains-tv", "26-06-07-0100_brown", "01.jpg")  # date-prefixed
    _make_nested_shoot(source_root, "youtube", "26-06-07", "26-06-07-0000")  # date-group segment
    _make_shoot(source_root, "only-gains-tv", "brown-flex", "01.jpg")  # no date in the path

    dates = {s.name: s.date for s in shoots.list_shoots()}
    assert dates["26-06-07-0100_brown"] == "26-06-07"  # from the flat prefix
    assert dates["26-06-07-0000"] == "26-06-07"  # from the date-group folder
    assert dates["brown-flex"] == ""  # no YY-MM-DD anywhere in the path


def test_list_by_channel_excludes_configured_channels(source_root, monkeypatch):
    monkeypatch.setenv("SHOOTS_EXCLUDED_CHANNELS", "wip")
    get_settings.cache_clear()
    _make_shoot(source_root, "only-gains-tv", "26-06-07-0100", "01.jpg")
    _make_shoot(source_root, "youtube", "26-06-07-0000", "01.jpg")
    _make_shoot(source_root, "wip", "26-06-07-0400", "01.jpg")

    by_channel = shoots.list_by_channel()
    assert set(by_channel) == {"only-gains-tv", "youtube"}  # wip hidden entirely


def test_recent_dates_includes_future_dedupes_and_sorts_newest_first():
    today = date(2026, 6, 8)
    by_channel = {
        "only-gains-tv": [
            _shoot("only-gains-tv/26-06-09-0100", date="26-06-09"),  # future → kept, at top
            _shoot("only-gains-tv/26-06-08-0100", date="26-06-08"),
            _shoot("only-gains-tv/26-06-07-0100", date="26-06-07"),
            _shoot("only-gains-tv/26-05-30-0100", date="26-05-30"),  # 9 days ago → out
            _shoot("only-gains-tv/no-date", date=""),  # no date → ignored
        ],
        "youtube": [_shoot("youtube/26-06-07-0000", date="26-06-07")],  # dup date across channels
    }

    # Future dates pass (newest-first), the >7-day-old date is dropped, dups collapse.
    assert shoots.recent_dates(by_channel, today=today) == ["26-06-09", "26-06-08", "26-06-07"]


def test_filter_shoots_by_channel_date_both_and_all():
    by_channel = {
        "only-gains-tv": [
            _shoot("only-gains-tv/26-06-08-0100", date="26-06-08"),
            _shoot("only-gains-tv/26-06-07-0100", date="26-06-07"),
        ],
        "youtube": [_shoot("youtube/26-06-07-0000", date="26-06-07")],
    }

    # All (blank/None) → everything unchanged.
    assert shoots.filter_shoots(by_channel) == by_channel
    assert shoots.filter_shoots(by_channel, "", "") == by_channel

    # Channel only.
    only_yt = shoots.filter_shoots(by_channel, channel="youtube")
    assert set(only_yt) == {"youtube"}

    # Date only — spans channels; empty channels are dropped.
    on_07 = shoots.filter_shoots(by_channel, date="26-06-07")
    assert set(on_07) == {"only-gains-tv", "youtube"}
    assert [s.date for s in on_07["only-gains-tv"]] == ["26-06-07"]

    # Both — intersection; a no-match channel disappears.
    yt_08 = shoots.filter_shoots(by_channel, channel="youtube", date="26-06-08")
    assert yt_08 == {}


def test_write_outputs_single_then_multi(source_root):
    d = _make_shoot(source_root, "ch", "s", "01.jpg")

    assert shoots.write_outputs("ch/s", ["solo"], [], "") == ["script.txt"]
    assert (d / "script.txt").read_text() == "solo"

    written = shoots.write_outputs("ch/s", ["a", "b"], ["T1", "T2"], "Scene summary.")
    assert written == ["script1.txt", "script2.txt", "titles.txt", "summary.md"]
    assert (d / "script2.txt").read_text() == "b"
    assert (d / "titles.txt").read_text() == "T1\nT2"
    assert (d / "summary.md").read_text() == "Scene summary."
