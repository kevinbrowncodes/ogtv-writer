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

    # --- Environment ----------------------------------------------------------
    environment: Environment = "development"
    debug: bool = True

    # --- Security -------------------------------------------------------------
    # Still used to sign the session cookie that carries one-shot flash messages.
    # (There is no login in this internal tool — see app/dependencies.py.)
    secret_key: str = "dev-only-insecure-change-me"

    # --- Database -------------------------------------------------------------
    database_url: str = "sqlite:///./data/app.db"

    # --- Server ---------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Feature flags --------------------------------------------------------
    # Gate whole areas of the app without touching code. Read them in templates
    # (`settings.feature_*`) or in routes to short-circuit with a 404/redirect.
    feature_dark_mode: bool = True
    feature_dashboard: bool = True

    # >>> ADD APP-SPECIFIC SETTINGS BELOW THIS LINE <<<
    # To plug a real LLM into the script generator later, add a key here and
    # read it from app/services/generation_service.py.
    # anthropic_api_key: str = ""

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
