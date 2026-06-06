"""Job schemas — validate the generation-job form."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    """Fields accepted when creating a job.

    The image is handled separately as an upload (see app/services/uploads.py).
    Whether ``count`` is required is decided in the route, because it depends on
    whether the chosen prompt uses a ``{{COUNT}}`` placeholder.
    """

    prompt_slug: str = Field(min_length=1, max_length=200)
    addendum: str = Field(default="", max_length=20000)
    count: int | None = Field(default=None, ge=1, le=50)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt_slug: str
    prompt_filename: str
    addendum: str
    count: int | None
    image_path: str
    image_filename: str
    status: str
    error: str
    created_at: datetime
    updated_at: datetime
