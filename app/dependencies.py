"""Shared FastAPI dependencies and typed annotations.

Import these in routes to keep signatures short and consistent:

    from app.dependencies import DbSession, CurrentUser, OptionalUser

    @router.get("/items")
    def list_items(db: DbSession, user: CurrentUser): ...

Auth model: a signed session cookie stores the logged-in user's id under
`session["user_id"]`. `require_user` enforces login; `OptionalUser` doesn't.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services import user_service

SESSION_USER_KEY = "user_id"


class NotAuthenticated(Exception):
    """Raised by `require_user` when no valid session exists.

    Handled centrally in main.py — redirects browsers to /login and sends an
    `HX-Redirect` header for HTMX requests.
    """

    def __init__(self, next_url: str | None = None) -> None:
        self.next_url = next_url
        super().__init__("Authentication required")


def get_current_user_optional(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Return the logged-in user, or None. Never raises."""
    user_id = request.session.get(SESSION_USER_KEY)
    if user_id is None:
        return None
    user = user_service.get_by_id(db, user_id)
    if user is None or not user.is_active:
        # Stale or disabled account: clear the cookie.
        request.session.pop(SESSION_USER_KEY, None)
        return None
    return user


def require_user(
    request: Request,
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """Require an authenticated, active user or raise `NotAuthenticated`."""
    if user is None:
        raise NotAuthenticated(next_url=request.url.path)
    return user


# --- Typed annotations (use these in route signatures) -----------------------
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(require_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
