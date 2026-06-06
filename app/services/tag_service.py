"""Tag business logic — the canonical tag catalog."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate


def list_tags(db: Session, *, kind: str | None = None) -> list[Tag]:
    stmt = select(Tag).order_by(Tag.kind.asc(), Tag.name.asc())
    if kind:
        stmt = stmt.where(Tag.kind == kind)
    return list(db.scalars(stmt).all())


def count_tags(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Tag)) or 0


def get_tag(db: Session, tag_id: int) -> Tag | None:
    return db.get(Tag, tag_id)


def get_by_name(db: Session, name: str) -> Tag | None:
    return db.scalar(select(Tag).where(func.lower(Tag.name) == name.lower().strip()))


def create_tag(db: Session, data: TagCreate) -> Tag:
    tag = Tag(name=data.name.strip(), kind=data.kind)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag: Tag, data: TagUpdate) -> Tag:
    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"] is not None:
        payload["name"] = payload["name"].strip()
    for field, value in payload.items():
        setattr(tag, field, value)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag: Tag) -> None:
    db.delete(tag)
    db.commit()
