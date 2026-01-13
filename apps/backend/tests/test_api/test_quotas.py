"""API tests for rate limits and quotas endpoints."""

from fastapi import status

# API v1 prefix
API_V1 = "/api/v1/quotas"


class TestRateLimitConfig:
    """Test rate limit configuration endpoints."""

    def test_get_rate_limit_config(self, client, auth_headers):
        """Test getting rate limit configuration."""
        response = client.get(
            f"{API_V1}/config",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tiers" in data
        assert "endpoint_limits" in data
        assert isinstance(data["tiers"], list)

    def test_get_rate_limit_config_unauthenticated_fails(self, client):
        """Test unauthenticated request fails."""
        response = client.get(f"{API_V1}/config")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMyUsage:
    """Test user's own quota usage endpoints."""

    def test_get_my_usage(self, client, auth_headers):
        """Test getting own quota usage."""
        response = client.get(
            f"{API_V1}/my-usage",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "user_id" in data
        assert "tier" in data
        assert "rate_limit_per_minute" in data
        assert "daily_used" in data

    def test_get_my_usage_unauthenticated_fails(self, client):
        """Test unauthenticated request fails."""
        response = client.get(f"{API_V1}/my-usage")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAdminQuotaManagement:
    """Test admin quota management endpoints."""

    def test_list_user_quotas_admin_success(self, client, admin_headers):
        """Test admin can list all user quotas."""
        response = client.get(
            f"{API_V1}/users",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)  # Returns list directly

    def test_list_user_quotas_with_pagination(self, client, admin_headers):
        """Test quota listing with pagination."""
        response = client.get(
            f"{API_V1}/users",
            params={"skip": 0, "limit": 10},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 10  # Returns list directly

    def test_list_user_quotas_filter_by_tier(self, client, admin_headers):
        """Test filtering quotas by tier."""
        response = client.get(
            f"{API_V1}/users",
            params={"tier": "standard"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_list_user_quotas_non_admin_fails(self, client, auth_headers):
        """Test non-admin cannot list user quotas."""
        response = client.get(
            f"{API_V1}/users",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_user_quota_admin_success(self, client, admin_headers, test_user):
        """Test admin can get specific user's quota."""
        response = client.get(
            f"{API_V1}/users/{test_user.id}",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == test_user.id

    def test_get_user_quota_not_found(self, client, admin_headers):
        """Test getting quota for non-existent user."""
        response = client.get(
            f"{API_V1}/users/99999",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_user_quota_success(self, client, admin_headers, test_user):
        """Test admin can update user quota."""
        response = client.patch(
            f"{API_V1}/users/{test_user.id}",
            json={
                "tier": "premium",
                "custom_rate_limit": 100,
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tier"] == "premium"
        assert data["custom_rate_limit"] == 100

    def test_update_user_quota_reset_count(self, client, admin_headers, test_user):
        """Test admin can reset user's daily count."""
        response = client.patch(
            f"{API_V1}/users/{test_user.id}",
            json={"reset_daily_count": True},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["daily_request_count"] == 0

    def test_update_user_quota_non_admin_fails(self, client, auth_headers, test_user):
        """Test non-admin cannot update quotas."""
        response = client.patch(
            f"{API_V1}/users/{test_user.id}",
            json={"tier": "premium"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUsageStats:
    """Test usage statistics endpoints."""

    def test_get_usage_stats_admin_success(self, client, admin_headers):
        """Test admin can get usage statistics."""
        response = client.get(
            f"{API_V1}/stats",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_requests_today" in data
        assert "total_requests_week" in data
        assert "unique_users_today" in data

    def test_get_usage_stats_non_admin_fails(self, client, auth_headers):
        """Test non-admin cannot get usage stats."""
        response = client.get(
            f"{API_V1}/stats",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestQuotaAlerts:
    """Test quota alert endpoints."""

    def test_get_quota_alerts_admin_success(self, client, admin_headers):
        """Test admin can get quota alerts."""
        response = client.get(
            f"{API_V1}/alerts",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_quota_alerts_with_threshold(self, client, admin_headers):
        """Test getting alerts with custom threshold."""
        response = client.get(
            f"{API_V1}/alerts",
            params={"threshold": 50},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_quota_alerts_non_admin_fails(self, client, auth_headers):
        """Test non-admin cannot get quota alerts."""
        response = client.get(
            f"{API_V1}/alerts",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
