"""Application configuration.

All configuration comes from environment variables (or a local `.env` file),
parsed and validated by pydantic-settings. This is the ONLY place env vars are
read — everything else imports `get_settings()`.

WHERE TO ADD CONFIG: add a new typed field below, give it a sensible default,
and document it in `.env.example`. That's the whole loop.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "production", "test"]


class Settings(BaseSettings):
    """Typed application settings.

    Field names map to UPPER_CASE env vars automatically (case-insensitive),
    e.g. the field ``app_name`` is populated from ``APP_NAME``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated env vars rather than erroring
        case_sensitive=False,
    )

    # --- App identity ---------------------------------------------------------
    app_name: str = "OGTV Writer"
    app_url: str = "http://localhost:8000"
    app_description: str = "OnlyGainsTV Writer — generate, organize, and export AI video scripts."
    brand_name: str = "OnlyGainsTV"

    # Build stamp (YYMMDD-HHMM, US Eastern) baked into the image at deploy by
    # `make deploy` and shown in the footer + /healthz. Left blank locally — the app
    # then falls back to the process start time (see app/version.py).
    build_version: str = ""

    # --- Environment ----------------------------------------------------------
    environment: Environment = "development"
    debug: bool = True

    # --- Security -------------------------------------------------------------
    # Still used to sign the session cookie that carries one-shot flash messages.
    # (There is no login in this internal tool — see app/dependencies.py.)
    secret_key: str = "dev-only-insecure-change-me"

    # --- Database -------------------------------------------------------------
    database_url: str = "sqlite:///./data/app.db"

    # Apply pending Alembic migrations on startup (great for local dev). Turn OFF in
    # production and run `alembic upgrade head` as a deploy step — the app then only
    # verifies the DB is at head and refuses to start if it isn't.
    auto_migrate: bool = True

    # Root holding shoot folders (data/logline/<channel>/<shoot>/01.jpg). Folder-based
    # jobs read the frame from here and write the produced scripts back into the folder.
    source_root: str = "data/logline"

    # Folder names to hide from the Shoots dashboard + job picker entirely, matched at
    # ANY depth under SOURCE_ROOT (a top-level "wip" channel and a nested "archive"
    # grouping are both skipped). Comma-separated; e.g. work-in-progress or archived
    # shoots not meant to appear in the live views.
    shoots_excluded_channels: str = "wip,archive"

    # --- Server ---------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Feature flags --------------------------------------------------------
    # Gate whole areas of the app without touching code. Read them in templates
    # (`settings.feature_*`) or in routes to short-circuit with a 404/redirect.
    feature_dark_mode: bool = True
    feature_dashboard: bool = True

    # >>> ADD APP-SPECIFIC SETTINGS BELOW THIS LINE <<<
    # Gemini powers the script generator (multimodal: prompt + first-frame image).
    # Get a key at https://aistudio.google.com; generation is disabled until set.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # How many times the worker tries a job before giving up. Only *transient* failures
    # (rate-limit / network / 5xx) are retried; a content block fails immediately.
    max_attempts: int = 3

    # --- Local model (DGX Spark / OpenAI-compatible) --------------------------
    # A self-hosted, OpenAI-compatible endpoint (e.g. vLLM) offered in the model picker
    # alongside Gemini. A BLANK base URL disables the local provider entirely — nothing
    # local shows up. No API key is needed for a LAN box (leave it blank).
    local_model_base_url: str = ""
    local_model_api_key: str = ""
    # Curated allowlist of model names to offer (comma-separated). When set, ONLY these
    # appear in the picker (keeps the dropdown to a couple of sane choices); when blank,
    # the live /v1/models list is used instead.
    local_model_names: str = ""

    # --- Derived helpers ------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        return self.environment == "test"

    @property
    def cookie_secure(self) -> bool:
        """Only send the session cookie over HTTPS in production."""
        return self.is_production


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the `.env` file is parsed once per process. Tests can clear the
    cache with `get_settings.cache_clear()` after monkeypatching env vars.
    """
    return Settings()
