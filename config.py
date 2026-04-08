"""
Application configuration management with environment variable loading.
Provides secure configuration loading with validation and type safety.
"""

import os
from dataclasses import dataclass

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not available, skip .env loading
    pass


def _get_env(name: str, required: bool = True, default: str | None = None) -> str:
    """Get environment variable with validation."""
    value = os.getenv(name, default)

    if required and not value:
        # For development, provide helpful error message with guidance
        app_env = os.getenv("APP_ENV", "local")
        if app_env == "local":
            raise RuntimeError(
                f"Missing required environment variable: {name}. "
                f"Please copy .env.example to .env and fill in the required values."
            )
        else:
            raise RuntimeError(f"Missing required environment variable: {name}")

    return value or ""


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""
    # AI
    gemini_api_key: str

    # News
    news_api_key: str

    # Email
    smtp_email: str
    smtp_password: str
    smtp_server: str
    smtp_port: int

    # App
    app_env: str  # local or production


def load_settings() -> Settings:
    """
    Load application settings from environment variables.

    Returns:
        Settings: Configured settings object with all required values

    Raises:
        RuntimeError: If any required environment variable is missing or invalid
    """
    try:
        smtp_port = int(_get_env("SMTP_PORT"))
    except ValueError as exc:
        raise RuntimeError("SMTP_PORT must be a valid integer") from exc

    return Settings(
        gemini_api_key=_get_env("GEMINI_API_KEY"),
        news_api_key=_get_env("NEWS_API_KEY"),
        smtp_email=_get_env("SMTP_EMAIL"),
        smtp_password=_get_env("SMTP_PASSWORD"),
        smtp_server=_get_env("SMTP_SERVER"),
        smtp_port=smtp_port,
        app_env=_get_env("APP_ENV", required=False, default="local"),
    )


settings = load_settings()
