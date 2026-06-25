"""Unit tests for the `make gemini-check` operator command (STORY_023).

The command never calls ``generate`` — it only reports ``gemini_status()`` — so these
mock the status and assert the printed line + exit code. No live, paid call is made.
"""

from __future__ import annotations

from app.services.generation_service import GeminiStatus
from scripts import gemini_check


def test_gemini_check_ok(monkeypatch, capsys):
    monkeypatch.setattr(
        gemini_check.generation_service,
        "gemini_status",
        lambda: GeminiStatus(models=["gemini-2.5-flash", "gemini-2.5-pro"], ok=True, detail=""),
    )
    rc = gemini_check.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "✅" in out
    assert "2 models" in out


def test_gemini_check_rejected_key(monkeypatch, capsys):
    monkeypatch.setattr(
        gemini_check.generation_service,
        "gemini_status",
        lambda: GeminiStatus(
            models=["gemini-2.5-flash"],
            ok=False,
            detail="API key rejected — check GEMINI_API_KEY (API_KEY_INVALID).",
        ),
    )
    rc = gemini_check.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "❌" in out
    assert "API_KEY_INVALID" in out
