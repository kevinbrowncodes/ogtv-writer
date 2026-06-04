"""Item model — the generic CRUD example.

`Item` is intentionally a neutral, replaceable entity. When you start a new app,
either rename this to your core entity (e.g. `Invoice`, `Note`, `Lead`) or copy
the file as a template for additional models. The CRUD route + service +
templates that operate on it follow the same naming, so renaming is mechanical.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin

# Allowed values for `Item.status`. Keep model + schema in sync.
ITEM_STATUSES = ("active", "archived")


class Item(Base, TimestampMixin):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    # To scope items to a user, uncomment and wire up the relationship:
    # owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # owner: Mapped["User"] = relationship(back_populates="items")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Item id={self.id} title={self.title!r} status={self.status}>"
