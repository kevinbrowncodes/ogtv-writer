"""User model.

A deliberately minimal account model: enough to log in, gate features, and
hang relationships off of. Extend it per project (avatar, plan, org_id, etc.).
"""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # >>> ADD APP-SPECIFIC USER FIELDS / RELATIONSHIPS BELOW <<<
    # plan: Mapped[str] = mapped_column(String(20), default="free")
    # items: Mapped[list["Item"]] = relationship(back_populates="owner")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User id={self.id} email={self.email!r}>"
