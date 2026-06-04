"""Reusable model mixins.

`TimestampMixin` adds `created_at` / `updated_at` to any model. Compose it with
`Base` on every table so you get audit timestamps for free:

    class Thing(Base, TimestampMixin):
        ...
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    """Adds created/updated timestamps managed in Python (DB-agnostic)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
