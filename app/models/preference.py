"""Preference model — studio-wide operator preferences as key/value rows.

OGTV Writer has no accounts, so a preference is app-wide: one row per key
(e.g. ``default_channel`` for the Shoots page's starting Channel filter).
Stored in the database rather than the browser so it survives restarts and
follows the operator across devices.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Preference(Base, TimestampMixin):
    __tablename__ = "preferences"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Preference key={self.key!r} value={self.value!r}>"
