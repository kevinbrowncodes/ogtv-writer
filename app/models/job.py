"""Job model — one queued generation request.

A Job pairs a chosen prompt (from the file catalog) with an uploaded first-frame
image and an optional addendum, then runs through a status lifecycle:

    queued → running → done | failed

STORY_002 creates jobs as ``queued``. The worker fields (``started_at``,
``finished_at``, ``result_raw``, ``error``) are declared here but only populated
once the background worker lands in STORY_003.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Which catalog prompt drives this job (filename stem + full filename).
    prompt_slug: Mapped[str] = mapped_column(String(200), index=True)
    prompt_filename: Mapped[str] = mapped_column(String(255), default="")

    # Optional per-job extra instructions, and the count for {{COUNT}} prompts.
    addendum: Mapped[str] = mapped_column(Text, default="")
    count: Mapped[int | None] = mapped_column(default=None)

    # The uploaded first-frame image (repo-relative path under data/uploads/).
    image_path: Mapped[str] = mapped_column(String(500), default="")
    image_filename: Mapped[str] = mapped_column(String(255), default="")

    # Lifecycle.
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    error: Mapped[str] = mapped_column(Text, default="")

    # Populated by the worker in STORY_003.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    result_raw: Mapped[str] = mapped_column(Text, default="")

    # Parsed out of result_raw (STORY_004): a titles list (newline-joined) + a summary.
    titles: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Job id={self.id} prompt={self.prompt_slug!r} status={self.status}>"
