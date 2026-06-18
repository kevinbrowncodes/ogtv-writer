"""Build version stamp — the single source of the app's date/time build label.

The stamp is ``YYMMDD-HHMM`` in **US Eastern** (24-hour / military) time, e.g.
``260618-0921`` → shown in the UI as ``Build 260618-0921``.

At deploy time ``make deploy`` computes the current stamp and bakes it into the
Docker image as the ``BUILD_VERSION`` env var, so the running build is fixed and
verifiable (footer + ``/healthz``). Locally (``make dev``) ``BUILD_VERSION`` is
blank, so we fall back to :data:`STARTUP_BUILD_STAMP` — the time this process
started — which keeps the slot populated without turning into a ticking clock.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings

# US Eastern. Requires the IANA tz database — guaranteed in Docker via the
# ``tzdata`` dependency (the slim Python image ships none).
EASTERN = ZoneInfo("America/New_York")


def current_build_stamp(now: datetime | None = None) -> str:
    """Return the build stamp ``YYMMDD-HHMM`` in US Eastern (24-hour) time.

    ``now`` may be any timezone-aware datetime (it is converted to Eastern first);
    when omitted, the current time is used. The ``now`` seam keeps this unit-testable
    without monkeypatching the clock.
    """
    moment = now if now is not None else datetime.now(EASTERN)
    return moment.astimezone(EASTERN).strftime("%y%m%d-%H%M")


# Computed once, at import — the local/dev fallback when BUILD_VERSION is unset.
STARTUP_BUILD_STAMP = current_build_stamp()


def resolve_build_version() -> str:
    """The build version to display: the baked deploy-time stamp, or the dev fallback."""
    return get_settings().build_version or STARTUP_BUILD_STAMP
