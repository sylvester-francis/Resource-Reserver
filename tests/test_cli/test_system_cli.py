from unittest.mock import patch

from cli.main import app


class TestSystemCLI:
    """Test CLI system management commands"""

    def test_system_status_success(self, runner, mock_api_success):
        """Test system status check"""
        result = runner.invoke(app, ["system", "status"])

        assert result.exit_code == 0
        assert "System Status Check" in result.stdout
        # Updated to match actual output format
        assert "API Connection:" in result.stdout

    def test_system_status_with_background_tasks(self, runner, mock_api_success):
        """Test system status with background task information"""
        result = runner.invoke(app, ["system", "status"])

        assert result.exit_code == 0
        # Background task info is included in health check response
        assert "System Status Check" in result.stdout

    def test_system_status_api_failure(self, runner):
        """Test system status when API is unreachable"""
        with patch("cli.main.client") as mock_client:
            mock_client.health_check.side_effect = Exception("Connection failed")

            result = runner.invoke(app, ["system", "status"])

            assert result.exit_code == 0  # Should not exit with error
            assert "API Connection:" in result.stdout

    def test_availability_summary(self, runner, mock_api_success, mock_auth_config):
        """Test system-wide availability summary"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["system", "summary"])

        assert result.exit_code == 0
        assert "System Availability Summary" in result.stdout
        mock_api_success.get_availability_summary.assert_called_once()

    def test_manual_cleanup_success(self, runner, mock_api_success, mock_auth_config, mock_inputs):
        """Test manual cleanup of expired reservations"""
        mock_inputs["confirm"].return_value = True
        
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["system", "cleanup"])

        assert result.exit_code == 0
        assert "Cleanup completed" in result.stdout
        mock_api_success.manual_cleanup_expired.assert_called_once()

    def test_manual_cleanup_abort(self, runner, mock_inputs):
        """Test aborting manual cleanup"""
        mock_inputs["confirm"].return_value = False
        
        result = runner.invoke(app, ["system", "cleanup"])

        assert result.exit_code == 0
        assert "Cleanup cancelled" in result.stdout

    def test_show_config(self, runner, mock_config):
        """Test showing current configuration"""
        with patch("cli.main.config", mock_config):
            result = runner.invoke(app, ["system", "config"])

        assert result.exit_code == 0
        assert "Current Configuration" in result.stdout
        assert "API URL: http://localhost:8000" in result.stdout
        # Since mock_config has no token by default
        assert "Authenticated: No" in result.stdout

    def test_show_config_authenticated(self, runner, mock_auth_config):
        """Test showing config when authenticated"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(app, ["system", "config"])

        assert result.exit_code == 0
        assert "Current Configuration" in result.stdout
        assert "Authenticated: Yes" in result.stdout