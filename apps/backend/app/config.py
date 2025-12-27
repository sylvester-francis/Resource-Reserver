"""Application configuration settings.

This module provides centralized configuration management for the Resource
Reservation System using Pydantic settings. All configuration values can be
set via environment variables or a .env file.

The settings are cached using lru_cache to avoid repeated parsing of
environment variables during the application lifecycle.

Example:
    Access settings in your application::

        from app.config import get_settings

        settings = get_settings()
        print(f"API URL: {settings.api_url}")
        print(f"Debug mode: {settings.debug}")

Environment Variables:
    All settings can be overridden via environment variables. See the
    Settings class attributes for the full list of configurable options.

Author:
    Sylvester-Francis
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support.

    This class defines all configuration options for the Resource Reservation
    System. Values can be set via environment variables (case-insensitive) or
    through a .env file in the project root.

    Attributes:
        app_name: Display name of the application.
        app_version: Current version string of the application.
        debug: Enable debug mode for additional logging and error details.
        environment: Runtime environment (development, staging, production).
        api_url: Base URL for the API server.

        database_url: SQLAlchemy database connection URL.

        secret_key: Secret key for JWT token signing. MUST be changed in production.
        algorithm: Algorithm used for JWT token signing (default: HS256).
        access_token_expire_minutes: JWT access token validity period in minutes.

        rate_limit_enabled: Enable/disable API rate limiting.
        rate_limit_testing_mode: Use higher rate limits for E2E testing.
        rate_limit_anonymous: Rate limit string for anonymous users.
        rate_limit_authenticated: Rate limit string for authenticated users.
        rate_limit_admin: Rate limit string for admin users.
        rate_limit_auth: Rate limit for authentication endpoints.
        rate_limit_heavy: Rate limit for resource-intensive endpoints.

        cors_origins: List of allowed CORS origins.

        redis_url: Redis connection URL for caching.
        cache_enabled: Enable/disable Redis caching.
        cache_ttl_resources: TTL in seconds for resource cache entries.
        cache_ttl_stats: TTL in seconds for statistics cache entries.
        cache_ttl_user_session: TTL in seconds for user session cache.

        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port.
        smtp_user: SMTP authentication username.
        smtp_password: SMTP authentication password.
        smtp_from: Default sender email address.
        smtp_from_name: Default sender display name.
        smtp_tls: Enable TLS for SMTP connection.
        smtp_ssl: Enable SSL for SMTP connection.
        email_enabled: Enable/disable email sending functionality.
        email_templates_dir: Path to email template directory.

    Example:
        Create a .env file with custom settings::

            DATABASE_URL=postgresql://user:pass@localhost/db
            SECRET_KEY=your-secure-random-key
            DEBUG=true
            REDIS_URL=redis://localhost:6379/0
    """

    # Application
    app_name: str = "Resource Reservation System"
    app_version: str = "2.0.1"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    api_url: str = os.getenv("API_URL", "http://localhost:8000")

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", "sqlite:///./data/db/resource_reserver_dev.db"
    )

    # Authentication
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # Rate Limiting
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    rate_limit_testing_mode: bool = (
        os.getenv("RATE_LIMIT_TESTING_MODE", "false").lower() == "true"
    )

    # Rate limits per minute for different user types
    rate_limit_anonymous: str = os.getenv("RATE_LIMIT_ANONYMOUS", "60/minute")
    rate_limit_authenticated: str = os.getenv("RATE_LIMIT_AUTHENTICATED", "200/minute")
    rate_limit_admin: str = os.getenv("RATE_LIMIT_ADMIN", "500/minute")

    # Specific endpoint rate limits
    rate_limit_auth: str = os.getenv("RATE_LIMIT_AUTH", "30/minute")
    rate_limit_heavy: str = os.getenv("RATE_LIMIT_HEAVY", "20/minute")

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000",
    ]

    # Redis Cache
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    cache_ttl_resources: int = int(os.getenv("CACHE_TTL_RESOURCES", "30"))
    cache_ttl_stats: int = int(os.getenv("CACHE_TTL_STATS", "60"))
    cache_ttl_user_session: int = int(os.getenv("CACHE_TTL_USER_SESSION", "300"))

    # Email Configuration (SMTP)
    smtp_host: str = os.getenv("SMTP_HOST", "localhost")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "noreply@resource-reserver.local")
    smtp_from_name: str = os.getenv("SMTP_FROM_NAME", "Resource Reserver")
    smtp_tls: bool = os.getenv("SMTP_TLS", "true").lower() == "true"
    smtp_ssl: bool = os.getenv("SMTP_SSL", "false").lower() == "true"
    email_enabled: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    email_templates_dir: str = os.getenv("EMAIL_TEMPLATES_DIR", "app/templates/email")

    class Config:
        """Pydantic model configuration.

        Attributes:
            env_file: Path to the .env file for loading environment variables.
            env_file_encoding: Character encoding for the .env file.
            extra: How to handle extra fields (ignore unknown env vars).
        """

        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns a cached Settings instance to avoid repeatedly parsing
    environment variables. The cache persists for the application's
    lifetime.

    Returns:
        Settings: The application settings instance.

    Example:
        >>> settings = get_settings()
        >>> print(settings.app_name)
        'Resource Reservation System'
    """
    return Settings()
