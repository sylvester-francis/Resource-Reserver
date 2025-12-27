"""Tests for the search endpoints.

Author: Sylvester-Francis
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


class TestResourceSearch:
    """Tests for resource search endpoints."""

    def test_search_requires_auth(self, client: TestClient):
        """Test that search endpoint requires authentication."""
        response = client.get("/api/v1/search/resources")
        assert response.status_code == 401

    def test_search_returns_results(self, client: TestClient, auth_headers: dict):
        """Test that search returns results."""
        response = client.get("/api/v1/search/resources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "has_more" in data

    def test_search_with_query(self, client: TestClient, auth_headers: dict):
        """Test search with text query."""
        response = client.get(
            "/api/v1/search/resources?query=test", headers=auth_headers
        )
        assert response.status_code == 200

    def test_search_with_tags(self, client: TestClient, auth_headers: dict):
        """Test search with tag filter."""
        response = client.get(
            "/api/v1/search/resources?tags=tag1,tag2", headers=auth_headers
        )
        assert response.status_code == 200

    def test_search_with_status(self, client: TestClient, auth_headers: dict):
        """Test search with status filter."""
        response = client.get(
            "/api/v1/search/resources?status=available", headers=auth_headers
        )
        assert response.status_code == 200

    def test_search_available_only(self, client: TestClient, auth_headers: dict):
        """Test search with available_only filter."""
        response = client.get(
            "/api/v1/search/resources?available_only=true", headers=auth_headers
        )
        assert response.status_code == 200

    def test_search_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test search with pagination parameters."""
        response = client.get(
            "/api/v1/search/resources?limit=10&offset=0", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0


class TestReservationSearch:
    """Tests for reservation search endpoints."""

    def test_search_requires_auth(self, client: TestClient):
        """Test that reservation search requires authentication."""
        response = client.get("/api/v1/search/reservations")
        assert response.status_code == 401

    def test_search_returns_results(self, client: TestClient, auth_headers: dict):
        """Test that reservation search returns results."""
        response = client.get("/api/v1/search/reservations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data

    def test_search_with_status(self, client: TestClient, auth_headers: dict):
        """Test reservation search with status filter."""
        response = client.get(
            "/api/v1/search/reservations?status=active", headers=auth_headers
        )
        assert response.status_code == 200

    def test_search_with_date_range(self, client: TestClient, auth_headers: dict):
        """Test reservation search with date range."""
        from urllib.parse import quote

        start = datetime.now(UTC).isoformat()
        end = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        response = client.get(
            f"/api/v1/search/reservations?start_from={quote(start)}&start_until={quote(end)}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_search_include_cancelled(self, client: TestClient, auth_headers: dict):
        """Test reservation search including cancelled."""
        response = client.get(
            "/api/v1/search/reservations?include_cancelled=true", headers=auth_headers
        )
        assert response.status_code == 200


class TestSearchSuggestions:
    """Tests for search suggestions endpoint."""

    def test_suggestions_requires_auth(self, client: TestClient):
        """Test that suggestions endpoint requires authentication."""
        response = client.get("/api/v1/search/suggestions?query=test")
        assert response.status_code == 401

    def test_suggestions_requires_query(self, client: TestClient, auth_headers: dict):
        """Test that suggestions requires a query."""
        response = client.get("/api/v1/search/suggestions", headers=auth_headers)
        assert response.status_code == 422

    def test_suggestions_returns_data(self, client: TestClient, auth_headers: dict):
        """Test suggestions returns resources and tags."""
        response = client.get(
            "/api/v1/search/suggestions?query=test", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "resources" in data
        assert "tags" in data


class TestPopularTags:
    """Tests for popular tags endpoint."""

    def test_popular_tags_requires_auth(self, client: TestClient):
        """Test that popular tags requires authentication."""
        response = client.get("/api/v1/search/tags/popular")
        assert response.status_code == 401

    def test_popular_tags_returns_data(self, client: TestClient, auth_headers: dict):
        """Test popular tags returns data."""
        response = client.get("/api/v1/search/tags/popular", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data


class TestResourceAvailability:
    """Tests for resource availability endpoint."""

    def test_availability_requires_auth(self, client: TestClient):
        """Test that availability requires authentication."""
        response = client.get("/api/v1/search/resources/1/availability")
        assert response.status_code == 401

    def test_availability_not_found(self, client: TestClient, auth_headers: dict):
        """Test availability for non-existent resource."""
        response = client.get(
            "/api/v1/search/resources/99999/availability", headers=auth_headers
        )
        assert response.status_code == 404


class TestSavedSearches:
    """Tests for saved searches endpoints."""

    def test_list_saved_requires_auth(self, client: TestClient):
        """Test that listing saved searches requires auth."""
        response = client.get("/api/v1/search/saved")
        assert response.status_code == 401

    def test_list_saved_returns_data(self, client: TestClient, auth_headers: dict):
        """Test listing saved searches."""
        response = client.get("/api/v1/search/saved", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "saved_searches" in data
        assert "count" in data

    def test_create_saved_search(self, client: TestClient, auth_headers: dict):
        """Test creating a saved search."""
        response = client.post(
            "/api/v1/search/saved",
            json={
                "name": "My Test Search",
                "search_type": "resources",
                "filters": {"query": "test", "available_only": True},
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["name"] == "My Test Search"

    def test_create_saved_search_invalid_type(
        self, client: TestClient, auth_headers: dict
    ):
        """Test creating saved search with invalid type."""
        response = client.post(
            "/api/v1/search/saved",
            json={
                "name": "Invalid Search",
                "search_type": "invalid",
                "filters": {},
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_delete_saved_not_found(self, client: TestClient, auth_headers: dict):
        """Test deleting non-existent saved search."""
        response = client.delete("/api/v1/search/saved/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_execute_saved_not_found(self, client: TestClient, auth_headers: dict):
        """Test executing non-existent saved search."""
        response = client.post(
            "/api/v1/search/saved/99999/execute", headers=auth_headers
        )
        assert response.status_code == 404


class TestSavedSearchWorkflow:
    """Integration tests for saved search workflow."""

    def test_full_saved_search_workflow(
        self, client: TestClient, auth_headers: dict, test_db
    ):
        """Test complete saved search workflow."""
        # Create a saved search
        create_response = client.post(
            "/api/v1/search/saved",
            json={
                "name": "Workflow Test Search",
                "search_type": "resources",
                "filters": {"query": "meeting", "available_only": True},
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        search_id = create_response.json()["id"]

        # List saved searches
        list_response = client.get("/api/v1/search/saved", headers=auth_headers)
        assert list_response.status_code == 200
        assert list_response.json()["count"] >= 1

        # Execute saved search
        execute_response = client.post(
            f"/api/v1/search/saved/{search_id}/execute", headers=auth_headers
        )
        assert execute_response.status_code == 200
        assert execute_response.json()["saved_search_name"] == "Workflow Test Search"

        # Delete saved search
        delete_response = client.delete(
            f"/api/v1/search/saved/{search_id}", headers=auth_headers
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True
