from unittest.mock import patch

import requests

from cli.main import app


class TestAuthCLI:
    """Test CLI authentication commands"""

    def test_register_success(self, runner, mock_api_success, mock_inputs):
        """Test successful user registration via CLI"""
        # Setup mock inputs for registration
        mock_inputs["prompt"].return_value = "testuser"
        mock_inputs["getpass"].side_effect = ["password123", "password123"]

        result = runner.invoke(app, ["auth", "register"])

        assert result.exit_code == 0
        assert "Successfully registered" in result.stdout
        mock_api_success.register.assert_called_once_with("testuser", "password123")

    def test_register_password_mismatch(self, runner, mock_inputs):
        """Test registration with mismatched passwords"""
        # Setup mock inputs for password mismatch
        mock_inputs["prompt"].return_value = "testuser"
        mock_inputs["getpass"].side_effect = ["password123", "different"]

        result = runner.invoke(app, ["auth", "register"])

        assert result.exit_code == 1
        assert "Passwords do not match" in result.stdout

    def test_login_success(self, runner, mock_api_success, mock_config, mock_inputs):
        """Test successful login via CLI"""
        # Setup mock inputs for login
        mock_inputs["prompt"].return_value = "testuser"
        mock_inputs["getpass"].return_value = "password123"

        with patch("cli.config.config", mock_config):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 0
        assert "Welcome back" in result.stdout
        mock_api_success.login.assert_called_once_with("testuser", "password123")

    def test_login_invalid_credentials(self, runner, mock_inputs):
        """Test login with invalid credentials"""
        # Setup mock inputs for invalid login
        mock_inputs["prompt"].return_value = "testuser"
        mock_inputs["getpass"].return_value = "wrongpass"

        with patch("cli.main.client") as mock_client:
            mock_client.login.side_effect = requests.exceptions.HTTPError("Invalid credentials")
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 1
        assert "Invalid username or password" in result.stdout

    def test_logout(self, runner, mock_config):
        """Test logout functionality"""
        # First, simulate being logged in
        mock_config.save_token("fake_token")

        with patch("cli.main.config", mock_config):
            result = runner.invoke(app, ["auth", "logout"])

        assert result.exit_code == 0
        assert "Successfully logged out" in result.stdout
        assert mock_config.load_token() is None

    def test_status_logged_in(self, runner, mock_config, mock_api_success):
        """Test auth status when logged in"""
        mock_config.save_token("fake_token")

        with patch("cli.main.config", mock_config):
            result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "You are logged in" in result.stdout
        assert "Connection to API: OK" in result.stdout

    def test_status_not_logged_in(self, runner, mock_config):
        """Test auth status when not logged in"""
        # Ensure no token is saved
        mock_config.clear_token()

        with patch("cli.main.config", mock_config):
            result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "You are not logged in" in result.stdout
        assert "cli auth login" in result.stdout
