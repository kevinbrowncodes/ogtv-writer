"""Script model — the core entity of OGTV Writer.

A Script is a structured, model-ready markdown document produced from a prompt
(by the generator or by hand) and exported into Veo / Wan / etc. It carries the
full studio metadata: target model, output format, lifecycle status, source
prompt, tags, notes, and a "used" timestamp.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Script(Base, TimestampMixin):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    # The script itself — markdown, the source of truth for copy/export.
    body: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    target_model: Mapped[str] = mapped_column(String(20), default="generic", index=True)
    output_format: Mapped[str] = mapped_column(String(30), default="short-form", index=True)

    # Where this came from: the source prompt text (or a short reference to it).
    prompt_source: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(String(300), default="", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    # Set when the script is marked "used" in a video.
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Script id={self.id} title={self.title!r} model={self.target_model} status={self.status}>"
