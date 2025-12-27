"""CLI tests for reservation commands."""

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

        mock_client.get_my_reservations.return_value = {
            "data": [
                {
                    "id": 1,
                    "resource_id": 1,
                    "resource": {"id": 1, "name": "Conference Room A"},
                    "start_time": future_time.isoformat(),
                    "end_time": (future_time + timedelta(hours=2)).isoformat(),
                    "status": "active",
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ],
            "next_cursor": None,
            "has_more": False,
            "total_count": 1,
        }

        mock_client.create_reservation.return_value = {
            "id": 2,
            "resource": {"id": 1, "name": "Conference Room A"},
            "start_time": future_time.isoformat(),
            "end_time": (future_time + timedelta(hours=1)).isoformat(),
            "status": "active",
        }

        mock_client.create_recurring_reservation.return_value = [
            {
                "id": 2,
                "resource": {"id": 1, "name": "Conference Room A"},
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "status": "active",
            },
            {
                "id": 3,
                "resource": {"id": 1, "name": "Conference Room A"},
                "start_time": (future_time + timedelta(days=7)).isoformat(),
                "end_time": (future_time + timedelta(days=7, hours=1)).isoformat(),
                "status": "active",
            },
        ]

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

    def test_create_reservation_success(
        self, runner, mock_api_success, mock_auth_config
    ):
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

    def test_create_reservation_with_end_time(
        self, runner, mock_api_success, mock_auth_config
    ):
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
                app,
                ["reservations", "create", "1", "2025-06-08 14:00", "invalid-duration"],
            )

        assert result.exit_code == 1
        assert (
            "End time must be a datetime (YYYY-MM-DD HH:MM) or duration (e.g., 2h, 30m)"
            in result.stdout
        )

    def test_create_reservation_past_time(
        self, runner, mock_api_success, mock_auth_config
    ):
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

    def test_list_reservations_success(
        self, runner, mock_api_success, mock_auth_config
    ):
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

    def test_list_upcoming_reservations(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test listing only upcoming reservations"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["reservations", "list", "--upcoming"])

        assert result.exit_code == 0
        assert "Your Reservations" in result.stdout

    def test_cancel_reservation_success(
        self, runner, mock_api_success, mock_auth_config
    ):
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

    def test_cancel_reservation_abort(
        self, runner, mock_api_success, mock_auth_config, mock_inputs
    ):
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

    def test_show_reservation_history_detailed(
        self, runner, mock_api_success, mock_auth_config
    ):
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

    def test_upcoming_command_shortcut(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test upcoming reservations shortcut command"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["upcoming"])

        assert result.exit_code == 0
        assert "Upcoming Reservations" in result.stdout
        mock_api_success.get_my_reservations.assert_called_once()

    def test_list_reservations_with_pagination(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test listing reservations with pagination options"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "list",
                    "--limit",
                    "10",
                    "--sort",
                    "created_at",
                    "--order",
                    "asc",
                ],
            )

        assert result.exit_code == 0
        mock_api_success.get_my_reservations.assert_called_once()
        call_kwargs = mock_api_success.get_my_reservations.call_args
        assert call_kwargs[1].get("limit") == 10
        assert call_kwargs[1].get("sort_by") == "created_at"
        assert call_kwargs[1].get("sort_order") == "asc"

    def test_list_reservations_with_cursor(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test listing reservations with pagination cursor"""
        mock_api_success.get_my_reservations.return_value = {
            "data": [],
            "next_cursor": None,
            "has_more": False,
        }
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app, ["reservations", "list", "--cursor", "cursor_abc"]
            )

        assert result.exit_code == 0
        call_kwargs = mock_api_success.get_my_reservations.call_args
        assert call_kwargs[1].get("cursor") == "cursor_abc"

    def test_create_recurring_reservation_weekly(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test creating a weekly recurring reservation"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "create",
                    "1",
                    "2025-06-08 14:00",
                    "2h",
                    "--recurrence",
                    "weekly",
                    "--days",
                    "1,3,5",
                    "--recurrence-count",
                    "5",
                ],
            )

        assert result.exit_code == 0
        assert "recurring reservations" in result.stdout
        mock_api_success.create_recurring_reservation.assert_called_once()
        call_kwargs = mock_api_success.create_recurring_reservation.call_args
        assert call_kwargs[1].get("frequency") == "weekly"
        assert call_kwargs[1].get("days_of_week") == [1, 3, 5]

    def test_create_recurring_reservation_daily(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test creating a daily recurring reservation"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "create",
                    "1",
                    "2025-06-08 14:00",
                    "1h",
                    "--recurrence",
                    "daily",
                    "--recurrence-count",
                    "3",
                ],
            )

        assert result.exit_code == 0
        assert "recurring reservations" in result.stdout
        mock_api_success.create_recurring_reservation.assert_called_once()

    def test_create_recurring_reservation_with_end_date(
        self, runner, mock_api_success, mock_auth_config
    ):
        """Test creating a recurring reservation with end date"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "create",
                    "1",
                    "2025-06-08 14:00",
                    "2h",
                    "--recurrence",
                    "weekly",
                    "--recurrence-end",
                    "2025-07-08",
                ],
            )

        assert result.exit_code == 0
        mock_api_success.create_recurring_reservation.assert_called_once()
        call_kwargs = mock_api_success.create_recurring_reservation.call_args
        assert call_kwargs[1].get("end_type") == "on_date"

    def test_create_recurring_reservation_invalid_frequency(
        self, runner, mock_auth_config
    ):
        """Test creating recurring reservation with invalid frequency"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "create",
                    "1",
                    "2025-06-08 14:00",
                    "1h",
                    "--recurrence",
                    "biweekly",
                ],
            )

        assert result.exit_code == 1
        assert "Recurrence must be: daily, weekly, or monthly" in result.stdout

    def test_create_recurring_reservation_invalid_days(self, runner, mock_auth_config):
        """Test creating weekly recurring reservation with invalid days"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "reservations",
                    "create",
                    "1",
                    "2025-06-08 14:00",
                    "1h",
                    "--recurrence",
                    "weekly",
                    "--days",
                    "7,8",
                ],
            )

        assert result.exit_code == 1
        assert "Days must be" in result.stdout
