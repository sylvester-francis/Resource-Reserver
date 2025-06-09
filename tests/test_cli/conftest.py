"""Shared fixtures for CLI tests."""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cli.config import CLIConfig


@pytest.fixture
def runner():
    """CLI test runner"""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock CLI configuration with temporary directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = CLIConfig()
        config.config_dir = Path(temp_dir)
        config.token_file = Path(temp_dir) / "auth.json"
        yield config


@pytest.fixture
def mock_auth_config():
    """Mock authenticated CLI configuration"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = CLIConfig()
        config.config_dir = Path(temp_dir)
        config.token_file = Path(temp_dir) / "auth.json"
        config.save_token("fake_token")  # Pre-authenticate
        yield config


@pytest.fixture
def mock_api_success():
    """Mock successful API responses for CLI commands"""
    with patch("cli.main.client") as mock_client:
        # Mock reservation data
        future_time = datetime.now(UTC) + timedelta(days=1)

        # Auth responses
        mock_client.register.return_value = {"username": "testuser", "id": 1}
        mock_client.login.return_value = "fake_jwt_token"
        mock_client.health_check.return_value = {"status": "healthy"}

        # Resource responses
        mock_client.list_resources.return_value = [
            {
                "id": 1,
                "name": "Conference Room A",
                "tags": ["meeting"],
                "available": True,
            },
            {"id": 2, "name": "Lab Equipment", "tags": ["lab"], "available": True},
        ]
        mock_client.create_resource.return_value = {"id": 3, "name": "New Resource"}
        mock_client.search_resources.return_value = [
            {"id": 1, "name": "Conference Room A"}
        ]
        mock_client.upload_resources_csv.return_value = {
            "created_count": 2,
            "errors": [],
        }

        # Reservation responses
        mock_client.get_my_reservations.return_value = [
            {
                "id": 1,
                "resource_id": 1,
                "resource": {"id": 1, "name": "Conference Room A"},
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=2)).isoformat(),
                "status": "active",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]
        mock_client.create_reservation.return_value = {
            "id": 2,
            "resource": {"id": 1, "name": "Conference Room A"},
            "start_time": future_time.isoformat(),
            "end_time": (future_time + timedelta(hours=1)).isoformat(),
            "status": "active",
        }
        mock_client.cancel_reservation.return_value = {
            "message": "Reservation cancelled successfully",
            "reservation_id": 1,
        }
        mock_client.get_reservation_history.return_value = [
            {
                "id": 1,
                "action": "created",
                "timestamp": datetime.now(UTC).isoformat(),
                "details": "Reservation created",
                "user_id": 1,
            }
        ]

        # System responses
        mock_client.get_availability_summary.return_value = {
            "total_resources": 5,
            "available_now": 3,
            "unavailable_now": 2,
            "currently_in_use": 1,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        mock_client.manual_cleanup_expired.return_value = {
            "expired_count": 0,
            "cleaned_reservations": [],
            "message": "Successfully cleaned up 0 expired reservations",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        yield mock_client


@pytest.fixture
def mock_inputs():
    """Mock all user input methods consistently"""
    with (
        patch("typer.prompt") as mock_prompt,
        patch("cli.main.getpass") as mock_getpass,
        patch("typer.confirm") as mock_confirm,
    ):
        # Default return values
        mock_prompt.return_value = "testuser"
        mock_getpass.return_value = "password123"
        mock_confirm.return_value = True

        yield {"prompt": mock_prompt, "getpass": mock_getpass, "confirm": mock_confirm}
