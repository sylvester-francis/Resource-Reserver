"""Tests for rate limiting and quota functionality.

Author: Sylvester-Francis
"""

from datetime import UTC, datetime

import pytest


class TestRateLimiterModule:
    """Tests for rate limiter module utilities."""

    def test_user_tier_enum(self):
        """Test UserTier enum values."""
        from app.core.rate_limiter import UserTier

        assert UserTier.ANONYMOUS.value == "anonymous"
        assert UserTier.AUTHENTICATED.value == "authenticated"
        assert UserTier.PREMIUM.value == "premium"
        assert UserTier.ADMIN.value == "admin"

    def test_tier_limits_configured(self):
        """Test that all tiers have rate limits configured."""
        from app.core.rate_limiter import TIER_LIMITS, UserTier

        for tier in UserTier:
            assert tier in TIER_LIMITS
            assert TIER_LIMITS[tier] > 0

    def test_daily_quota_limits_configured(self):
        """Test that daily quotas are configured."""
        from app.core.rate_limiter import DAILY_QUOTA_LIMITS, UserTier

        for tier in UserTier:
            assert tier in DAILY_QUOTA_LIMITS
            # Admin has unlimited quota (None)
            if tier == UserTier.ADMIN:
                assert DAILY_QUOTA_LIMITS[tier] is None
            else:
                assert DAILY_QUOTA_LIMITS[tier] is None or DAILY_QUOTA_LIMITS[tier] > 0

    def test_endpoint_limits_configured(self):
        """Test that endpoint-specific limits are configured."""
        from app.core.rate_limiter import ENDPOINT_LIMITS

        assert "/api/v1/token" in ENDPOINT_LIMITS
        assert "/api/v1/register" in ENDPOINT_LIMITS
        assert ENDPOINT_LIMITS["/api/v1/token"] == 5

    def test_rate_limit_info_to_headers(self):
        """Test RateLimitInfo header generation."""
        from app.core.rate_limiter import RateLimitInfo

        reset_at = datetime.now(UTC)
        info = RateLimitInfo(limit=100, remaining=50, reset_at=reset_at)

        headers = info.to_headers()
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "50"
        assert "X-RateLimit-Reset" in headers
        assert "Retry-After" not in headers

    def test_rate_limit_info_with_retry_after(self):
        """Test RateLimitInfo with retry after."""
        from app.core.rate_limiter import RateLimitInfo

        reset_at = datetime.now(UTC)
        info = RateLimitInfo(limit=100, remaining=0, reset_at=reset_at, retry_after=30)

        headers = info.to_headers()
        assert headers["X-RateLimit-Remaining"] == "0"
        assert headers["Retry-After"] == "30"


