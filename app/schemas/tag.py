"""Tag schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TagKind = Literal["theme", "model", "style"]


class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    kind: TagKind = "theme"


class TagCreate(TagBase):
    """Fields accepted when creating a tag."""


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    kind: TagKind | None = None


class TagRead(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
