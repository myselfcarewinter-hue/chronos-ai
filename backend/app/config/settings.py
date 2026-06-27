"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Chronos AI"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "chronos_ai"

    # Google Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # JWT
    jwt_secret_key: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Scheduler
    guardian_interval_minutes: int = 60
    reflection_hour: int = 23
    reflection_minute: int = 0

    # Gamification
    xp_per_task_complete: int = 100
    xp_per_subtask_complete: int = 25
    streak_bonus_multiplier: float = 1.5

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _validate_jwt_secret(self) -> "Settings":
        """Prevent deployment with the default JWT secret in non-development environments."""
        if self.environment != "development" and self.jwt_secret_key == _DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET_KEY must be changed from the default value "
                f"in {self.environment} environment. "
                "Set a strong random secret via the JWT_SECRET_KEY environment variable."
            )
        return self

    @property
    def is_gemini_configured(self) -> bool:
        """Return True when the Gemini API key is present."""
        return bool(self.gemini_api_key)

    @property
    def is_google_oauth_configured(self) -> bool:
        """Return True when Google OAuth credentials are present."""
        return bool(self.google_client_id and self.google_client_secret)

    def log_startup_status(self) -> None:
        """Log a human-readable summary of configured features at startup."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== Chronos AI Configuration ===")
        logger.info("Environment : %s", self.environment)
        logger.info("Debug mode  : %s", self.debug)
        logger.info("Gemini AI   : %s", "configured" if self.is_gemini_configured else "MISSING — fallback mode")
        logger.info("Google OAuth: %s", "configured" if self.is_google_oauth_configured else "MISSING — demo mode only")
        logger.info("MongoDB URI : %s", self.mongo_uri)
        logger.info("CORS origins: %s", self.cors_origin_list)
        logger.info("===============================")


@lru_cache
def get_settings() -> Settings:
    return Settings()

