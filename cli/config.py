"""Configuration management for CLI client."""

import json
import os
from pathlib import Path


class CLIConfig:
    """Configuration manager for CLI client."""

    def __init__(self):
        # Use environment variable if set, otherwise use default
        config_dir = os.getenv("CLI_CONFIG_DIR", "~/.reservation-cli")
        self.config_dir = Path(config_dir).expanduser()
        self.token_file = self.config_dir / "auth.json"
        self.api_url = os.getenv("API_URL", "http://localhost:8000")

        # Ensure config directory exists (parents=True creates parent dirs if needed)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_token(self, token: str) -> None:
        """Save authentication token."""
        auth_data = {"access_token": token}
        with open(self.token_file, "w") as f:
            json.dump(auth_data, f)

    def load_token(self) -> str | None:
        """Load authentication token."""
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file) as f:
                auth_data = json.load(f)
                return auth_data.get("access_token")
        except (json.JSONDecodeError, KeyError):
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
