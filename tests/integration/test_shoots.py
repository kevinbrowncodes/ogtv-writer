"""Integration tests for the Shoots dashboard + run actions."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from app.config import get_settings
from app.routes.shoots import MAX_ADDENDUM
from app.services import generation_service, job_service, shoots

VEO = "video-review-prompt"  # fixture prompt (no {{COUNT}})


def _seed(root: Path, rel_dir: str, *, frame: str = "01.jpg", script: bool = False) -> None:
    """Create a shoot folder under SOURCE_ROOT (optionally already 'done')."""
    d = root / rel_dir
    d.mkdir(parents=True, exist_ok=True)
    (d / frame).write_bytes(b"img")
    if script:
        (d / "script.txt").write_text("already generated")


@pytest.fixture(autouse=True)
def _source_root(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    pending = tmp_path / "only-gains-tv" / "26-orange"
    pending.mkdir(parents=True)
    (pending / "01.jpg").write_bytes(b"img")
    done = tmp_path / "only-gains-tv" / "26-brown"
    done.mkdir(parents=True)
    (done / "01.jpg").write_bytes(b"img")
    (done / "script.txt").write_text("already generated")  # → done
    yield
    get_settings.cache_clear()


def test_dashboard_lists_channels_and_status(client):
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert "only-gains-tv" in resp.text
    assert "26-orange" in resp.text
    assert "Pending" in resp.text
    assert "Done" in resp.text


def test_dashboard_warns_when_gemini_unavailable(client):
    # The test env forces GEMINI_API_KEY="" → the live model list can't be fetched, so
    # the picker surfaces a clear warning instead of silently showing the default only.
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert "Gemini unavailable" in resp.text
    assert "GEMINI_API_KEY" in resp.text


def test_dashboard_no_warning_when_gemini_ok(client, monkeypatch):
    monkeypatch.setattr(
        generation_service,
        "gemini_status",
        lambda: generation_service.GeminiStatus(
            models=["gemini-2.5-flash", "gemini-2.5-pro"], ok=True, detail=""
        ),
    )
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert "Gemini unavailable" not in resp.text
    assert "gemini-2.5-pro" in resp.text  # the full live list is shown


def test_run_queues_folder_job_for_pending_shoot(client, db):
    resp = client.post(
        "/shoots/run",
        data={"source_dir": "only-gains-tv/26-orange", "prompt_slug": VEO},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    job = job_service.list_jobs(db)[0]
    assert job.source_dir == "only-gains-tv/26-orange"
    assert job.image_filename == "01.jpg"


def test_run_invalid_shoot_queues_nothing(client, db):
    resp = client.post(
        "/shoots/run",
        data={"source_dir": "only-gains-tv/nope", "prompt_slug": VEO},
        follow_redirects=False,
    )
    assert resp.status_code == 303  # flashes an error, redirects
    assert job_service.count_jobs(db) == 0


def test_run_all_queues_pending_only(client, db):
    resp = client.post("/shoots/run-all", data={"prompt_slug": VEO}, follow_redirects=False)
    assert resp.status_code == 303
    jobs = job_service.list_jobs(db)
    assert len(jobs) == 1  # only 26-orange (pending); 26-brown is done → skipped
    assert jobs[0].source_dir == "only-gains-tv/26-orange"


def test_run_htmx_swaps_list_without_resetting_picker(client, db):
    # An HTMX run returns only the list partial (+ a toast) so the picker <form> is never
    # re-rendered and the operator's Prompt/Model/count survive (BUG_004).
    resp = client.post(
        "/shoots/run",
        data={"source_dir": "only-gains-tv/26-orange", "prompt_slug": VEO},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert 'id="shoots-list"' in resp.text  # the tables swapped in
    assert "Select a prompt" not in resp.text  # the picker is NOT in the response → untouched
    assert "HX-Trigger" in resp.headers  # success toast fired
    assert job_service.count_jobs(db) == 1  # the job really queued


def test_run_all_htmx_swaps_list_without_resetting_picker(client, db):
    resp = client.post(
        "/shoots/run-all",
        data={"prompt_slug": VEO},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert 'id="shoots-list"' in resp.text
    assert "Select a prompt" not in resp.text
    assert "HX-Trigger" in resp.headers
    assert job_service.count_jobs(db) == 1  # only the one pending shoot


def test_rows_show_context_button(client):
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert "+ Context" in resp.text
    assert 'hx-get="/shoots/context"' in resp.text


def test_context_modal_renders_prefilled(client):
    # Save a note first, then the editor should reopen pre-filled with it.
    client.post(
        "/shoots/context",
        data={"source_dir": "only-gains-tv/26-orange", "addendum": "Saved note here."},
    )
    resp = client.get("/shoots/context", params={"source_dir": "only-gains-tv/26-orange"})
    assert resp.status_code == 200
    assert 'name="addendum"' in resp.text  # the context textarea
    assert 'name="source_dir"' in resp.text and "only-gains-tv/26-orange" in resp.text
    assert "26-orange" in resp.text  # which shoot
    assert "Saved note here." in resp.text  # pre-filled
    assert "Save" in resp.text


def test_save_context_persists_and_closes_modal(client):
    resp = client.post(
        "/shoots/context",
        data={"source_dir": "only-gains-tv/26-orange", "addendum": "Make it spicy."},
    )
    assert resp.status_code == 200
    assert 'id="modal" hx-swap-oob="true"' in resp.text  # OOB clears the modal
    assert "✎ Context" in resp.text  # the row now shows the edit/has-context state
    # It really persisted on the shoot:
    assert shoots.resolve("only-gains-tv/26-orange").context == "Make it spicy."


def test_save_empty_context_clears_it(client):
    client.post(
        "/shoots/context",
        data={"source_dir": "only-gains-tv/26-orange", "addendum": "temporary"},
    )
    client.post(
        "/shoots/context", data={"source_dir": "only-gains-tv/26-orange", "addendum": "   "}
    )
    assert shoots.resolve("only-gains-tv/26-orange").context == ""


def test_save_context_rejects_overlong(client):
    resp = client.post(
        "/shoots/context",
        data={"source_dir": "only-gains-tv/26-orange", "addendum": "x" * (MAX_ADDENDUM + 1)},
    )
    assert resp.status_code == 200
    assert shoots.resolve("only-gains-tv/26-orange").context == ""  # nothing saved


def test_run_uses_saved_context_as_addendum(client, db):
    client.post(
        "/shoots/context",
        data={"source_dir": "only-gains-tv/26-orange", "addendum": "  Make it extra spicy.  "},
    )
    resp = client.post(
        "/shoots/run",
        data={"source_dir": "only-gains-tv/26-orange", "prompt_slug": VEO},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    job = job_service.list_jobs(db)[0]
    assert job.source_dir == "only-gains-tv/26-orange"
    assert job.addendum == "Make it extra spicy."  # from the saved note, stripped


# --- STORY_016: channel + date filters ---------------------------------------


def test_dashboard_renders_filter_dropdowns_and_hides_excluded_channel(client):
    root = Path(get_settings().source_root)
    _seed(root, "youtube/26-06-07/26-06-07-0000", frame="01.jpeg")
    _seed(root, "wip/secret-wip-shoot")  # excluded channel

    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert 'name="channel"' in resp.text and 'name="date"' in resp.text  # the two selects
    assert "All channels" in resp.text and "All dates" in resp.text  # defaults
    assert "only-gains-tv" in resp.text and "youtube" in resp.text  # channel options
    assert 'value="wip"' not in resp.text  # no channel filter option for wip
    assert "secret-wip-shoot" not in resp.text  # excluded from the list too


def test_list_filters_by_channel(client):
    root = Path(get_settings().source_root)
    _seed(root, "youtube/26-06-07/26-06-07-0000", frame="01.jpeg")

    resp = client.get("/shoots/list", params={"channel": "youtube"})
    assert resp.status_code == 200
    assert "26-06-07-0000" in resp.text  # the youtube shoot
    assert "26-orange" not in resp.text  # the only-gains-tv shoot is filtered out


def test_list_filters_by_date(client):
    root = Path(get_settings().source_root)
    today = date.today().strftime("%y-%m-%d")
    _seed(root, f"only-gains-tv/{today}/{today}-0000")

    resp = client.get("/shoots/list", params={"date": today})
    assert resp.status_code == 200
    assert f"{today}-0000" in resp.text  # the dated shoot
    assert "26-orange" not in resp.text  # the undated shoot is filtered out


def test_list_empty_filter_shows_message(client):
    resp = client.get("/shoots/list", params={"channel": "no-such-channel"})
    assert resp.status_code == 200
    assert "No shoots match this filter" in resp.text


def test_dashboard_keeps_dropdowns_when_filter_matches_nothing(client):
    # Even when the filter empties the list, the picker + dropdowns stay so it can be cleared.
    resp = client.get("/shoots", params={"channel": "no-such-channel"})
    assert resp.status_code == 200
    assert 'name="channel"' in resp.text  # filter still present
    assert "No shoots match this filter" in resp.text


# --- STORY_017: channel-scoped + upcoming date options -----------------------


def test_date_options_follow_selected_channel(client):
    root = Path(get_settings().source_root)
    today = date.today()
    yt_date = today.strftime("%y-%m-%d")  # youtube has today's date
    ogtv_date = (today - timedelta(days=2)).strftime("%y-%m-%d")  # ogtv has a different date
    _seed(root, f"youtube/{yt_date}/{yt_date}-0000", frame="01.jpeg")
    _seed(root, f"only-gains-tv/{ogtv_date}/{ogtv_date}-0000")

    resp = client.get("/shoots", params={"channel": "youtube"})
    assert resp.status_code == 200
    assert f'value="{yt_date}"' in resp.text  # youtube's date is offered
    assert f'value="{ogtv_date}"' not in resp.text  # only-gains-tv's date is not


def test_list_swaps_date_select_out_of_band_for_channel(client):
    root = Path(get_settings().source_root)
    today = date.today().strftime("%y-%m-%d")
    _seed(root, f"youtube/{today}/{today}-0000", frame="01.jpeg")

    resp = client.get("/shoots/list", params={"channel": "youtube"})
    assert resp.status_code == 200
    # The Date select comes back out-of-band so a channel change rebuilds its options.
    assert 'id="shoot-date-filter"' in resp.text and 'hx-swap-oob="true"' in resp.text
    assert f'value="{today}"' in resp.text  # youtube's date in the rebuilt options


def test_stale_date_for_channel_resets_to_all(client):
    root = Path(get_settings().source_root)
    today = date.today()
    yt_date = today.strftime("%y-%m-%d")
    ogtv_date = (today - timedelta(days=2)).strftime("%y-%m-%d")
    _seed(root, f"youtube/{yt_date}/{yt_date}-0000", frame="01.jpeg")
    _seed(root, f"only-gains-tv/{ogtv_date}/{ogtv_date}-0000")

    # Ask for youtube + a date only only-gains-tv has → date is dropped, all of youtube shows.
    resp = client.get("/shoots/list", params={"channel": "youtube", "date": ogtv_date})
    assert resp.status_code == 200
    assert f"{yt_date}-0000" in resp.text  # youtube's shoot is listed (not filtered away)
    # The reset is reflected: "All dates" is the selected option, not ogtv_date.
    assert f'value="{ogtv_date}" selected' not in resp.text


def test_future_dated_shoot_appears_as_option(client):
    root = Path(get_settings().source_root)
    tomorrow = (date.today() + timedelta(days=1)).strftime("%y-%m-%d")
    _seed(root, f"only-gains-tv/{tomorrow}/{tomorrow}-0000")

    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert f'value="{tomorrow}"' in resp.text  # upcoming date is offered


def test_run_all_scopes_to_filtered_subset(client, db):
    root = Path(get_settings().source_root)
    _seed(root, "youtube/26-06-07/26-06-07-0000", frame="01.jpeg")  # another pending shoot

    # Filter to youtube → only the youtube pending shoot runs (not 26-orange).
    resp = client.post(
        "/shoots/run-all",
        data={"prompt_slug": VEO, "channel": "youtube"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    jobs = job_service.list_jobs(db)
    assert len(jobs) == 1
    assert jobs[0].source_dir == "youtube/26-06-07/26-06-07-0000"


def test_run_redirect_preserves_filter(client):
    resp = client.post(
        "/shoots/run",
        data={
            "source_dir": "only-gains-tv/26-orange",
            "prompt_slug": VEO,
            "channel": "only-gains-tv",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "channel=only-gains-tv" in resp.headers["location"]


def test_dashboard_lists_nested_shoot_and_runs_it(client, db):
    # A date-grouped channel: youtube/26-06-07/26-06-07-0000/01.jpeg (BUG_001 / STORY_013).
    root = Path(get_settings().source_root)
    nested = root / "youtube" / "26-06-07" / "26-06-07-0000"
    nested.mkdir(parents=True)
    (nested / "01.jpeg").write_bytes(b"img")

    page = client.get("/shoots")
    assert page.status_code == 200
    assert "youtube" in page.text
    assert "26-06-07-0000" in page.text  # nested shoot is listed
    assert "youtube/26-06-07/26-06-07-0000" in page.text  # Run carries its full rel path

    resp = client.post(
        "/shoots/run",
        data={"source_dir": "youtube/26-06-07/26-06-07-0000", "prompt_slug": VEO},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    job = job_service.list_jobs(db)[0]
    assert job.source_dir == "youtube/26-06-07/26-06-07-0000"
    assert job.image_filename == "01.jpeg"
