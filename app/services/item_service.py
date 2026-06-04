"""Item business logic — the reference CRUD service.

Every function takes a `Session` and returns ORM objects (or plain values). This
is the pattern to copy for new entities. Routes never write queries directly.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate


def list_items(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Item]:
    """Return items, newest first, optionally filtered by search/status."""
    stmt = select(Item).order_by(Item.created_at.desc())
    if search:
        stmt = stmt.where(Item.title.ilike(f"%{search.strip()}%"))
    if status:
        stmt = stmt.where(Item.status == status)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def count_items(db: Session, *, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(Item)
    if status:
        stmt = stmt.where(Item.status == status)
    return db.scalar(stmt) or 0


def get_item(db: Session, item_id: int) -> Item | None:
    return db.get(Item, item_id)


def create_item(db: Session, data: ItemCreate) -> Item:
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item: Item, data: ItemUpdate) -> Item:
    # `exclude_unset` => only overwrite fields the caller actually provided.
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: Item) -> None:
    db.delete(item)
    db.commit()


def status_breakdown(db: Session) -> dict[str, int]:
    """Counts per status — used by the dashboard cards."""
    stmt = select(Item.status, func.count()).group_by(Item.status)
    rows = db.execute(stmt).tuples().all()
    return dict(rows)
