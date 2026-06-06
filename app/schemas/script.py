"""Script schemas — validate script forms, shape output for templates."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ScriptStatus = Literal["draft", "ready", "used", "archived"]


class ScriptBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=50000)
    status: ScriptStatus = "draft"
    tags: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=5000)


class ScriptCreate(ScriptBase):
    """Fields accepted when creating a script."""


class ScriptUpdate(BaseModel):
    """All fields optional — only the provided ones are changed (PATCH-style)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=50000)
    status: ScriptStatus | None = None
    tags: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=5000)


class ScriptRead(ScriptBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    used_at: datetime | None
    created_at: datetime
    updated_at: datetime
