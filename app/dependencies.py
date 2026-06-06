"""Shared FastAPI dependencies and typed annotations.

OGTV Writer is a single-operator internal tool, so there is **no login**. The
only shared dependency routes need is a request-scoped database session:

    from app.dependencies import DbSession

    @router.get("/scripts")
    def scripts_page(db: DbSession): ...

If you later open this up to multiple OnlyGainsTV studio roles, reintroduce a
`CurrentUser` dependency here and gate routes with it — every route already
takes `db` the same way, so adding `user` alongside it is mechanical.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

# --- Typed annotations (use these in route signatures) -----------------------
DbSession = Annotated[Session, Depends(get_db)]
