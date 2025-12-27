"""Application configuration settings."""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = "Resource Reservation System"
    app_version: str = "2.0.1"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    api_url: str = os.getenv("API_URL", "http://localhost:8000")

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", "sqlite:///./data/resource_reserver_dev.db"
    )

    # Authentication
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # Rate Limiting
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

    # Rate limits per minute for different user types
    rate_limit_anonymous: str = os.getenv("RATE_LIMIT_ANONYMOUS", "20/minute")
    rate_limit_authenticated: str = os.getenv("RATE_LIMIT_AUTHENTICATED", "100/minute")
    rate_limit_admin: str = os.getenv("RATE_LIMIT_ADMIN", "500/minute")

    # Specific endpoint rate limits
    rate_limit_auth: str = os.getenv("RATE_LIMIT_AUTH", "5/minute")  # Login/register
    rate_limit_heavy: str = os.getenv("RATE_LIMIT_HEAVY", "10/minute")  # CSV upload

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000",
    ]

    # Redis Cache
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    cache_ttl_resources: int = int(os.getenv("CACHE_TTL_RESOURCES", "30"))  # seconds
    cache_ttl_stats: int = int(os.getenv("CACHE_TTL_STATS", "60"))  # seconds
    cache_ttl_user_session: int = int(
        os.getenv("CACHE_TTL_USER_SESSION", "300")
    )  # 5 minutes

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
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra environment variables


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
