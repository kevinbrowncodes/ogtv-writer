"""Application factory + wiring.

`create_app()` builds the FastAPI instance: middleware, static files, routers,
templates, and exception handlers. A module-level `app` is exported so you can
run the server with:

    uvicorn app.main:app --reload

Add a new feature area by writing a router under `app/routes/` and including it
in `_register_routers()` below — that's the one place routers are mounted.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import init_db
from app.dependencies import NotAuthenticated
from app.logging_config import configure_logging
from app.routes import auth, health, items, pages, pwa
from app.routes import settings as settings_routes
from app.templating import templates

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks.

    We create tables on startup for a frictionless dev/test experience. In
    production you'd run migrations instead (see CUSTOMIZATION.md) and can make
    this a no-op.
    """
    settings = get_settings()
    log.info("Starting %s (env=%s)", settings.app_name, settings.environment)
    init_db()
    yield
    log.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        debug=settings.debug,
        lifespan=lifespan,
        # Hide API docs in production by default (this is a server-rendered app).
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
    )

    # --- Middleware ----------------------------------------------------------
    # Signed session cookie (powers login + flash messages).
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        https_only=settings.cookie_secure,
        same_site="lax",
        session_cookie="session",
    )

    # --- Static files --------------------------------------------------------
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    _register_routers(app)
    _register_exception_handlers(app)
    return app


def _register_routers(app: FastAPI) -> None:
    """The single place routers are mounted. Add new feature routers here."""
    app.include_router(health.router)
    app.include_router(pwa.router)
    app.include_router(auth.router)
    app.include_router(pages.router)
    app.include_router(items.router)
    app.include_router(settings_routes.router)
    # >>> INCLUDE NEW FEATURE ROUTERS BELOW <<<
    # app.include_router(billing.router)


def _register_exception_handlers(app: FastAPI) -> None:
    settings = get_settings()

    @app.exception_handler(NotAuthenticated)
    async def _not_authenticated(request: Request, exc: NotAuthenticated) -> Response:
        """Send unauthenticated users to the login page.

        For HTMX requests we use the `HX-Redirect` response header so the
        browser does a full navigation instead of swapping the login page into
        a fragment.
        """
        login_url = "/login"
        if exc.next_url and exc.next_url != "/":
            login_url = f"/login?next={exc.next_url}"
        if request.headers.get("HX-Request") == "true":
            return Response(status_code=204, headers={"HX-Redirect": login_url})
        return RedirectResponse(url=login_url, status_code=303)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(request: Request, exc: StarletteHTTPException) -> Response:
        """Render a friendly 404 page for browser navigations."""
        if exc.status_code == 404 and "text/html" in request.headers.get("accept", ""):
            return templates.TemplateResponse(request, "errors/404.html", {}, status_code=404)
        # Re-raise as the default handler would (JSON for APIs, etc.).
        return Response(content=str(exc.detail), status_code=exc.status_code)

    # Only swallow tracebacks in production. In dev, let them surface so you can
    # debug with the interactive traceback.
    if settings.is_production:

        @app.exception_handler(500)
        async def _server_error(request: Request, exc: Exception) -> HTMLResponse:
            log.exception("Unhandled server error")
            return templates.TemplateResponse(request, "errors/500.html", {}, status_code=500)


# The ASGI app uvicorn/gunicorn import: `app.main:app`.
app = create_app()
