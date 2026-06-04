"""Health check endpoint — useful for Docker/Kubernetes/load-balancer probes."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
    }
