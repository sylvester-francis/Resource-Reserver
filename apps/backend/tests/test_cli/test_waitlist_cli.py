"""Tests for waitlist CLI commands."""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from typer.testing import CliRunner

from cli.config import CLIConfig
from cli.main import app


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
    """Mock authenticated config"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = CLIConfig()
        config.config_dir = Path(temp_dir)
        config.token_file = Path(temp_dir) / "auth.json"
        config.save_token("fake_token")  # Pre-authenticate
        yield config


@pytest.fixture
def mock_api_success():
    """Mock successful API responses for waitlist commands"""
    with patch("cli.main.client") as mock_client:
        future_time = datetime.now(UTC) + timedelta(days=1)

        mock_client.join_waitlist.return_value = {
            "id": 1,
            "resource_id": 1,
            "user_id": 1,
            "desired_start": future_time.isoformat(),
            "desired_end": (future_time + timedelta(hours=2)).isoformat(),
            "flexible_time": False,
            "status": "waiting",
            "position": 1,
            "created_at": datetime.now(UTC).isoformat(),
        }

        mock_client.list_my_waitlist_entries.return_value = {
            "data": [
                {
                    "id": 1,
                    "resource_id": 1,
                    "resource": {"id": 1, "name": "Conference Room A"},
                    "user_id": 1,
                    "desired_start": future_time.isoformat(),
                    "desired_end": (future_time + timedelta(hours=2)).isoformat(),
                    "flexible_time": False,
                    "status": "waiting",
                    "position": 1,
                    "created_at": datetime.now(UTC).isoformat(),
                },
                {
                    "id": 2,
                    "resource_id": 2,
                    "resource": {"id": 2, "name": "Meeting Room B"},
                    "user_id": 1,
                    "desired_start": future_time.isoformat(),
                    "desired_end": (future_time + timedelta(hours=1)).isoformat(),
                    "flexible_time": True,
                    "status": "offered",
                    "position": 1,
                    "created_at": datetime.now(UTC).isoformat(),
                    "offered_at": datetime.now(UTC).isoformat(),
                    "offer_expires_at": (
                        datetime.now(UTC) + timedelta(hours=1)
                    ).isoformat(),
                },
            ],
            "next_cursor": None,
            "has_more": False,
            "total_count": 2,
        }

        mock_client.get_waitlist_entry.return_value = {
            "id": 1,
            "resource_id": 1,
            "resource": {"id": 1, "name": "Conference Room A"},
            "user_id": 1,
            "desired_start": future_time.isoformat(),
            "desired_end": (future_time + timedelta(hours=2)).isoformat(),
            "flexible_time": False,
            "status": "offered",
            "position": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "offered_at": datetime.now(UTC).isoformat(),
            "offer_expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }

        mock_client.leave_waitlist.return_value = {
            "message": "Successfully left the waitlist",
            "waitlist_id": 1,
            "status": "cancelled",
        }

        mock_client.accept_waitlist_offer.return_value = {
            "id": 10,
            "resource_id": 1,
            "resource": {"id": 1, "name": "Conference Room A"},
            "start_time": future_time.isoformat(),
            "end_time": (future_time + timedelta(hours=2)).isoformat(),
            "status": "active",
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
        mock_prompt.return_value = "testuser"
        mock_getpass.return_value = "password123"
        mock_confirm.return_value = True

        yield {"prompt": mock_prompt, "getpass": mock_getpass, "confirm": mock_confirm}


class TestWaitlistCLI:
    """Test CLI waitlist management commands"""

    def test_join_waitlist_success(self, runner, mock_api_success, mock_auth_config):
        """Test joining a waitlist via CLI"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "waitlist",
                    "join",
                    "--resource",
                    "1",
                    "--start",
                    "2025-06-08 14:00",
                    "--end",
                    "2025-06-08 16:00",
                ],
            )

        assert result.exit_code == 0
        assert "Successfully joined waitlist" in result.stdout
        assert "Position: #1" in result.stdout
        mock_api_success.join_waitlist.assert_called_once()

    def test_join_waitlist_flexible(self, runner, mock_api_success, mock_auth_config):
        """Test joining a waitlist with flexible timing"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "waitlist",
                    "join",
                    "--resource",
                    "1",
                    "--start",
                    "2025-06-08 14:00",
                    "--end",
                    "2025-06-08 16:00",
                    "--flexible",
                ],
            )

        assert result.exit_code == 0
        assert "Flexible: Yes" in result.stdout
        mock_api_success.join_waitlist.assert_called_once()
        call_args = mock_api_success.join_waitlist.call_args
        assert call_args[0][3] is True  # flexible_time parameter

    def test_join_waitlist_not_authenticated(self, runner):
        """Test joining waitlist without authentication"""
        with patch(
            "cli.config.config.get_auth_headers",
            side_effect=ValueError("Not authenticated"),
        ):
            result = runner.invoke(
                app,
                [
                    "waitlist",
                    "join",
                    "--resource",
                    "1",
                    "--start",
                    "2025-06-08 14:00",
                    "--end",
                    "2025-06-08 16:00",
                ],
            )

        assert result.exit_code == 1
        assert "Please login first" in result.stdout

    def test_join_waitlist_invalid_time(self, runner, mock_auth_config):
        """Test joining waitlist with end time before start time"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "waitlist",
                    "join",
                    "--resource",
                    "1",
                    "--start",
                    "2025-06-08 16:00",
                    "--end",
                    "2025-06-08 14:00",
                ],
            )

        assert result.exit_code == 1
        assert "End time must be after start time" in result.stdout

    def test_list_waitlist_entries(self, runner, mock_api_success, mock_auth_config):
        """Test listing waitlist entries"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["waitlist", "list"])

        assert result.exit_code == 0
        assert "Waitlist Entries" in result.stdout
        mock_api_success.list_my_waitlist_entries.assert_called_once()

    def test_list_waitlist_with_pagination(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test listing waitlist entries with pagination options"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app, ["waitlist", "list", "--limit", "5", "--sort", "position"]
            )

        assert result.exit_code == 0
        call_kwargs = mock_api_success.list_my_waitlist_entries.call_args
        assert call_kwargs[1].get("limit") == 5
        assert call_kwargs[1].get("sort_by") == "position"

    def test_list_waitlist_include_completed(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test listing waitlist entries including completed"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["waitlist", "list", "--include-completed"])

        assert result.exit_code == 0
        call_kwargs = mock_api_success.list_my_waitlist_entries.call_args
        assert call_kwargs[1].get("include_completed") is True

    def test_waitlist_status(self, runner, mock_api_success, mock_auth_config):
        """Test getting waitlist entry status"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["waitlist", "status", "1"])

        assert result.exit_code == 0
        assert "Waitlist Entry #1" in result.stdout
        assert "Conference Room A" in result.stdout
        mock_api_success.get_waitlist_entry.assert_called_once_with(1)

    def test_waitlist_status_not_found(self, runner, mock_auth_config):
        """Test getting status for non-existent waitlist entry"""
        with patch("cli.main.client") as mock_client:
            mock_client.get_waitlist_entry.side_effect = requests.exceptions.HTTPError(
                "Waitlist entry not found"
            )
            with patch("cli.main.config", mock_auth_config):
                result = runner.invoke(app, ["waitlist", "status", "999"])

        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_leave_waitlist_success(
        self, runner, mock_api_success, mock_auth_config, mock_inputs
    ):
        """Test leaving the waitlist"""
        mock_inputs["confirm"].return_value = True
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["waitlist", "leave", "1"])

        assert result.exit_code == 0
        assert "Successfully left waitlist" in result.stdout
        mock_api_success.leave_waitlist.assert_called_once_with(1)

    def test_leave_waitlist_with_force(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test leaving the waitlist with force flag"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["waitlist", "leave", "1", "--force"])

        assert result.exit_code == 0
        assert "Successfully left waitlist" in result.stdout
        mock_api_success.leave_waitlist.assert_called_once()

    def test_leave_waitlist_cancelled(
        self, runner, mock_api_success, mock_auth_config, mock_inputs
    ):
        """Test cancelling leave waitlist operation"""
        mock_inputs["confirm"].return_value = False
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["waitlist", "leave", "1"])

        assert result.exit_code == 0
        assert "cancelled" in result.stdout
        mock_api_success.leave_waitlist.assert_not_called()

    def test_accept_waitlist_offer_success(
        self, runner, mock_api_success, mock_auth_config, mock_inputs
    ):
        """Test accepting a waitlist offer"""
        mock_inputs["confirm"].return_value = True
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["waitlist", "accept", "1"])

        assert result.exit_code == 0
        assert "Reservation created from waitlist offer" in result.stdout
        assert "Reservation ID: 10" in result.stdout
        mock_api_success.accept_waitlist_offer.assert_called_once_with(1)

    def test_accept_waitlist_offer_with_force(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test accepting a waitlist offer with force flag"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["waitlist", "accept", "1", "--force"])

        assert result.exit_code == 0
        assert "Reservation created" in result.stdout

    def test_accept_waitlist_offer_expired(self, runner, mock_auth_config):
        """Test accepting an expired waitlist offer"""
        with patch("cli.main.client") as mock_client:
            future_time = datetime.now(UTC) + timedelta(days=1)
            mock_client.get_waitlist_entry.return_value = {
                "id": 1,
                "resource_id": 1,
                "resource": {"id": 1, "name": "Conference Room A"},
                "user_id": 1,
                "desired_start": future_time.isoformat(),
                "desired_end": (future_time + timedelta(hours=2)).isoformat(),
                "flexible_time": False,
                "status": "offered",
                "position": 1,
                "created_at": datetime.now(UTC).isoformat(),
            }
            mock_client.accept_waitlist_offer.side_effect = (
                requests.exceptions.HTTPError("Offer expired")
            )
            with patch("cli.main.config", mock_auth_config):
                result = runner.invoke(app, ["waitlist", "accept", "1", "--force"])

        assert result.exit_code == 1
        assert "expired" in result.stdout

    def test_accept_waitlist_no_offer(self, runner, mock_auth_config):
        """Test accepting when no offer is available"""
        with patch("cli.main.client") as mock_client:
            future_time = datetime.now(UTC) + timedelta(days=1)
            mock_client.get_waitlist_entry.return_value = {
                "id": 1,
                "resource_id": 1,
                "resource": {"id": 1, "name": "Conference Room A"},
                "user_id": 1,
                "desired_start": future_time.isoformat(),
                "desired_end": (future_time + timedelta(hours=2)).isoformat(),
                "flexible_time": False,
                "status": "waiting",  # Not offered
                "position": 1,
                "created_at": datetime.now(UTC).isoformat(),
            }
            with patch("cli.main.config", mock_auth_config):
                result = runner.invoke(app, ["waitlist", "accept", "1"])

        assert result.exit_code == 1
        assert "No active offer" in result.stdout
