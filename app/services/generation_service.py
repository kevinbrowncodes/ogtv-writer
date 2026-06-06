"""Script generation via Google Gemini.

Replaces the old offline/deterministic generator (EPIC_001). Given a job — a
catalog prompt + an uploaded first-frame image + an optional addendum + a count —
this assembles the final prompt, calls Gemini (multimodal), and stores the raw
response on the job. Splitting that response into individual scripts is STORY_004.

The Gemini call goes through ``app/services/gemini_client.py``, which tests mock so
no live, paid calls are ever made.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.job import Job
from app.services import gemini_client, prompt_catalog
from app.services.uploads import PROJECT_ROOT

log = logging.getLogger(__name__)

# Output contract: we ask Gemini to wrap its parts in these markers so STORY_004
# can split the response reliably. Prototyped here; finalized in the parser story.
_OUTPUT_CONTRACT = (
    "\n\n---\n"
    "When you respond, wrap each script you produce between a line '<<<SCRIPT n>>>' "
    "and a line '<<<END SCRIPT>>>' (n starting at 1). If you produce a list of titles, "
    "wrap it between '<<<TITLES>>>' and '<<<END TITLES>>>'. Put any summary between "
    "'<<<SUMMARY>>>' and '<<<END SUMMARY>>>'."
)

_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def assemble_prompt(body: str, *, count: int | None, addendum: str) -> str:
    """Build the final prompt sent to Gemini.

    - Substitutes the job's count into any ``{{COUNT}}`` placeholder.
    - Appends the optional per-job addendum under a clear delimiter.
    - Appends the app output contract so the response parses cleanly (STORY_004).
    """
    text = body
    if count is not None:
        text = text.replace("{{COUNT}}", str(count))
    if addendum.strip():
        text += f"\n\n## Additional details for this job\n{addendum.strip()}"
    return text + _OUTPUT_CONTRACT


def _read_image(image_path: str) -> bytes:
    path = Path(image_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / image_path
    return path.read_bytes()


def run_job(db: Session, job: Job) -> None:
    """Generate for a single (already-claimed) job, storing the raw response.

    Always commits a terminal state — ``done`` with ``result_raw`` or ``failed``
    with ``error`` — and never raises, so the worker loop keeps running.
    """
    settings = get_settings()
    try:
        if not settings.gemini_api_key:
            raise RuntimeError("No GEMINI_API_KEY configured — set it in .env to generate.")

        prompt = prompt_catalog.get_prompt(job.prompt_slug)
        if prompt is None:
            raise RuntimeError(f"Prompt '{job.prompt_slug}' no longer exists.")

        mime = _MIME_BY_EXT.get(Path(job.image_path).suffix.lower(), "image/jpeg")
        image_bytes = _read_image(job.image_path)
        assembled = assemble_prompt(prompt.body, count=job.count, addendum=job.addendum)

        text = gemini_client.generate(
            prompt=assembled,
            image_bytes=image_bytes,
            image_mime=mime,
            model=settings.gemini_model,
            api_key=settings.gemini_api_key,
        )

        job.result_raw = text
        job.status = "done"
        job.error = ""
    except Exception as exc:  # any failure marks the job failed, never crashes the worker
        log.exception("Job %s failed", job.id)
        job.status = "failed"
        job.error = str(exc)
    finally:
        job.finished_at = _utcnow()
        db.commit()
