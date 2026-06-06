"""ScriptTemplate schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TemplateCategory = Literal["general", "model-pattern", "shot-structure"]
TargetModel = Literal["veo", "wan", "generic"]
OutputFormat = Literal["short-form", "cinematic", "montage", "narrated", "shot-list"]


class ScriptTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=500)
    category: TemplateCategory = "general"
    target_model: TargetModel = "generic"
    output_format: OutputFormat = "short-form"
    body: str = Field(default="", max_length=50000)


class ScriptTemplateCreate(ScriptTemplateBase):
    """Fields accepted when creating a template."""


class ScriptTemplateUpdate(BaseModel):
    """All fields optional — only the provided ones are changed (PATCH-style)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    category: TemplateCategory | None = None
    target_model: TargetModel | None = None
    output_format: OutputFormat | None = None
    body: str | None = Field(default=None, max_length=50000)


class ScriptTemplateRead(ScriptTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