class TestInMemoryRateLimiter:
    """Tests for in-memory rate limiter."""

    def test_check_rate_limit_initial(self):
        """Test initial rate limit check."""
        from app.core.rate_limiter import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        info = limiter.check_rate_limit("test_key", limit=10)

        assert info.limit == 10
        assert info.remaining == 10
        assert info.retry_after is None

    def test_record_request_decrements_remaining(self):
        """Test that recording requests decrements remaining."""
        from app.core.rate_limiter import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        key = "test_key_2"

        limiter.record_request(key)
        limiter.record_request(key)
        limiter.record_request(key)

        info = limiter.check_rate_limit(key, limit=10)
        assert info.remaining == 7

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded detection."""
        from app.core.rate_limiter import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        key = "test_key_3"

        # Exhaust the limit
        for _ in range(5):
            limiter.record_request(key)

        info = limiter.check_rate_limit(key, limit=5)
        assert info.remaining == 0
        assert info.retry_after is not None
        assert info.retry_after > 0

    def test_daily_count_tracking(self):
        """Test daily request count tracking."""
        from app.core.rate_limiter import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        user_id = "user_123"
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        assert limiter.get_daily_count(user_id, today) == 0

        limiter.increment_daily_count(user_id, today)
        limiter.increment_daily_count(user_id, today)

        assert limiter.get_daily_count(user_id, today) == 2

    def test_usage_stats(self):
        """Test usage statistics."""
        from app.core.rate_limiter import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        user_id = "user_456"
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        limiter.increment_daily_count(user_id, today)

        stats = limiter.get_usage_stats(user_id)
        assert "daily_count" in stats
        assert stats["daily_count"] == 1
        assert stats["date"] == today


class TestGetEndpointLimit:
    """Tests for endpoint-specific rate limits."""

    def test_get_specific_endpoint_limit(self):
        """Test getting limit for specific endpoint."""
        from app.core.rate_limiter import get_endpoint_limit

        assert get_endpoint_limit("/api/v1/token") == 5
        assert get_endpoint_limit("/api/v1/register") == 5

    def test_get_bulk_endpoint_limit(self):
        """Test getting limit for bulk endpoints."""
        from app.core.rate_limiter import get_endpoint_limit

        # Pattern matching
        limit = get_endpoint_limit("/api/v1/bulk/reservations")
        assert limit == 5

    def test_get_no_specific_limit(self):
        """Test endpoint with no specific limit returns None."""
        from app.core.rate_limiter import get_endpoint_limit

        assert get_endpoint_limit("/api/v1/resources") is None
        assert get_endpoint_limit("/api/v1/reservations/my") is None


class TestUsageSummary:
    """Tests for usage summary function."""

    def test_get_usage_summary_without_user(self):
        """Test getting usage summary without user ID."""
        from app.core.rate_limiter import get_usage_summary

        summary = get_usage_summary()

        assert "tier_limits" in summary
        assert "daily_quotas" in summary
        assert "endpoint_limits" in summary

    def test_get_usage_summary_with_user(self):
        """Test getting usage summary for a user."""
        from app.core.rate_limiter import get_usage_summary

        summary = get_usage_summary("test_user")

        assert "daily_count" in summary
        assert "date" in summary


class TestQuotaEndpoints:
    """Tests for quota API endpoints."""

    def test_get_rate_limit_config(self, client, auth_headers):
        """Test getting rate limit configuration."""
        response = client.get("/api/v1/quotas/config", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "tiers" in data
        assert "endpoint_limits" in data
        assert len(data["tiers"]) > 0

    def test_get_my_usage(self, client, auth_headers):
        """Test getting own usage stats."""
        response = client.get("/api/v1/quotas/my-usage", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "user_id" in data
        assert "tier" in data
        assert "rate_limit_per_minute" in data
        assert "daily_used" in data

    def test_get_rate_limit_summary(self, client, auth_headers):
        """Test getting rate limit summary."""
        response = client.get("/api/v1/quotas/summary", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "tier_limits" in data or "daily_count" in data

    def test_list_user_quotas_requires_admin(self, client, auth_headers):
        """Test that listing user quotas requires admin role."""
        response = client.get("/api/v1/quotas/users", headers=auth_headers)
        # Regular user should be denied
        assert response.status_code == 403

    def test_get_usage_stats_requires_admin(self, client, auth_headers):
        """Test that usage stats require admin role."""
        response = client.get("/api/v1/quotas/stats", headers=auth_headers)
        assert response.status_code == 403

    def test_get_quota_alerts_requires_admin(self, client, auth_headers):
        """Test that quota alerts require admin role."""
        response = client.get("/api/v1/quotas/alerts", headers=auth_headers)
        assert response.status_code == 403


class TestRateLimitHeaders:
    """Tests for rate limit headers in responses.

    Note: These tests are skipped when rate limiting is disabled (default in tests).
    The rate limiter module logic is tested in other tests.
    """

    @pytest.mark.skip(reason="Rate limiting disabled in tests")
    def test_response_includes_rate_limit_headers(self, client, auth_headers):
        """Test that responses include rate limit headers."""
        response = client.get("/api/v1/resources/", headers=auth_headers)

        # Rate limit headers should be present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.skip(reason="Rate limiting disabled in tests")
    def test_rate_limit_remaining_decrements(self, client, auth_headers):
        """Test that remaining limit decrements with requests."""
        # Make first request
        response1 = client.get("/api/v1/resources/", headers=auth_headers)
        remaining1 = int(response1.headers.get("X-RateLimit-Remaining", 0))

        # Make second request
        response2 = client.get("/api/v1/resources/", headers=auth_headers)
        remaining2 = int(response2.headers.get("X-RateLimit-Remaining", 0))

        # Second request should have fewer remaining
        assert remaining2 <= remaining1


class TestAPIQuotaModel:
    """Tests for APIQuota model."""

    def test_create_api_quota(self, test_db):
        """Test creating an API quota record."""
        from app import models

        db = test_db()

        # First create a user
        user = models.User(username="quota_test_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create quota
        quota = models.APIQuota(
            user_id=user.id,
            tier="authenticated",
        )
        db.add(quota)
        db.commit()
        db.refresh(quota)

        assert quota.id is not None
        assert quota.tier == "authenticated"
        assert quota.daily_request_count == 0
        assert quota.total_requests == 0

        db.close()

    def test_api_quota_custom_limits(self, test_db):
        """Test API quota with custom limits."""
        from app import models

        db = test_db()

        user = models.User(username="custom_quota_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        quota = models.APIQuota(
            user_id=user.id,
            tier="premium",
            custom_rate_limit=200,
            custom_daily_quota=10000,
        )
        db.add(quota)
        db.commit()
        db.refresh(quota)

        assert quota.custom_rate_limit == 200
        assert quota.custom_daily_quota == 10000

        db.close()


class TestAPIUsageLogModel:
    """Tests for APIUsageLog model."""

    def test_create_usage_log(self, test_db):
        """Test creating an API usage log entry."""
        from app import models

        db = test_db()

        log = models.APIUsageLog(
            endpoint="/api/v1/resources",
            method="GET",
            status_code=200,
            response_time_ms=50,
            rate_limit=100,
            rate_remaining=99,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.id is not None
        assert log.endpoint == "/api/v1/resources"
        assert log.status_code == 200
        assert log.response_time_ms == 50

        db.close()

    def test_usage_log_with_user(self, test_db):
        """Test usage log with user association."""
        from app import models

        db = test_db()

        user = models.User(username="usage_log_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        log = models.APIUsageLog(
            user_id=user.id,
            endpoint="/api/v1/reservations",
            method="POST",
            status_code=201,
            ip_address="192.168.1.1",
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.user_id == user.id
        assert log.ip_address == "192.168.1.1"

        db.close()
