"""Tests for the bulk operations endpoints.

Author: Sylvester-Francis
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


class TestBulkCreate:
    """Tests for bulk create endpoint."""

    def test_bulk_create_requires_auth(self, client: TestClient):
        """Test that bulk create requires authentication."""
        response = client.post(
            "/api/v1/bulk/reservations",
            json={"reservations": []},
        )
        assert response.status_code == 401

    def test_bulk_create_requires_at_least_one(
        self, client: TestClient, auth_headers: dict
    ):
        """Test that bulk create requires at least one reservation."""
        response = client.post(
            "/api/v1/bulk/reservations",
            json={"reservations": []},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_bulk_create_max_limit(self, client: TestClient, auth_headers: dict):
        """Test that bulk create respects max limit."""
        start = datetime.now(UTC) + timedelta(hours=1)
        reservations = [
            {
                "resource_id": 1,
                "start_time": (start + timedelta(hours=i)).isoformat(),
                "end_time": (start + timedelta(hours=i, minutes=30)).isoformat(),
            }
            for i in range(101)  # One over the limit
        ]
        response = client.post(
            "/api/v1/bulk/reservations",
            json={"reservations": reservations},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_bulk_create_dry_run(
        self, client: TestClient, auth_headers: dict, admin_headers: dict, test_db
    ):
        """Test bulk create with dry run."""
        # Create a resource first (requires admin)
        resource_response = client.post(
            "/api/v1/resources/",
            json={"name": "bulk-test-resource"},
            headers=admin_headers,
        )
        assert resource_response.status_code in [200, 201]
        resource_id = resource_response.json()["id"]

        # Try dry run
        start = datetime.now(UTC) + timedelta(hours=1)
        response = client.post(
            "/api/v1/bulk/reservations",
            json={
                "reservations": [
                    {
                        "resource_id": resource_id,
                        "start_time": start.isoformat(),
                        "end_time": (start + timedelta(hours=1)).isoformat(),
                    }
                ],
                "dry_run": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True
        assert data["success"] == 1

    def test_bulk_create_success(
        self, client: TestClient, auth_headers: dict, admin_headers: dict, test_db
    ):
        """Test successful bulk create."""
        # Create a resource first (requires admin)
        resource_response = client.post(
            "/api/v1/resources/",
            json={"name": "bulk-create-resource"},
            headers=admin_headers,
        )
        assert resource_response.status_code in [200, 201]
        resource_id = resource_response.json()["id"]

        # Create multiple reservations
        start = datetime.now(UTC) + timedelta(hours=5)
        response = client.post(
            "/api/v1/bulk/reservations",
            json={
                "reservations": [
                    {
                        "resource_id": resource_id,
                        "start_time": start.isoformat(),
                        "end_time": (start + timedelta(hours=1)).isoformat(),
                    },
                    {
                        "resource_id": resource_id,
                        "start_time": (start + timedelta(hours=2)).isoformat(),
                        "end_time": (start + timedelta(hours=3)).isoformat(),
                    },
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == 2
        assert data["failed"] == 0


class TestBulkCancel:
    """Tests for bulk cancel endpoint."""

    def test_bulk_cancel_requires_auth(self, client: TestClient):
        """Test that bulk cancel requires authentication."""
        response = client.post(
            "/api/v1/bulk/reservations/cancel",
            json={"reservation_ids": [1]},
        )
        assert response.status_code == 401

    def test_bulk_cancel_empty_list(self, client: TestClient, auth_headers: dict):
        """Test that bulk cancel requires at least one ID."""
        response = client.post(
            "/api/v1/bulk/reservations/cancel",
            json={"reservation_ids": []},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_bulk_cancel_not_found(self, client: TestClient, auth_headers: dict):
        """Test bulk cancel with non-existent IDs."""
        response = client.post(
            "/api/v1/bulk/reservations/cancel",
            json={"reservation_ids": [99999, 99998]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["failed"] == 2
        assert data["success"] == 0


class TestCSVImport:
    """Tests for CSV import endpoint."""

    def test_import_requires_auth(self, client: TestClient):
        """Test that import requires authentication."""
        response = client.post(
            "/api/v1/bulk/reservations/import",
            files={"file": ("test.csv", "resource_id,start_time,end_time", "text/csv")},
        )
        assert response.status_code == 401

    def test_import_requires_csv_file(self, client: TestClient, auth_headers: dict):
        """Test that import requires a CSV file."""
        response = client.post(
            "/api/v1/bulk/reservations/import",
            files={"file": ("test.txt", "some content", "text/plain")},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]

    def test_import_dry_run(
        self, client: TestClient, auth_headers: dict, admin_headers: dict, test_db
    ):
        """Test CSV import with dry run."""
        # Create a resource first (requires admin)
        resource_response = client.post(
            "/api/v1/resources/",
            json={"name": "csv-test-resource"},
            headers=admin_headers,
        )
        assert resource_response.status_code in [200, 201]
        resource_id = resource_response.json()["id"]

        # Create CSV content
        start = datetime.now(UTC) + timedelta(hours=10)
        csv_content = f"""resource_id,start_time,end_time
{resource_id},{start.isoformat()},{(start + timedelta(hours=1)).isoformat()}"""

        response = client.post(
            "/api/v1/bulk/reservations/import?dry_run=true",
            files={"file": ("import.csv", csv_content, "text/csv")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True


class TestCSVExport:
    """Tests for CSV export endpoint."""

    def test_export_requires_auth(self, client: TestClient):
        """Test that export requires authentication."""
        response = client.get("/api/v1/bulk/reservations/export")
        assert response.status_code == 401

    def test_export_returns_csv(self, client: TestClient, auth_headers: dict):
        """Test that export returns CSV content."""
        response = client.get(
            "/api/v1/bulk/reservations/export",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")

    def test_export_with_filters(self, client: TestClient, auth_headers: dict):
        """Test export with filters."""
        response = client.get(
            "/api/v1/bulk/reservations/export?status=active",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestBulkValidate:
    """Tests for bulk validate endpoint."""

    def test_validate_requires_auth(self, client: TestClient):
        """Test that validate requires authentication."""
        response = client.post(
            "/api/v1/bulk/reservations/validate",
            json={"reservations": []},
        )
        assert response.status_code == 401

    def test_validate_returns_validity(
        self, client: TestClient, auth_headers: dict, admin_headers: dict, test_db
    ):
        """Test that validate returns validity status."""
        # Create a resource first (requires admin)
        resource_response = client.post(
            "/api/v1/resources/",
            json={"name": "validate-test-resource"},
            headers=admin_headers,
        )
        assert resource_response.status_code in [200, 201]
        resource_id = resource_response.json()["id"]

        start = datetime.now(UTC) + timedelta(hours=20)
        response = client.post(
            "/api/v1/bulk/reservations/validate",
            json={
                "reservations": [
                    {
                        "resource_id": resource_id,
                        "start_time": start.isoformat(),
                        "end_time": (start + timedelta(hours=1)).isoformat(),
                    }
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "would_create" in data
        assert "errors" in data


class TestBulkWorkflow:
    """Integration tests for bulk workflow."""

    def test_full_bulk_workflow(
        self, client: TestClient, auth_headers: dict, admin_headers: dict, test_db
    ):
        """Test complete bulk workflow."""
        # Create a resource (requires admin)
        resource_response = client.post(
            "/api/v1/resources/",
            json={"name": "bulk-workflow-resource"},
            headers=admin_headers,
        )
        assert resource_response.status_code in [200, 201]
        resource_id = resource_response.json()["id"]

        # Validate first
        start = datetime.now(UTC) + timedelta(hours=30)
        validate_response = client.post(
            "/api/v1/bulk/reservations/validate",
            json={
                "reservations": [
                    {
                        "resource_id": resource_id,
                        "start_time": start.isoformat(),
                        "end_time": (start + timedelta(hours=1)).isoformat(),
                    },
                    {
                        "resource_id": resource_id,
                        "start_time": (start + timedelta(hours=2)).isoformat(),
                        "end_time": (start + timedelta(hours=3)).isoformat(),
                    },
                ]
            },
            headers=auth_headers,
        )
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

        # Create reservations
        create_response = client.post(
            "/api/v1/bulk/reservations",
            json={
                "reservations": [
                    {
                        "resource_id": resource_id,
                        "start_time": start.isoformat(),
                        "end_time": (start + timedelta(hours=1)).isoformat(),
                    },
                    {
                        "resource_id": resource_id,
                        "start_time": (start + timedelta(hours=2)).isoformat(),
                        "end_time": (start + timedelta(hours=3)).isoformat(),
                    },
                ]
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["success"] == 2

        # Get reservation IDs
        reservation_ids = [c["reservation_id"] for c in created["created"]]

        # Cancel them
        cancel_response = client.post(
            "/api/v1/bulk/reservations/cancel",
            json={
                "reservation_ids": reservation_ids,
                "reason": "Bulk test cleanup",
            },
            headers=auth_headers,
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["success"] == 2
