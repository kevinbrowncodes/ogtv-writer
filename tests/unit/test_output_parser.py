"""Unit tests for the Gemini response parser."""

from __future__ import annotations

from app.services.output_parser import parse_response

MULTI = """preamble the model might add
<<<SCRIPT 1>>>
First script body.
<<<END SCRIPT>>>
<<<SCRIPT 2>>>
Second script body.
<<<END SCRIPT>>>
<<<TITLES>>>
Title A 🔥
Title B 💪
<<<END TITLES>>>
<<<SUMMARY>>>
An overall summary.
<<<END SUMMARY>>>
"""


def test_parses_multiple_scripts_titles_and_summary():
    out = parse_response(MULTI)
    assert out.scripts == ["First script body.", "Second script body."]
    assert out.titles == ["Title A 🔥", "Title B 💪"]
    assert out.summary == "An overall summary."


def test_single_marked_script():
    out = parse_response("<<<SCRIPT 1>>>\nonly one\n<<<END SCRIPT>>>")
    assert out.scripts == ["only one"]
    assert out.titles == []
    assert out.summary == ""


def test_unmarked_response_falls_back_to_whole_as_one_script():
    out = parse_response("Just one script, no markers at all.")
    assert out.scripts == ["Just one script, no markers at all."]
    assert out.titles == []
    assert out.summary == ""


def test_malformed_missing_end_marker_does_not_crash():
    out = parse_response("<<<SCRIPT 1>>> body with no end marker")
    # No complete block matched, so the whole text becomes one script.
    assert len(out.scripts) == 1
    assert out.scripts[0]


def test_empty_response():
    out = parse_response("")
    assert out.scripts == []
    assert out.titles == []
    assert out.summary == ""
