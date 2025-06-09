import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
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
def mock_api_success():
    """Mock successful API responses for reservation commands"""
    with patch("cli.main.client") as mock_client:
        # Mock reservation data
        future_time = datetime.now(UTC) + timedelta(days=1)

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
            },
            {
                "id": 2,
                "action": "cancelled",
                "timestamp": datetime.now(UTC).isoformat(),
                "details": "Reservation cancelled by user",
                "user_id": 1,
            },
        ]

        yield mock_client


@pytest.fixture
def mock_inputs():
    """Mock all user input methods consistently"""
    with patch("typer.prompt") as mock_prompt, \
         patch("cli.main.getpass") as mock_getpass, \
         patch("typer.confirm") as mock_confirm:

        # Default return values
        mock_prompt.return_value = "testuser"
        mock_getpass.return_value = "password123"
        mock_confirm.return_value = True

        yield {
            "prompt": mock_prompt,
            "getpass": mock_getpass,
            "confirm": mock_confirm
        }


@pytest.fixture
def mock_auth_config():
    """Mock authenticated config"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = CLIConfig()
        config.config_dir = Path(temp_dir)
        config.token_file = Path(temp_dir) / "auth.json"
        config.save_token("fake_token")  # Pre-authenticate
        yield config


class TestReservationsCLI:
    """Test CLI reservation management commands"""

    def test_create_reservation_success(self, runner, mock_api_success, mock_auth_config):
        """Test creating a reservation via CLI"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "create",
                    "1",  # resource_id
                    "2025-06-08 14:00",  # start_time
                    "2h",  # duration
                ],
            )

        assert result.exit_code == 0
        assert "Reservation created successfully" in result.stdout
        mock_api_success.create_reservation.assert_called_once()

    def test_create_reservation_with_end_time(self, runner, mock_api_success, mock_auth_config):
        """Test creating reservation with explicit end time"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "create",
                    "1",
                    "2025-06-08 14:00",
                    "2025-06-08 16:00",
                ],
            )

        assert result.exit_code == 0
        assert "Reservation created successfully" in result.stdout
        mock_api_success.create_reservation.assert_called_once()

    def test_create_reservation_invalid_duration(self, runner, mock_auth_config):
        """Test creating reservation with invalid duration"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app, ["reservations", "create", "1", "2025-06-08 14:00", "invalid-duration"]
            )

        assert result.exit_code == 1
        assert "End time must be a datetime (YYYY-MM-DD HH:MM) or duration (e.g., 2h, 30m)" in result.stdout

    def test_create_reservation_past_time(self, runner, mock_api_success, mock_auth_config):
        """Test creating reservation with past time"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "create",
                    "1",
                    "2020-01-01 10:00",  # Past date
                    "2h",
                ],
            )

        assert result.exit_code == 0
        assert "Reservation created successfully" in result.stdout

    def test_create_reservation_not_authenticated(self, runner):
        """Test creating reservation without authentication"""
        with patch(
            "cli.config.config.get_auth_headers",
            side_effect=ValueError("Not authenticated"),
        ):
            result = runner.invoke(
                app, ["reservations", "create", "1", "2025-06-08 14:00", "2h"]
            )

        assert result.exit_code == 1
        assert "Please login first" in result.stdout

    def test_list_reservations_success(self, runner, mock_api_success, mock_auth_config):
        """Test listing reservations"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["reservations", "list"])

        assert result.exit_code == 0
        assert "Conference Room A" in result.stdout
        assert "Active" in result.stdout
        mock_api_success.get_my_reservations.assert_called_once()

    def test_list_reservations_include_cancelled(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test listing reservations including cancelled ones"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["reservations", "list", "--include-cancelled"])

        assert result.exit_code == 0
        mock_api_success.get_my_reservations.assert_called_once()

    def test_list_upcoming_reservations(self, runner, mock_api_success, mock_auth_config):
        """Test listing only upcoming reservations"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["reservations", "list", "--upcoming"])

        assert result.exit_code == 0
        assert "Your Reservations" in result.stdout

    def test_cancel_reservation_success(self, runner, mock_api_success, mock_auth_config):
        """Test cancelling a reservation"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "cancel",
                    "1",  # reservation_id
                    "--reason",
                    "Test cancellation",
                    "--force",  # Skip confirmation
                ],
            )

        assert result.exit_code == 0
        assert "cancelled successfully" in result.stdout
        mock_api_success.cancel_reservation.assert_called_once()

    def test_cancel_reservation_with_confirmation(
        self, runner, mock_api_success, mock_auth_config, mock_inputs
    ):
        """Test cancelling reservation with confirmation dialog"""
        mock_inputs["confirm"].return_value = True

        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                ["reservations", "cancel", "1", "--reason", "Meeting cancelled"],
            )

        assert result.exit_code == 0
        assert "cancelled successfully" in result.stdout

    def test_cancel_reservation_abort(self, runner, mock_api_success, mock_auth_config, mock_inputs):
        """Test aborting reservation cancellation"""
        mock_inputs["confirm"].return_value = False

        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["reservations", "cancel", "1"])

        assert result.exit_code == 0
        assert "Cancellation aborted" in result.stdout
        mock_api_success.cancel_reservation.assert_not_called()

    def test_show_reservation_history(self, runner, mock_api_success, mock_auth_config):
        """Test showing reservation history"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "history",
                    "1",  # reservation_id
                ],
            )

        assert result.exit_code == 0
        assert "History for Reservation 1" in result.stdout
        assert "Created" in result.stdout
        assert "Cancelled" in result.stdout
        mock_api_success.get_reservation_history.assert_called_once_with(1)

    def test_show_reservation_history_detailed(self, runner, mock_api_success, mock_auth_config):
        """Test showing detailed reservation history"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["reservations", "history", "1", "--detailed"])

        assert result.exit_code == 0
        assert "History for Reservation 1" in result.stdout

    def test_quick_reserve_command(self, runner, mock_api_success, mock_auth_config):
        """Test quick reserve command shortcut"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reserve",  # Quick command
                    "1",
                    "2025-06-08 14:00",
                    "2h",
                ],
            )

        assert result.exit_code == 0
        assert "Quick reservation created" in result.stdout
        mock_api_success.create_reservation.assert_called_once()

    def test_upcoming_command_shortcut(self, runner, mock_api_success, mock_auth_config):
        """Test upcoming reservations shortcut command"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["upcoming"])

        assert result.exit_code == 0
        assert "Upcoming Reservations" in result.stdout
        mock_api_success.get_my_reservations.assert_called_once()
