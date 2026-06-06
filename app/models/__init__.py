"""ORM models package.

Importing every model here ensures it's registered on `Base.metadata` before
`init_db()` / migrations run. When you add a new model file, add it to the
imports below.
"""

from app.models.job import Job
from app.models.prompt import Prompt
from app.models.script import Script
from app.models.script_template import ScriptTemplate
from app.models.tag import Tag

__all__ = ["Job", "Prompt", "Script", "ScriptTemplate", "Tag"]
