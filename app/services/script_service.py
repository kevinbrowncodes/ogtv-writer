"""Script business logic — the library.

Handles CRUD plus the studio-specific actions: marking a script "used" (stamps
`used_at`), duplicating, and the filtered library listing.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.script import Script
from app.schemas.script import ScriptCreate, ScriptUpdate


def list_scripts(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    target_model: str | None = None,
    tag: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[Script]:
    """Return scripts, newest first, filtered by search/status/model/tag."""
    stmt = select(Script).order_by(Script.created_at.desc())
    if search:
        needle = f"%{search.strip()}%"
        stmt = stmt.where(or_(Script.title.ilike(needle), Script.body.ilike(needle)))
    if status:
        stmt = stmt.where(Script.status == status)
    if target_model:
        stmt = stmt.where(Script.target_model == target_model)
    if tag:
        stmt = stmt.where(Script.tags.ilike(f"%{tag.strip()}%"))
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def count_scripts(db: Session, *, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(Script)
    if status:
        stmt = stmt.where(Script.status == status)
    return db.scalar(stmt) or 0


def get_script(db: Session, script_id: int) -> Script | None:
    return db.get(Script, script_id)


def create_script(db: Session, data: ScriptCreate) -> Script:
    script = Script(**data.model_dump())
    _sync_used_at(script)
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


def update_script(db: Session, script: Script, data: ScriptUpdate) -> Script:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(script, field, value)
    _sync_used_at(script)
    db.commit()
    db.refresh(script)
    return script


def duplicate_script(db: Session, script: Script) -> Script:
    """Create a fresh draft copy of an existing script."""
    copy = Script(
        title=f"{script.title} (copy)",
        body=script.body,
        status="draft",
        target_model=script.target_model,
        output_format=script.output_format,
        prompt_source=script.prompt_source,
        tags=script.tags,
        notes=script.notes,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


def delete_script(db: Session, script: Script) -> None:
    db.delete(script)
    db.commit()


def status_breakdown(db: Session) -> dict[str, int]:
    stmt = select(Script.status, func.count()).group_by(Script.status)
    return dict(db.execute(stmt).tuples().all())


def _sync_used_at(script: Script) -> None:
    """Stamp `used_at` the first time a script is marked used."""
    if script.status == "used" and script.used_at is None:
        script.used_at = datetime.now(UTC)
