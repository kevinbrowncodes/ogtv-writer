"""Prompt business logic — the inbox.

Every function takes a `Session`. Routes never write queries directly.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.prompt import Prompt
from app.schemas.prompt import PromptCreate, PromptUpdate


def list_prompts(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[Prompt]:
    """Return prompts, newest first, optionally filtered."""
    stmt = select(Prompt).order_by(Prompt.created_at.desc())
    if search:
        needle = f"%{search.strip()}%"
        stmt = stmt.where(or_(Prompt.title.ilike(needle), Prompt.body.ilike(needle)))
    if status:
        stmt = stmt.where(Prompt.status == status)
    if tag:
        stmt = stmt.where(Prompt.tags.ilike(f"%{tag.strip()}%"))
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def count_prompts(db: Session, *, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(Prompt)
    if status:
        stmt = stmt.where(Prompt.status == status)
    return db.scalar(stmt) or 0


def get_prompt(db: Session, prompt_id: int) -> Prompt | None:
    return db.get(Prompt, prompt_id)


def create_prompt(db: Session, data: PromptCreate) -> Prompt:
    prompt = Prompt(**data.model_dump())
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


def update_prompt(db: Session, prompt: Prompt, data: PromptUpdate) -> Prompt:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prompt, field, value)
    db.commit()
    db.refresh(prompt)
    return prompt


def delete_prompt(db: Session, prompt: Prompt) -> None:
    db.delete(prompt)
    db.commit()


def status_breakdown(db: Session) -> dict[str, int]:
    stmt = select(Prompt.status, func.count()).group_by(Prompt.status)
    return dict(db.execute(stmt).tuples().all())
