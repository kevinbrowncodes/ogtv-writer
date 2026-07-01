"""Unit tests for the ``make local-check`` operator command (STORY_025).

The command never generates — it only probes ``/v1/models`` — so these mock the probe
and assert the printed line + exit code. No live call is made.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.llm_errors import ModelProbe
from scripts import local_check


def test_local_check_reachable(monkeypatch, capsys):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "http://spark-1.local:8003/v1")
    get_settings.cache_clear()
    monkeypatch.setattr(
        local_check.local_client,
        "probe_models",
        lambda *a, **k: ModelProbe(models=["aeon-ultimate", "aeon-fast"], ok=True, reason=""),
    )
    rc = local_check.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "✅" in out
    assert "2 models" in out
    get_settings.cache_clear()


def test_local_check_no_base_url(monkeypatch, capsys):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "")
    get_settings.cache_clear()
    rc = local_check.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "LOCAL_MODEL_BASE_URL" in out
    get_settings.cache_clear()


def test_local_check_unreachable(monkeypatch, capsys):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "http://spark-1.local:8003/v1")
    get_settings.cache_clear()
    monkeypatch.setattr(
        local_check.local_client,
        "probe_models",
        lambda *a, **k: ModelProbe(
            models=[], ok=False, reason="Couldn't reach the local endpoint."
        ),
    )
    rc = local_check.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "❌" in out
    assert "reach the local endpoint" in out
    get_settings.cache_clear()
