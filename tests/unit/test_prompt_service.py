"""Unit tests for the Prompt service (no HTTP layer — just DB logic)."""

from __future__ import annotations

from app.schemas.prompt import PromptCreate, PromptUpdate
from app.services import prompt_service


def test_create_and_get_prompt(db):
    prompt = prompt_service.create_prompt(db, PromptCreate(title="Hook", body="A gym scene"))
    assert prompt.id is not None
    assert prompt.status == "draft"

    fetched = prompt_service.get_prompt(db, prompt.id)
    assert fetched is not None
    assert fetched.title == "Hook"


def test_list_orders_newest_first(db):
    a = prompt_service.create_prompt(db, PromptCreate(title="First"))
    b = prompt_service.create_prompt(db, PromptCreate(title="Second"))
    prompts = prompt_service.list_prompts(db)
    assert [p.id for p in prompts] == [b.id, a.id]


def test_search_matches_title_and_body(db):
    prompt_service.create_prompt(db, PromptCreate(title="Sunrise run", body="stadium stairs"))
    prompt_service.create_prompt(db, PromptCreate(title="Deadlift", body="chalk and iron"))

    assert len(prompt_service.list_prompts(db, search="sunrise")) == 1
    assert len(prompt_service.list_prompts(db, search="chalk")) == 1  # body match


def test_filter_by_status_and_tag(db):
    prompt_service.create_prompt(db, PromptCreate(title="A", status="ready", tags="gym, veo"))
    prompt_service.create_prompt(db, PromptCreate(title="B", status="draft", tags="wan"))

    assert len(prompt_service.list_prompts(db, status="ready")) == 1
    assert len(prompt_service.list_prompts(db, tag="gym")) == 1


def test_update_only_changes_provided_fields(db):
    prompt = prompt_service.create_prompt(db, PromptCreate(title="Original", body="keep me"))
    prompt_service.update_prompt(db, prompt, PromptUpdate(title="Renamed"))

    refreshed = prompt_service.get_prompt(db, prompt.id)
    assert refreshed.title == "Renamed"
    assert refreshed.body == "keep me"  # untouched


def test_delete_prompt(db):
    prompt = prompt_service.create_prompt(db, PromptCreate(title="Temp"))
    prompt_service.delete_prompt(db, prompt)
    assert prompt_service.get_prompt(db, prompt.id) is None
