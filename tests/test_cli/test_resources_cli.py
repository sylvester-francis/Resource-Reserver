import os
import tempfile
from unittest.mock import patch

from cli.main import app


class TestResourcesCLI:
    """Test CLI resource management commands"""

    def test_list_resources_success(self, runner, mock_api_success):
        """Test listing resources via CLI"""
        result = runner.invoke(app, ["resources", "list"])

        assert result.exit_code == 0
        assert "Conference Room A" in result.stdout
        mock_api_success.list_resources.assert_called_once()

    def test_list_resources_with_details(self, runner, mock_api_success):
        """Test listing resources with details"""
        result = runner.invoke(app, ["resources", "list", "--details"])

        assert result.exit_code == 0
        assert "Tags:" in result.stdout
        mock_api_success.list_resources.assert_called_once()

    def test_search_resources_by_query(self, runner, mock_api_success):
        """Test searching resources by query"""
        result = runner.invoke(app, ["resources", "search", "--query", "conference"])

        assert result.exit_code == 0
        assert "Conference Room A" in result.stdout
        mock_api_success.search_resources.assert_called_once()

    def test_search_resources_with_time_filter(
        self, runner, mock_api_success, mock_auth_config, mock_inputs
    ):
        """Test searching resources with time filter"""
        mock_inputs["confirm"].return_value = False  # Don't make reservation

        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "resources",
                    "search",
                    "--from",
                    "2025-06-08 09:00",
                    "--until",
                    "2025-06-08 17:00",
                ],
            )

        assert result.exit_code == 0
        mock_api_success.search_resources.assert_called_once()

    def test_search_resources_invalid_time_range(self, runner):
        """Test search with invalid time range"""
        result = runner.invoke(
            app,
            [
                "resources",
                "search",
                "--from",
                "2025-06-08 17:00",
                "--until",
                "2025-06-08 09:00",  # End before start
            ],
        )

        assert result.exit_code == 1
        assert "End time must be after start time" in result.stdout

    def test_create_resource_success(self, runner, mock_api_success, mock_auth_config):
        """Test creating a resource via CLI"""
        with patch("cli.main.config", mock_auth_config):
            result = runner.invoke(
                app,
                [
                    "resources",
                    "create",
                    "Test Meeting Room",
                    "--tags",
                    "meeting,projector",
                    "--available",
                ],
            )

        assert result.exit_code == 0
        assert "Created resource" in result.stdout
        mock_api_success.create_resource.assert_called_once()

    def test_create_resource_not_authenticated(self, runner):
        """Test creating resource without authentication"""
        with patch(
            "cli.config.config.get_auth_headers",
            side_effect=ValueError("Not authenticated"),
        ):
            result = runner.invoke(app, ["resources", "create", "Test Room"])

        assert result.exit_code == 1
        assert "Please login first" in result.stdout

    def test_upload_csv_success(self, runner, mock_api_success, mock_auth_config):
        """Test CSV upload via CLI"""
        csv_content = """name,tags,available
Test Room 1,"meeting,small",true
Test Room 2,"conference,large",true"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            with patch("cli.main.config", mock_auth_config):
                result = runner.invoke(app, ["resources", "upload", csv_path])

            assert result.exit_code == 0
            assert "Upload completed" in result.stdout
            mock_api_success.upload_resources_csv.assert_called_once()
        finally:
            os.unlink(csv_path)

    def test_upload_csv_with_preview(
        self, runner, mock_api_success, mock_auth_config, mock_inputs
    ):
        """Test CSV upload with preview"""
        csv_content = """name,tags,available
Preview Room 1,"test,preview",true
Preview Room 2,"test,preview",false"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            mock_inputs["confirm"].return_value = True
            with patch("cli.main.config", mock_auth_config):
                result = runner.invoke(
                    app, ["resources", "upload", csv_path, "--preview"]
                )

            assert result.exit_code == 0
            assert "Preview of" in result.stdout
            mock_api_success.upload_resources_csv.assert_called_once()
        finally:
            os.unlink(csv_path)

    def test_upload_nonexistent_file(self, runner):
        """Test uploading non-existent file"""
        result = runner.invoke(app, ["resources", "upload", "/nonexistent/file.csv"])

        assert result.exit_code == 1
        assert "File not found:" in result.stdout

    def test_upload_non_csv_file(self, runner):
        """Test uploading non-CSV file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("not a csv file")
            txt_path = f.name

        try:
            result = runner.invoke(app, ["resources", "upload", txt_path])

            assert result.exit_code == 1
            assert "File must be a CSV file" in result.stdout
        finally:
            os.unlink(txt_path)
