"""CLI tests for resource commands."""

import os
import tempfile
from unittest.mock import patch

from cli.main import app


class TestResourcesCLI:
    """Test CLI resource management commands"""

    def test_list_resources_success(self, runner, mock_api_success):
        """Test listing resources via CLI"""
        # Update mock to return paginated response format
        mock_api_success.list_resources.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "Conference Room A",
                    "tags": ["meeting"],
                    "available": True,
                },
                {"id": 2, "name": "Lab Equipment", "tags": ["lab"], "available": True},
            ],
            "next_cursor": None,
            "has_more": False,
            "total_count": 2,
        }
        result = runner.invoke(app, ["resources", "list"])

        assert result.exit_code == 0
        assert "Conference Room A" in result.stdout
        mock_api_success.list_resources.assert_called_once()

    def test_list_resources_with_pagination_limit(self, runner, mock_api_success):
        """Test listing resources with custom limit"""
        mock_api_success.list_resources.return_value = {
            "data": [{"id": 1, "name": "Resource 1", "tags": [], "available": True}],
            "next_cursor": "cursor_123",
            "has_more": True,
            "total_count": 10,
        }
        result = runner.invoke(app, ["resources", "list", "--limit", "1"])

        assert result.exit_code == 0
        assert "Resource 1" in result.stdout
        # Check pagination info is shown
        assert "cursor_123" in result.stdout or "More results" in result.stdout
        mock_api_success.list_resources.assert_called_once()

    def test_list_resources_with_cursor(self, runner, mock_api_success):
        """Test listing resources with pagination cursor"""
        mock_api_success.list_resources.return_value = {
            "data": [{"id": 2, "name": "Resource 2", "tags": [], "available": True}],
            "next_cursor": None,
            "has_more": False,
            "total_count": 10,
        }
        result = runner.invoke(app, ["resources", "list", "--cursor", "cursor_123"])

        assert result.exit_code == 0
        assert "Resource 2" in result.stdout
        mock_api_success.list_resources.assert_called_once()
        # Verify cursor was passed
        call_kwargs = mock_api_success.list_resources.call_args
        assert call_kwargs[1].get("cursor") == "cursor_123"

    def test_list_resources_with_sort(self, runner, mock_api_success):
        """Test listing resources with custom sort"""
        mock_api_success.list_resources.return_value = {
            "data": [{"id": 1, "name": "A Resource", "tags": [], "available": True}],
            "next_cursor": None,
            "has_more": False,
        }
        result = runner.invoke(
            app, ["resources", "list", "--sort", "id", "--order", "desc"]
        )

        assert result.exit_code == 0
        mock_api_success.list_resources.assert_called_once()
        call_kwargs = mock_api_success.list_resources.call_args
        assert call_kwargs[1].get("sort_by") == "id"
        assert call_kwargs[1].get("sort_order") == "desc"

    def test_list_resources_fetch_all(self, runner, mock_api_success, mock_inputs):
        """Test fetching all resources with pagination"""
        mock_inputs["confirm"].return_value = True
        # First call returns page 1 with more
        # Second call returns page 2 without more
        mock_api_success.list_resources.side_effect = [
            {
                "data": [
                    {"id": 1, "name": "Resource 1", "tags": [], "available": True}
                ],
                "next_cursor": "cursor_1",
                "has_more": True,
            },
            {
                "data": [
                    {"id": 2, "name": "Resource 2", "tags": [], "available": True}
                ],
                "next_cursor": None,
                "has_more": False,
            },
        ]
        result = runner.invoke(app, ["resources", "list", "--all"])

        assert result.exit_code == 0
        assert mock_api_success.list_resources.call_count == 2

    def test_list_resources_with_details(self, runner, mock_api_success):
        """Test listing resources with details"""
        mock_api_success.list_resources.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "Conference Room A",
                    "tags": ["meeting"],
                    "available": True,
                },
            ],
            "next_cursor": None,
            "has_more": False,
        }
        result = runner.invoke(app, ["resources", "list", "--details"])

        assert result.exit_code == 0
        assert "Tags:" in result.stdout
        mock_api_success.list_resources.assert_called_once()

    def test_search_resources_by_query(self, runner, mock_api_success):
        """Test searching resources by query"""
        mock_api_success.search_resources.return_value = {
            "data": [
                {"id": 1, "name": "Conference Room A", "tags": [], "available": True}
            ],
            "next_cursor": None,
            "has_more": False,
        }
        result = runner.invoke(app, ["resources", "search", "--query", "conference"])

        assert result.exit_code == 0
        assert "Conference Room A" in result.stdout
        mock_api_success.search_resources.assert_called_once()

    def test_search_resources_with_time_filter(
        self, runner, mock_api_success, mock_auth_config, mock_inputs
    ):
        """Test searching resources with time filter"""
        mock_inputs["confirm"].return_value = False  # Don't make reservation
        mock_api_success.search_resources.return_value = {
            "data": [
                {"id": 1, "name": "Conference Room A", "tags": [], "available": True}
            ],
            "next_cursor": None,
            "has_more": False,
        }

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
