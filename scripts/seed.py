"""Seed the database with sample OnlyGainsTV studio data.

Run it with either:

    make seed
    python -m scripts.seed

Idempotent: safe to run repeatedly (skips data that already exists). There is no
login in OGTV Writer; this seeds tags and a few sample scripts. Prompts live as
``.md`` files in ``app/static/prompts/``, and scripts are normally produced by jobs.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a plain file (`python scripts/seed.py`) by putting the repo
# root on sys.path. (Not needed for `python -m scripts.seed`.)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import migrations_runner  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.schemas.script import ScriptCreate  # noqa: E402
from app.schemas.tag import TagCreate  # noqa: E402
from app.services import script_service, tag_service  # noqa: E402

SAMPLE_TAGS = [
    ("gym", "theme"),
    ("sunrise", "theme"),
    ("transformation", "theme"),
    ("veo", "model"),
    ("wan", "model"),
    ("cinematic", "style"),
    ("hype", "style"),
]

SAMPLE_SCRIPTS = [
    ScriptCreate(
        title="Sunrise stairs — cinematic v1",
        body="# Sunrise stairs\n\nHook: breath in cold air. Build: the climb. Payoff: skyline.",
        status="draft",
        tags="gym, sunrise, cinematic",
    ),
    ScriptCreate(
        title="Chalk and iron — short-form v1",
        body="# Chalk and iron\n\nHook: hands hit the chalk. Build: the bar bends. Payoff: lockout.",
        status="ready",
        tags="gym, hype",
    ),
    ScriptCreate(
        title="Transformation reveal — montage v1",
        body="# Transformation\n\nWeek 1 → Week 12 montage, matched framing, confident finish.",
        status="used",
        tags="transformation",
    ),
]


def main() -> None:
    migrations_runner.upgrade_to_head()

    with SessionLocal() as db:
        # --- Tags -------------------------------------------------------------
        if tag_service.count_tags(db) == 0:
            for name, kind in SAMPLE_TAGS:
                tag_service.create_tag(db, TagCreate(name=name, kind=kind))
            print(f"✓ Created {len(SAMPLE_TAGS)} tags")
        else:
            print("• Tags already present — skipping")

        # --- Scripts ----------------------------------------------------------
        if script_service.count_scripts(db) == 0:
            for script in SAMPLE_SCRIPTS:
                script_service.create_script(db, script)
            print(f"✓ Created {len(SAMPLE_SCRIPTS)} sample scripts")
        else:
            print("• Scripts already present — skipping")

    print("Done.")


if __name__ == "__main__":
    main()
