"""ScriptTemplate model — reusable script/prompt patterns.

Templates are the building blocks the generator and the writer reuse: a Veo
cinematic pattern, a Wan motion pattern, a standard shot-structure, etc. Each
has a markdown body (the pattern, often with {placeholders}) plus the model and
format it targets.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class ScriptTemplate(Base, TimestampMixin):
    __tablename__ = "script_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    category: Mapped[str] = mapped_column(String(40), default="general", index=True)
    target_model: Mapped[str] = mapped_column(String(20), default="generic", index=True)
    output_format: Mapped[str] = mapped_column(String(30), default="short-form")
    body: Mapped[str] = mapped_column(Text, default="")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ScriptTemplate id={self.id} name={self.name!r} category={self.category}>"
