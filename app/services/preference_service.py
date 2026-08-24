"""Read/write studio-wide operator preferences (key/value rows).

Keys in use:
- ``default_channel`` — the channel the Shoots page's Channel filter starts on
  ("" = All channels). See STORY_028.
- ``default_model`` — the model the Shoots/Generate pickers start on
  ("" = the ``.env``-configured Gemini model). See STORY_030.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.preference import Preference

DEFAULT_CHANNEL_KEY = "default_channel"
DEFAULT_MODEL_KEY = "default_model"


def get_preference(db: Session, key: str, default: str = "") -> str:
    """Return the stored value for `key`, or `default` when unset."""
    row = db.get(Preference, key)
    return row.value if row is not None else default


def set_preference(db: Session, key: str, value: str) -> None:
    """Store `value` under `key`, creating or overwriting the row."""
    row = db.get(Preference, key)
    if row is None:
        row = Preference(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()
