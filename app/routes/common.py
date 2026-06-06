"""Small helpers shared across feature routers."""

from __future__ import annotations

from pydantic import ValidationError


def field_errors(exc: ValidationError) -> dict[str, str]:
    """Flatten a pydantic ValidationError into {field: message} for templates."""
    errors: dict[str, str] = {}
    for err in exc.errors():
        field = str(err["loc"][-1]) if err["loc"] else "_"
        errors.setdefault(field, err["msg"])
    return errors
