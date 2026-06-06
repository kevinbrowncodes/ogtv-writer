"""ScriptTemplate business logic — the reusable pattern library."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.script_template import ScriptTemplate
from app.schemas.script_template import ScriptTemplateCreate, ScriptTemplateUpdate


def list_templates(
    db: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    target_model: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[ScriptTemplate]:
    stmt = select(ScriptTemplate).order_by(ScriptTemplate.name.asc())
    if search:
        stmt = stmt.where(ScriptTemplate.name.ilike(f"%{search.strip()}%"))
    if category:
        stmt = stmt.where(ScriptTemplate.category == category)
    if target_model:
        stmt = stmt.where(ScriptTemplate.target_model == target_model)
    return list(db.scalars(stmt.limit(limit).offset(offset)).all())


def count_templates(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(ScriptTemplate)) or 0


def get_template(db: Session, template_id: int) -> ScriptTemplate | None:
    return db.get(ScriptTemplate, template_id)


def create_template(db: Session, data: ScriptTemplateCreate) -> ScriptTemplate:
    template = ScriptTemplate(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template(
    db: Session, template: ScriptTemplate, data: ScriptTemplateUpdate
) -> ScriptTemplate:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, template: ScriptTemplate) -> None:
    db.delete(template)
    db.commit()
