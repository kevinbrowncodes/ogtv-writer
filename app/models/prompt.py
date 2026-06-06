"""Prompt model — the inbox entity.

A Prompt is a raw markdown idea you paste in (a scene, a concept, a brief). You
save it as a draft, tag it by theme/model/style, and later feed it into the
script generator. It's deliberately light: title + markdown body + tags.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Prompt(Base, TimestampMixin):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    # Comma-separated theme/model/style tags (kept simple for fast filtering).
    tags: Mapped[str] = mapped_column(String(300), default="", index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Prompt id={self.id} title={self.title!r} status={self.status}>"
