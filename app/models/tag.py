"""Tag model — the catalog of reusable labels.

Prompts and Scripts store tags inline as a comma-separated string (simple, fast
to filter). This `Tag` table is the *catalog* of canonical tags you maintain —
your themes, model labels, and styles — so tagging stays consistent across the
studio. Each tag has a `kind`: theme | model | style.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), default="theme", index=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Tag id={self.id} name={self.name!r} kind={self.kind}>"
