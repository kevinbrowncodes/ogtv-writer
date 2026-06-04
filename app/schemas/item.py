"""Item schemas — validate input from HTMX forms, shape output for templates."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ItemStatus = Literal["active", "archived"]


class ItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    status: ItemStatus = "active"


class ItemCreate(ItemBase):
    """Fields accepted when creating an Item."""


class ItemUpdate(BaseModel):
    """All fields optional — only the provided ones are changed (PATCH-style)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: ItemStatus | None = None


class ItemRead(ItemBase):
    """Item as returned to templates/APIs."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
