"""Logging setup.

A single `configure_logging()` call wires up the root logger. In development we
use a compact, human-readable format; in production we emit a more structured
line that's easy to grep or ship to a log aggregator.

Usage (done once in main.py):

    from app.logging_config import configure_logging
    configure_logging(settings)

Then anywhere:

    import logging
    log = logging.getLogger(__name__)
    log.info("something happened", extra={"item_id": 5})
"""

from __future__ import annotations

import logging
import sys

from app.config import Settings

_DEV_FORMAT = "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"
_PROD_FORMAT = 'time=%(asctime)s level=%(levelname)s logger=%(name)s msg="%(message)s"'


def configure_logging(settings: Settings) -> None:
    """Configure the root logger based on the current environment."""
    level = logging.DEBUG if settings.debug else logging.INFO
    fmt = _DEV_FORMAT if settings.is_development else _PROD_FORMAT

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))

    root = logging.getLogger()
    root.handlers.clear()  # avoid duplicate handlers on reload
    root.addHandler(handler)
    root.setLevel(level)

    # Tame noisy third-party loggers in dev.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )

    logging.getLogger(__name__).debug(
        "Logging configured (env=%s, level=%s)", settings.environment, logging.getLevelName(level)
    )
