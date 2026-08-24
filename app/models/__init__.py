"""ORM models package.

Importing every model here ensures it's registered on `Base.metadata` before
`init_db()` / migrations run. When you add a new model file, add it to the
imports below.
"""

from app.models.job import Job
from app.models.preference import Preference
from app.models.script import Script
from app.models.tag import Tag

__all__ = ["Job", "Preference", "Script", "Tag"]
