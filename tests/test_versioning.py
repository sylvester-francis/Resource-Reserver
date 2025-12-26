"""Tests for API versioning functionality.

Author: Sylvester-Francis
"""

from fastapi.testclient import TestClient


class TestAPIVersioning:
    """Tests for API versioning."""

    def test_api_versions_endpoint(self, client: TestClient):
        """Test API versions info endpoint."""
        response = client.get("/api/versions")
        assert response.status_code == 200
        data = response.json()

        assert "current_version" in data
        assert "versions" in data
        assert "deprecated_endpoints" in data
        assert data["current_version"] == "v1"

    def test_v1_endpoints_have_version_header(
        self, client: TestClient, auth_headers: dict
    ):
        """Test that v1 endpoints include version header."""
        response = client.get("/api/v1/resources/", headers=auth_headers)
        assert response.status_code == 200
        assert response.headers.get("X-API-Version") == "v1"

    def test_deprecated_endpoint_has_deprecation_headers(self, client: TestClient):
        """Test that deprecated endpoints have deprecation headers."""
        # /token is marked as deprecated in favor of /api/v1/token
        response = client.post(
            "/token",
            data={"username": "nonexistent", "password": "wrong"},
        )
        # Even failed requests should have deprecation headers
        assert response.headers.get("Deprecation") == "true"
        assert "Sunset" in response.headers
        assert "X-Deprecation-Notice" in response.headers


class TestVersioningModule:
    """Tests for versioning module utilities."""

    def test_api_version_from_string(self):
        """Test parsing version strings."""
        from app.core.versioning import APIVersion

        assert APIVersion.from_string("v1") == APIVersion.V1
        assert APIVersion.from_string("V1") == APIVersion.V1
        assert APIVersion.from_string("1") == APIVersion.V1
        assert APIVersion.from_string("v2") == APIVersion.V2

    def test_api_version_numeric(self):
        """Test numeric version property."""
        from app.core.versioning import APIVersion

        assert APIVersion.V1.numeric == 1
        assert APIVersion.V2.numeric == 2

    def test_get_api_version_from_path(self):
        """Test extracting version from path."""
        from app.core.versioning import APIVersion, get_api_version_from_path

        assert get_api_version_from_path("/api/v1/resources") == APIVersion.V1
        assert get_api_version_from_path("/api/v2/resources") == APIVersion.V2
        assert get_api_version_from_path("/health") is None
        assert get_api_version_from_path("/token") is None

    def test_check_endpoint_deprecation(self):
        """Test checking endpoint deprecation."""
        from app.core.versioning import check_endpoint_deprecation

        # Deprecated endpoint
        info = check_endpoint_deprecation("GET", "/token")
        assert info is not None
        assert "alternative" in info
        assert info["alternative"] == "/api/v1/token"

        # Non-deprecated endpoint
        info = check_endpoint_deprecation("GET", "/api/v1/resources/")
        assert info is None

    def test_get_version_info(self):
        """Test getting version info."""
        from app.core.versioning import get_version_info

        info = get_version_info()

        assert info["current_version"] == "v1"
        assert "v1" in info["versions"]
        assert "v2" in info["versions"]
        assert info["versions"]["v1"]["status"] == "current"
        assert info["versions"]["v2"]["status"] == "preview"
