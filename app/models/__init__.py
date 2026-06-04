"""ORM models package.

Importing every model here ensures it's registered on `Base.metadata` before
`init_db()` / migrations run. When you add a new model file, add it to the
imports below.
"""

from app.models.item import Item
from app.models.user import User

__all__ = ["Item", "User"]
