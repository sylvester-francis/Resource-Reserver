"""Configuration management for CLI client."""

import json
import os
import time
from datetime import datetime
from pathlib import Path


class CLIConfig:
    """Configuration manager for CLI client."""

    # API version to use
    API_VERSION = "v1"

    def __init__(self):
        # Use environment variable if set, otherwise use default
        config_dir = os.getenv("CLI_CONFIG_DIR", "~/.reservation-cli")
        self.config_dir = Path(config_dir).expanduser()
        self.token_file = self.config_dir / "auth.json"
        base_url = os.getenv("API_URL", "http://localhost:8000")
        # Ensure base URL doesn't have trailing slash
        self.base_url = base_url.rstrip("/")
        # API URL with version prefix
        self.api_url = f"{self.base_url}/api/{self.API_VERSION}"

        # Ensure config directory exists (parents=True creates parent dirs if needed)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_token(
        self,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int | None = None,
    ) -> None:
        """Save authentication tokens.

        Args:
            access_token: The JWT access token
            refresh_token: Optional refresh token for token rotation
            expires_in: Optional token expiry time in seconds
        """
        auth_data = {
            "access_token": access_token,
            "saved_at": time.time(),
        }

        if refresh_token:
            auth_data["refresh_token"] = refresh_token

        if expires_in:
            auth_data["expires_in"] = expires_in
            auth_data["expires_at"] = time.time() + expires_in

        with open(self.token_file, "w") as f:
            json.dump(auth_data, f, indent=2)

    def load_token(self) -> str | None:
        """Load access token."""
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file) as f:
                auth_data = json.load(f)
                return auth_data.get("access_token")
        except (json.JSONDecodeError, KeyError):
            return None

    def load_refresh_token(self) -> str | None:
        """Load refresh token."""
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file) as f:
                auth_data = json.load(f)
                return auth_data.get("refresh_token")
        except (json.JSONDecodeError, KeyError):
            return None

    def load_auth_data(self) -> dict | None:
        """Load all authentication data."""
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return None

    def is_token_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if the access token is expired or about to expire.

        Args:
            buffer_seconds: Number of seconds before expiry to consider as expired

        Returns:
            True if token is expired or will expire within buffer_seconds
        """
        auth_data = self.load_auth_data()
        if not auth_data:
            return True

        expires_at = auth_data.get("expires_at")
        if not expires_at:
            # If no expiry info, assume 30 minutes from save time
            saved_at = auth_data.get("saved_at", 0)
            expires_at = saved_at + (30 * 60)  # 30 minutes default

        return time.time() >= (expires_at - buffer_seconds)

    def get_token_expiry_time(self) -> datetime | None:
        """Get the token expiry time as a datetime object."""
        auth_data = self.load_auth_data()
        if not auth_data:
            return None

        expires_at = auth_data.get("expires_at")
        if expires_at:
            return datetime.fromtimestamp(expires_at)
        return None

    def clear_token(self) -> None:
        """Clear stored authentication token."""
        if self.token_file.exists():
            self.token_file.unlink()

    def get_auth_headers(self) -> dict:
        """Get authentication headers for API requests."""
        token = self.load_token()
        if not token:
            raise ValueError("Not authenticated. Please login first.")
        return {"Authorization": f"Bearer {token}"}


# Global config instance
config = CLIConfig()
