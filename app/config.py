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
    app_name: str = "Hyperstack"
    app_url: str = "http://localhost:8000"
    app_description: str = "A generic FastAPI + HTMX + Tailwind starter."

    # --- Environment ----------------------------------------------------------
    environment: Environment = "development"
    debug: bool = True

    # --- Security -------------------------------------------------------------
    secret_key: str = "dev-only-insecure-change-me"

    # --- Database -------------------------------------------------------------
    database_url: str = "sqlite:///./data/app.db"

    # --- Server ---------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Seed / demo credentials ---------------------------------------------
    seed_user_email: str = "admin@example.com"
    seed_user_password: str = "password123"

    # --- Feature flags --------------------------------------------------------
    # Gate whole areas of the app without touching code. Read them in templates
    # (`settings.feature_*`) or in routes to short-circuit with a 404/redirect.
    feature_signups: bool = True
    feature_dark_mode: bool = True
    feature_dashboard: bool = True

    # >>> ADD APP-SPECIFIC SETTINGS BELOW THIS LINE <<<
    # stripe_secret_key: str = ""
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
