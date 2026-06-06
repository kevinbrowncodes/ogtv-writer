"""Prompt schemas — validate inbox forms, shape output for templates."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PromptStatus = Literal["draft", "ready", "archived"]


class PromptBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=20000)
    tags: str = Field(default="", max_length=300)
    status: PromptStatus = "draft"


class PromptCreate(PromptBase):
    """Fields accepted when saving a new prompt."""


class PromptUpdate(BaseModel):
    """All fields optional — only the provided ones are changed (PATCH-style)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=20000)
    tags: str | None = Field(default=None, max_length=300)
    status: PromptStatus | None = None


class PromptRead(PromptBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
