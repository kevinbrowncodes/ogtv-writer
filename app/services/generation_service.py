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
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.job import Job
from app.services import gemini_client, output_parser, prompt_catalog, script_service, shoots
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


@dataclass(frozen=True)
class GeminiStatus:
    """Whether the live Gemini model list could be fetched, and what to show.

    ``models`` always contains at least the configured default so the picker never
    renders empty. ``ok`` is False when the list couldn't be fetched (no key / rejected
    key / network); ``detail`` then explains why, for the operator (STORY_023).
    """

    models: list[str]
    ok: bool
    detail: str


_status_cache: GeminiStatus | None = None


def gemini_status() -> GeminiStatus:
    """Cached Gemini availability + selectable models for this process.

    A successful fetch is cached for the process lifetime. A failure (no key / rejected
    key / network) is NOT cached and falls back to just the configured default — so the
    picker keeps working and the status self-heals once the key is fixed, no restart.
    """
    global _status_cache
    if _status_cache is not None:
        return _status_cache
    settings = get_settings()
    default = settings.gemini_model
    if not settings.gemini_api_key:
        return GeminiStatus(
            models=[default],
            ok=False,
            detail="No GEMINI_API_KEY configured — set one to enable generation.",
        )
    probe = gemini_client.probe_models(settings.gemini_api_key)
    if not probe.ok or not probe.models:
        detail = probe.reason or "Gemini returned no usable models."
        log.warning("Gemini model list unavailable: %s", detail)
        return GeminiStatus(models=[default], ok=False, detail=detail)
    models = probe.models if default in probe.models else [default, *probe.models]
    status = GeminiStatus(models=models, ok=True, detail="")
    _status_cache = status
    return status


def available_models() -> list[str]:
    """Selectable Gemini models, always including the configured default.

    Thin accessor over :func:`gemini_status` (single fetch path + shared cache).
    """
    return gemini_status().models


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


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff between retries: 1s, 2s, 4s, … capped at 30s."""
    return float(min(2 ** (attempt - 1), 30))


def _sleep(seconds: float) -> None:
    """Indirection so tests can patch out the (otherwise real) backoff sleep."""
    time.sleep(seconds)


def _generate_with_retries(
    db: Session, job: Job, *, assembled: str, mime: str, settings: Settings
) -> str:
    """Call Gemini, retrying transient failures up to ``max_attempts``.

    Records each try on ``job.attempts`` (committed between tries so the live view can
    show "attempt N of M"). A :class:`gemini_client.RetryableError` is retried with a
    short backoff; any other error (including a content block) propagates immediately.
    """
    max_attempts = max(1, settings.max_attempts)
    while True:
        job.attempts += 1
        try:
            return gemini_client.generate(
                prompt=assembled,
                image_bytes=_read_image(job.image_path),
                image_mime=mime,
                model=job.model or settings.gemini_model,
                api_key=settings.gemini_api_key,
            )
        except gemini_client.RetryableError as exc:
            if job.attempts >= max_attempts:
                raise
            log.warning(
                "Job %s attempt %s/%s failed (transient): %s",
                job.id,
                job.attempts,
                max_attempts,
                exc,
            )
            db.commit()  # persist the attempt count so the live view updates
            _sleep(_backoff_seconds(job.attempts))


def run_job(db: Session, job: Job) -> None:
    """Generate for a single (already-claimed) job, storing the raw response.

    Always commits a terminal state — ``done`` with ``result_raw`` or ``failed``
    with ``error`` — and never raises, so the worker loop keeps running. Transient
    failures are retried up to ``MAX_ATTEMPTS`` (STORY_012).
    """
    settings = get_settings()
    try:
        if not settings.gemini_api_key:
            raise RuntimeError("No GEMINI_API_KEY configured — set it in .env to generate.")

        prompt = prompt_catalog.get_prompt(job.prompt_slug)
        if prompt is None:
            raise RuntimeError(f"Prompt '{job.prompt_slug}' no longer exists.")

        mime = _MIME_BY_EXT.get(Path(job.image_path).suffix.lower(), "image/jpeg")
        assembled = assemble_prompt(prompt.body, count=job.count, addendum=job.addendum)

        text = _generate_with_retries(db, job, assembled=assembled, mime=mime, settings=settings)

        parsed = output_parser.parse_response(text)
        job.result_raw = text
        job.titles = "\n".join(parsed.titles)
        job.summary = parsed.summary
        job.status = "done"
        job.error = ""
        script_service.create_generated_scripts(db, job, parsed.scripts, title_base=prompt.title)
        if job.source_dir:
            written = shoots.write_outputs(
                job.source_dir, parsed.scripts, parsed.titles, parsed.summary
            )
            job.output_files = "\n".join(written)
        if job.count and len(parsed.scripts) != job.count:
            log.warning(
                "Job %s: requested %s scripts, parsed %s", job.id, job.count, len(parsed.scripts)
            )
    except Exception as exc:  # any failure marks the job failed, never crashes the worker
        log.exception("Job %s failed", job.id)
        job.status = "failed"
        job.error = str(exc)
    finally:
        job.finished_at = _utcnow()
        db.commit()
