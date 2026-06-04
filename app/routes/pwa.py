"""PWA endpoints: web app manifest + service worker.

Both are served from the site ROOT (not /static) on purpose:
  - The manifest is generated dynamically so it always reflects APP_NAME.
  - The service worker must be served at root with `Service-Worker-Allowed: /`
    so it can control the whole origin (scope "/").
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from app.config import get_settings

router = APIRouter(tags=["pwa"])

STATIC_DIR = Path(__file__).parent.parent / "static"


@router.get("/manifest.webmanifest", include_in_schema=False)
def manifest() -> JSONResponse:
    settings = get_settings()
    data = {
        "name": settings.app_name,
        "short_name": settings.app_name,
        "description": settings.app_description,
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0b0f17",
        "theme_color": "#0b0f17",
        "icons": [
            {
                "src": "/static/icons/icon.svg",
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any maskable",
            }
        ],
    }
    return JSONResponse(data, media_type="application/manifest+json")


@router.get("/service-worker.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "service-worker.js",
        media_type="application/javascript",
        headers={
            # Allow the SW (served at root) to control the entire site.
            "Service-Worker-Allowed": "/",
            # Never let the SW file itself be cached stale.
            "Cache-Control": "no-cache",
        },
    )
