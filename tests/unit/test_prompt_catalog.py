"""Unit tests for the file-based prompt catalog service.

Each test points the service at a throwaway ``tmp_path`` dir via the optional
``directory`` argument, so it never touches the real ``app/static/prompts/`` folder.
"""

from __future__ import annotations

from pathlib import Path

from app.services import prompt_catalog


def _write(directory: Path, name: str, text: str = "x") -> None:
    (directory / name).write_text(text, encoding="utf-8")


def test_list_prompts_lists_md_only_sorted(tmp_path: Path) -> None:
    _write(tmp_path, "b-second.md", "hello")
    _write(tmp_path, "a-first.md", "world")
    _write(tmp_path, "notes.txt", "ignore me")
    (tmp_path / "sub").mkdir()

    prompts = prompt_catalog.list_prompts(tmp_path)

    assert [p.slug for p in prompts] == ["a-first", "b-second"]
    assert [p.filename for p in prompts] == ["a-first.md", "b-second.md"]
    # The list view does not load bodies.
    assert all(p.body == "" for p in prompts)


def test_title_derived_from_filename(tmp_path: Path) -> None:
    _write(tmp_path, "my-cool_prompt.md")
    (prompt,) = prompt_catalog.list_prompts(tmp_path)
    assert prompt.title == "My Cool Prompt"


def test_has_count_detection(tmp_path: Path) -> None:
    _write(tmp_path, "with.md", "make {{COUNT}} scripts")
    _write(tmp_path, "with-spaces.md", "make {{ COUNT }} scripts")
    _write(tmp_path, "without.md", "make some scripts")

    by_slug = {p.slug: p for p in prompt_catalog.list_prompts(tmp_path)}

    assert by_slug["with"].has_count is True
    assert by_slug["with-spaces"].has_count is True
    assert by_slug["without"].has_count is False


def test_get_prompt_returns_body(tmp_path: Path) -> None:
    _write(tmp_path, "brief.md", "# Brief\nbody text")
    prompt = prompt_catalog.get_prompt("brief", tmp_path)
    assert prompt is not None
    assert prompt.body == "# Brief\nbody text"
    assert prompt.filename == "brief.md"
    assert prompt.has_count is False


def test_get_prompt_unknown_returns_none(tmp_path: Path) -> None:
    assert prompt_catalog.get_prompt("nope", tmp_path) is None


def test_get_prompt_rejects_traversal(tmp_path: Path) -> None:
    # A secret file sits outside the prompts dir; the guard must never read it.
    (tmp_path.parent / "secret.md").write_text("top secret", encoding="utf-8")
    (tmp_path / "ok.md").write_text("fine", encoding="utf-8")

    assert prompt_catalog.get_prompt("../secret", tmp_path) is None
    assert prompt_catalog.get_prompt("..", tmp_path) is None
    assert prompt_catalog.get_prompt("sub/ok", tmp_path) is None
    # The legitimate file in the dir still resolves.
    assert prompt_catalog.get_prompt("ok", tmp_path) is not None


def test_empty_dir_returns_empty_list(tmp_path: Path) -> None:
    assert prompt_catalog.list_prompts(tmp_path) == []


def test_missing_dir_returns_empty_list(tmp_path: Path) -> None:
    assert prompt_catalog.list_prompts(tmp_path / "does-not-exist") == []
