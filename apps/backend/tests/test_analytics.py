"""Tests for the analytics endpoints.

Author: Sylvester-Francis
"""

from fastapi.testclient import TestClient


class TestAnalyticsEndpoints:
    """Tests for analytics API endpoints."""

    def test_dashboard_requires_auth(self, client: TestClient):
        """Test that dashboard endpoint requires authentication."""
        response = client.get("/api/v1/analytics/dashboard")
        assert response.status_code == 401

    def test_dashboard_returns_summary(self, client: TestClient, auth_headers: dict):
        """Test dashboard endpoint returns summary data."""
        response = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "overview" in data
        assert "top_resources" in data

    def test_dashboard_with_days_param(self, client: TestClient, auth_headers: dict):
        """Test dashboard endpoint with days parameter."""
        response = client.get(
            "/api/v1/analytics/dashboard?days=7", headers=auth_headers
        )
        assert response.status_code == 200

    def test_utilization_endpoint(self, client: TestClient, auth_headers: dict):
        """Test utilization endpoint."""
        response = client.get("/api/v1/analytics/utilization", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "utilization" in data

    def test_utilization_with_days_param(self, client: TestClient, auth_headers: dict):
        """Test utilization endpoint with days parameter."""
        response = client.get(
            "/api/v1/analytics/utilization?days=7", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"]["days"] == 7

    def test_utilization_with_resource_id(self, client: TestClient, auth_headers: dict):
        """Test utilization endpoint with resource_id filter."""
        response = client.get(
            "/api/v1/analytics/utilization?resource_id=1", headers=auth_headers
        )
        assert response.status_code == 200

    def test_popular_resources_endpoint(self, client: TestClient, auth_headers: dict):
        """Test popular resources endpoint."""
        response = client.get(
            "/api/v1/analytics/popular-resources", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "resources" in data

    def test_popular_resources_with_limit(self, client: TestClient, auth_headers: dict):
        """Test popular resources with limit parameter."""
        response = client.get(
            "/api/v1/analytics/popular-resources?limit=5", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["resources"]) <= 5

    def test_peak_times_endpoint(self, client: TestClient, auth_headers: dict):
        """Test peak times endpoint."""
        response = client.get("/api/v1/analytics/peak-times", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "hourly_distribution" in data
        assert "daily_distribution" in data
        assert "peak_hour" in data
        assert "peak_day" in data
        assert len(data["hourly_distribution"]) == 24
        assert len(data["daily_distribution"]) == 7

    def test_peak_times_with_days(self, client: TestClient, auth_headers: dict):
        """Test peak times with days parameter."""
        response = client.get(
            "/api/v1/analytics/peak-times?days=14", headers=auth_headers
        )
        assert response.status_code == 200

    def test_user_patterns_endpoint(self, client: TestClient, auth_headers: dict):
        """Test user patterns endpoint."""
        response = client.get("/api/v1/analytics/user-patterns", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "users" in data

    def test_user_patterns_with_limit(self, client: TestClient, auth_headers: dict):
        """Test user patterns with limit parameter."""
        response = client.get(
            "/api/v1/analytics/user-patterns?limit=10", headers=auth_headers
        )
        assert response.status_code == 200

    def test_export_utilization_csv(self, client: TestClient, auth_headers: dict):
        """Test utilization CSV export."""
        response = client.get(
            "/api/v1/analytics/export/utilization.csv", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")
        # Check CSV content
        content = response.text
        assert "resource_id" in content
        assert "resource_name" in content

    def test_export_reservations_csv(self, client: TestClient, auth_headers: dict):
        """Test reservations CSV export."""
        response = client.get(
            "/api/v1/analytics/export/reservations.csv", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")
        # Check CSV content
        content = response.text
        assert "reservation_id" in content
        assert "resource_name" in content

    def test_export_utilization_csv_requires_auth(self, client: TestClient):
        """Test that utilization export requires authentication."""
        response = client.get("/api/v1/analytics/export/utilization.csv")
        assert response.status_code == 401

    def test_export_reservations_csv_requires_auth(self, client: TestClient):
        """Test that reservations export requires authentication."""
        response = client.get("/api/v1/analytics/export/reservations.csv")
        assert response.status_code == 401
