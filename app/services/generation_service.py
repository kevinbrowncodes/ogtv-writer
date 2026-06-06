"""Script generator — turns one markdown prompt into N structured scripts.

This is the engine behind the "Generate" workspace. Given a source prompt, a
target model (Veo / Wan / Generic), an output format, and a count, it produces
that many *distinct* draft scripts and saves them to the library.

It is deliberately **offline and deterministic**: each variation is built from a
rotating set of cinematic "lenses" (camera / lighting / mood) layered over
model- and format-specific patterns. No API key, no network — paste-ready
markdown every time. Variations differ by lens, so the same inputs reproduce.

WANT A REAL LLM LATER? Keep `create_scripts()` as the seam: swap the body of
`build_script_body()` for a Claude/OpenAI call (add the key in app/config.py and
read it here). Everything upstream — routes, library, export — stays the same.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain import FORMAT_LABELS, MODEL_LABELS
from app.models.script import Script
from app.schemas.script import ScriptCreate

# Each variation pulls the next lens; cycling these gives up to 10 distinct
# takes on the same prompt before repeating.
VARIATION_LENSES: tuple[dict[str, str], ...] = (
    {
        "label": "Hero push-in",
        "camera": "slow dolly push-in, 35mm",
        "lighting": "warm golden-hour key light",
        "mood": "triumphant, heroic",
    },
    {
        "label": "Handheld grit",
        "camera": "handheld tracking, 24mm",
        "lighting": "hard overcast daylight",
        "mood": "raw, kinetic",
    },
    {
        "label": "Drone reveal",
        "camera": "rising drone reveal, wide",
        "lighting": "cool blue-hour ambience",
        "mood": "epic, expansive",
    },
    {
        "label": "Macro detail",
        "camera": "macro detail, shallow depth of field",
        "lighting": "soft rim light, dark background",
        "mood": "intense, intimate",
    },
    {
        "label": "Orbit",
        "camera": "180° orbit around subject",
        "lighting": "neon practicals, teal & magenta",
        "mood": "stylized, electric",
    },
    {
        "label": "Locked-off",
        "camera": "locked-off tripod, symmetrical frame",
        "lighting": "clean high-key studio light",
        "mood": "clinical, confident",
    },
    {
        "label": "Low angle",
        "camera": "low-angle wide, 18mm",
        "lighting": "backlit haze, lens flare",
        "mood": "powerful, larger-than-life",
    },
    {
        "label": "Slow-mo",
        "camera": "120fps slow motion, locked",
        "lighting": "dramatic chiaroscuro",
        "mood": "weighty, cinematic",
    },
    {
        "label": "Whip pan",
        "camera": "fast whip-pan transitions",
        "lighting": "punchy sunlit contrast",
        "mood": "energetic, hype",
    },
    {
        "label": "Top-down",
        "camera": "top-down birds-eye, static",
        "lighting": "even soft daylight",
        "mood": "graphic, clean",
    },
)

# Model-specific prompt tuning + a sensible "avoid" list per model.
MODEL_GUIDANCE: dict[str, dict[str, str]] = {
    "veo": {
        "style": "photorealistic, natural physics, crisp 4K detail, subtle realistic camera motion, filmic color grade",
        "avoid": "warped anatomy, jittery motion, text artifacts, oversaturation, morphing limbs",
    },
    "wan": {
        "style": "smooth coherent motion, stable subject, stylized cinematic lighting, consistent character",
        "avoid": "flicker, identity drift, melting edges, duplicated subjects, abrupt warps",
    },
    "generic": {
        "style": "clear single subject, simple background, steady motion, balanced exposure",
        "avoid": "clutter, busy background, fast erratic motion, distorted faces",
    },
}

# Sensible aspect ratio + duration defaults per format.
FORMAT_TECH: dict[str, dict[str, str]] = {
    "short-form": {"aspect": "9:16 (vertical)", "duration": "~10s"},
    "cinematic": {"aspect": "16:9 (widescreen)", "duration": "~8s"},
    "montage": {"aspect": "9:16 or 1:1", "duration": "~12s (4 quick shots)"},
    "narrated": {"aspect": "16:9", "duration": "~15s"},
    "shot-list": {"aspect": "16:9", "duration": "per-shot (see table)"},
}

_DEFAULT_TECH = {"aspect": "16:9", "duration": "~10s"}


def create_scripts(
    db: Session,
    *,
    source_prompt: str,
    target_model: str,
    output_format: str,
    count: int,
    title_base: str = "",
    tags: str = "",
    template_body: str = "",
) -> list[Script]:
    """Generate `count` draft scripts from one prompt and persist them."""
    subject = summarize_prompt(source_prompt)
    base_title = (title_base or _title_from_subject(subject)).strip()

    created: list[Script] = []
    for i in range(1, count + 1):
        body = build_script_body(
            subject=subject,
            target_model=target_model,
            output_format=output_format,
            variation=i,
            count=count,
            title=f"{base_title} — {FORMAT_LABELS.get(output_format, output_format)} v{i}",
            tags=tags,
            template_body=template_body,
        )
        script = Script(
            **ScriptCreate(
                title=f"{base_title} v{i}",
                body=body,
                status="draft",
                target_model=target_model,
                output_format=output_format,
                prompt_source=source_prompt.strip(),
                tags=tags.strip(),
            ).model_dump()
        )
        db.add(script)
        created.append(script)

    db.commit()
    for script in created:
        db.refresh(script)
    return created


def build_script_body(
    *,
    subject: str,
    target_model: str,
    output_format: str,
    variation: int,
    count: int,
    title: str,
    tags: str = "",
    template_body: str = "",
) -> str:
    """Build the markdown for a single script variation (pure / no DB)."""
    lens = VARIATION_LENSES[(variation - 1) % len(VARIATION_LENSES)]
    guidance = MODEL_GUIDANCE.get(target_model, MODEL_GUIDANCE["generic"])
    tech = FORMAT_TECH.get(output_format, _DEFAULT_TECH)
    model_label = MODEL_LABELS.get(target_model, target_model)
    format_label = FORMAT_LABELS.get(output_format, output_format)
    brand = get_settings().brand_name

    master_prompt = (
        f"{subject}, {lens['camera']}, {lens['lighting']}, {lens['mood']}, {guidance['style']}"
    )

    ctx = {
        "subject": subject,
        "prompt": subject,
        "model": model_label,
        "format": format_label,
        "camera": lens["camera"],
        "lighting": lens["lighting"],
        "mood": lens["mood"],
        "variation": str(variation),
        "brand": brand,
    }
    if template_body.strip():
        structure = _fill_placeholders(template_body.strip(), ctx)
    else:
        structure = _structure_for_format(output_format, subject, lens, brand)

    return "\n".join(
        [
            f"# {title}",
            "",
            f"> **Model:** {model_label} · **Format:** {format_label} "
            f"· **Variation:** {variation}/{count} · **Lens:** {lens['label']}",
            "",
            "## Master prompt",
            "",
            master_prompt,
            "",
            "## Structure",
            "",
            structure,
            "",
            "## Tech",
            "",
            f"- **Aspect ratio:** {tech['aspect']}",
            f"- **Duration:** {tech['duration']}",
            f"- **Tags:** {tags.strip() or '—'}",
            "",
            "## Avoid",
            "",
            guidance["avoid"],
            "",
        ]
    )


# --- Format-specific structure builders --------------------------------------
def _structure_for_format(fmt: str, subject: str, lens: dict[str, str], brand: str) -> str:
    builder = _FORMAT_BUILDERS.get(fmt, _short_form)
    return builder(subject, lens, brand)


def _short_form(subject: str, lens: dict[str, str], brand: str) -> str:
    return "\n".join(
        [
            f"- **Hook (0–2s):** {subject} — open on a {lens['mood']} beat",
            f"- **Build (2–6s):** {lens['camera']}; escalate the action",
            f"- **Payoff (6–10s):** climactic moment under {lens['lighting']}",
            "- **On-screen text:** punchy 3–5 word caption",
            f"- **CTA:** follow {brand} for more",
        ]
    )


def _cinematic(subject: str, lens: dict[str, str], brand: str) -> str:
    return "\n".join(
        [
            f"- **Scene:** {subject}",
            f"- **Camera:** {lens['camera']}",
            f"- **Lighting & palette:** {lens['lighting']}",
            f"- **Mood:** {lens['mood']}",
            "- **Action beats:**",
            "  1. Establish the subject in the frame",
            f"  2. {lens['camera']} into the decisive moment",
            "  3. Hold on the payoff, then a slow fade",
            "- **Audio:** ambient bed with a subtle low-end swell",
        ]
    )


def _montage(subject: str, lens: dict[str, str], brand: str) -> str:
    return "\n".join(
        [
            f"- **Theme:** {subject}",
            "- **Shots (cut on the beat):**",
            f"  1. (1.5s) wide establishing — {lens['lighting']}",
            "  2. (1.0s) texture / detail insert",
            f"  3. (1.0s) motion beat — {lens['camera']}",
            f"  4. (1.5s) hero shot — {lens['mood']}",
            "- **Transitions:** hard cuts on the music",
            "- **Music:** driving, builds to the hero shot",
        ]
    )


def _narrated(subject: str, lens: dict[str, str], brand: str) -> str:
    return "\n".join(
        [
            f"- **Logline:** {subject}",
            f'- **VO 1:** "It starts here." → Visual: {lens["camera"]}',
            f'- **VO 2:** "Every rep counts." → Visual: {lens["lighting"]}',
            f'- **VO 3:** "This is the payoff." → Visual: payoff under a {lens["mood"]} tone',
            f"- **Tone:** {lens['mood']}, voice of {brand}",
        ]
    )


def _shot_list(subject: str, lens: dict[str, str], brand: str) -> str:
    return "\n".join(
        [
            "| # | Shot | Camera | Light | Dur |",
            "|---|------|--------|-------|-----|",
            f"| 1 | Establish {subject} | {lens['camera']} | {lens['lighting']} | 2s |",
            "| 2 | Subject in action | push-in | key + rim | 2s |",
            f"| 3 | Detail insert | macro | {lens['lighting']} | 1.5s |",
            f"| 4 | Payoff | {lens['camera']} | {lens['mood']} | 2s |",
        ]
    )


_FORMAT_BUILDERS = {
    "short-form": _short_form,
    "cinematic": _cinematic,
    "montage": _montage,
    "narrated": _narrated,
    "shot-list": _shot_list,
}


# --- Text helpers ------------------------------------------------------------
_MARKDOWN_PREFIX = re.compile(r"^\s*(?:[#>\-*+]+\s*|\d+[.)]\s*)")


def summarize_prompt(source: str, *, max_len: int = 240) -> str:
    """Reduce a markdown prompt to a concise subject phrase for prompt-building."""
    lines: list[str] = []
    for raw in (source or "").splitlines():
        cleaned = _MARKDOWN_PREFIX.sub("", raw).strip()
        if cleaned:
            lines.append(cleaned)
    text = " ".join(lines).strip()
    if not text:
        return "your subject"
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def _title_from_subject(subject: str, *, max_len: int = 60) -> str:
    first = re.split(r"[.!?]", subject, maxsplit=1)[0].strip(" …")
    if len(first) > max_len:
        first = first[:max_len].rsplit(" ", 1)[0]
    return first or "Untitled script"


def _fill_placeholders(template: str, ctx: dict[str, str]) -> str:
    """Replace {placeholders} in a template body without choking on stray braces."""
    out = template
    for key, value in ctx.items():
        out = out.replace("{" + key + "}", value)
    return out
