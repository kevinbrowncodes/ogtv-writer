"""Seed the database with sample OnlyGainsTV studio data.

Run it with either:

    make seed
    python -m scripts.seed

Idempotent: safe to run repeatedly (skips data that already exists). There is
no login in OGTV Writer, so this only seeds prompts, scripts, templates, tags.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a plain file (`python scripts/seed.py`) by putting the repo
# root on sys.path. (Not needed for `python -m scripts.seed`.)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db  # noqa: E402
from app.schemas.prompt import PromptCreate  # noqa: E402
from app.schemas.script import ScriptCreate  # noqa: E402
from app.schemas.script_template import ScriptTemplateCreate  # noqa: E402
from app.schemas.tag import TagCreate  # noqa: E402
from app.services import (  # noqa: E402
    prompt_service,
    script_service,
    script_template_service,
    tag_service,
)

SAMPLE_TAGS = [
    ("gym", "theme"),
    ("sunrise", "theme"),
    ("transformation", "theme"),
    ("veo", "model"),
    ("wan", "model"),
    ("cinematic", "style"),
    ("hype", "style"),
]

SAMPLE_TEMPLATES = [
    ScriptTemplateCreate(
        name="Veo cinematic hero",
        description="High-detail, photorealistic hero shot for Google Veo.",
        category="model-pattern",
        target_model="veo",
        output_format="cinematic",
        body=(
            "**Subject:** {subject}\n"
            "**Camera:** {camera}\n"
            "**Lighting:** {lighting}\n"
            "**Mood:** {mood}\n"
            "**Prompt for {model}:** {subject}, {camera}, {lighting}, photorealistic 4K, filmic grade.\n"
            "**Voice of {brand}.**"
        ),
    ),
    ScriptTemplateCreate(
        name="Wan smooth-motion loop",
        description="Coherent, stable motion pattern tuned for Wan.",
        category="model-pattern",
        target_model="wan",
        output_format="short-form",
        body=(
            "**Loop subject:** {subject}\n"
            "**Motion:** {camera}, smooth and continuous\n"
            "**Lighting:** {lighting}\n"
            "**Keep:** stable subject identity, no flicker"
        ),
    ),
    ScriptTemplateCreate(
        name="4-shot structure",
        description="Reusable establish → action → detail → payoff shot structure.",
        category="shot-structure",
        target_model="generic",
        output_format="shot-list",
        body=(
            "1. Establish {subject} — {lighting}\n"
            "2. Action beat — {camera}\n"
            "3. Detail insert — macro\n"
            "4. Payoff — {mood}"
        ),
    ),
]

SAMPLE_PROMPTS = [
    PromptCreate(
        title="Sunrise stadium stairs",
        body=(
            "# Scene\n"
            "A lone athlete sprints up empty stadium stairs at sunrise. Breath visible "
            "in the cold air, determination on their face, city skyline behind."
        ),
        tags="gym, sunrise, cinematic",
        status="ready",
    ),
    PromptCreate(
        title="Chalk and iron",
        body=(
            "# Scene\n"
            "Close-up of hands chalking up before a heavy deadlift. Dust catches the "
            "light. Slow build to the lift, veins and tension, then the lockout."
        ),
        tags="gym, hype",
        status="draft",
    ),
    PromptCreate(
        title="12-week transformation reveal",
        body=(
            "# Concept\n"
            "Side-by-side transformation montage — week 1 to week 12. Same lighting, "
            "same pose, dramatic change. End on a confident smile to camera."
        ),
        tags="transformation",
        status="draft",
    ),
]


def main() -> None:
    init_db()

    with SessionLocal() as db:
        # --- Tags -------------------------------------------------------------
        if tag_service.count_tags(db) == 0:
            for name, kind in SAMPLE_TAGS:
                tag_service.create_tag(db, TagCreate(name=name, kind=kind))
            print(f"✓ Created {len(SAMPLE_TAGS)} tags")
        else:
            print("• Tags already present — skipping")

        # --- Templates --------------------------------------------------------
        if script_template_service.count_templates(db) == 0:
            for tpl in SAMPLE_TEMPLATES:
                script_template_service.create_template(db, tpl)
            print(f"✓ Created {len(SAMPLE_TEMPLATES)} templates")
        else:
            print("• Templates already present — skipping")

        # --- Prompts ----------------------------------------------------------
        if prompt_service.count_prompts(db) == 0:
            for prompt in SAMPLE_PROMPTS:
                prompt_service.create_prompt(db, prompt)
            print(f"✓ Created {len(SAMPLE_PROMPTS)} prompts")
        else:
            print("• Prompts already present — skipping")

        # --- Scripts ----------------------------------------------------------
        if script_service.count_scripts(db) == 0:
            # A draft from the first prompt...
            script_service.create_script(
                db,
                ScriptCreate(
                    title="Sunrise stairs — cinematic v1",
                    body="# Sunrise stairs\n\nHook: breath in cold air. Build: the climb. Payoff: skyline.",
                    status="draft",
                    target_model="veo",
                    output_format="cinematic",
                    tags="gym, sunrise, cinematic",
                ),
            )
            # ...plus a couple in later lifecycle states for the dashboard.
            script_service.create_script(
                db,
                ScriptCreate(
                    title="Chalk and iron — short-form v1",
                    body="# Chalk and iron\n\nHook: hands hit the chalk. Build: the bar bends. Payoff: lockout.",
                    status="ready",
                    target_model="wan",
                    output_format="short-form",
                    tags="gym, hype",
                ),
            )
            script_service.create_script(
                db,
                ScriptCreate(
                    title="Transformation reveal — montage v1",
                    body="# Transformation\n\nWeek 1 → Week 12 montage, matched framing, confident finish.",
                    status="used",
                    target_model="generic",
                    output_format="montage",
                    tags="transformation",
                ),
            )
            print(f"✓ Created sample scripts ({script_service.count_scripts(db)} total)")
        else:
            print("• Scripts already present — skipping")

    print("Done.")


if __name__ == "__main__":
    main()
