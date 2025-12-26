"""Enhanced rate limiting with per-user quotas and role-based limits.

Provides:
- Per-user rate limits based on role
- API usage tracking and quotas
- Rate limit headers in responses
- Configurable limits per endpoint

Author: Sylvester-Francis
"""

import logging
import time
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import Request, Response
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)


class UserTier(str, Enum):
    """User tier for rate limiting."""

    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated"
    PREMIUM = "premium"
    ADMIN = "admin"


# Rate limit configurations per tier (requests per minute)
TIER_LIMITS = {
    UserTier.ANONYMOUS: 20,
    UserTier.AUTHENTICATED: 100,
    UserTier.PREMIUM: 500,
    UserTier.ADMIN: 1000,
}

# Endpoint-specific rate limits (path pattern: requests per minute)
ENDPOINT_LIMITS = {
    "/api/v1/token": 5,
    "/api/v1/register": 5,
    "/api/v1/resources/upload": 10,
    "/api/v1/bulk/": 5,
    "/api/v1/analytics/export/": 10,
    "/api/v1/audit/export/": 10,
}

# Daily quota limits per tier
DAILY_QUOTA_LIMITS = {
    UserTier.ANONYMOUS: 500,
    UserTier.AUTHENTICATED: 5000,
    UserTier.PREMIUM: 50000,
    UserTier.ADMIN: None,  # Unlimited
}


class RateLimitInfo:
    """Container for rate limit information."""

    def __init__(
        self,
        limit: int,
        remaining: int,
        reset_at: datetime,
        retry_after: int | None = None,
    ):
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
        self.retry_after = retry_after

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at.timestamp())),
        }
        if self.retry_after is not None:
            headers["Retry-After"] = str(self.retry_after)
        return headers


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for tracking request counts.

    For production, this should be replaced with Redis-based storage.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = {}
        self._daily_counts: dict[str, dict[str, int]] = {}

    def _cleanup_old_requests(self, key: str, window_seconds: int = 60):
        """Remove requests older than the window."""
        if key not in self._requests:
            return
        cutoff = time.time() - window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check_rate_limit(
        self, key: str, limit: int, window_seconds: int = 60
    ) -> RateLimitInfo:
        """Check if a request is within rate limits."""
        self._cleanup_old_requests(key, window_seconds)

        if key not in self._requests:
            self._requests[key] = []

        current_count = len(self._requests[key])
        remaining = limit - current_count

        # Calculate reset time
        if self._requests[key]:
            oldest_request = min(self._requests[key])
            reset_at = datetime.fromtimestamp(oldest_request + window_seconds, tz=UTC)
        else:
            reset_at = datetime.now(UTC) + timedelta(seconds=window_seconds)

        retry_after = None
        if remaining <= 0:
            retry_after = int(reset_at.timestamp() - time.time())
            if retry_after < 0:
                retry_after = 1

        return RateLimitInfo(
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after,
        )

    def record_request(self, key: str):
        """Record a request for rate limiting."""
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key].append(time.time())

    def get_daily_count(self, user_id: str, date: str) -> int:
        """Get daily request count for a user."""
        if user_id not in self._daily_counts:
            return 0
        return self._daily_counts.get(user_id, {}).get(date, 0)

    def increment_daily_count(self, user_id: str, date: str):
        """Increment daily request count."""
        if user_id not in self._daily_counts:
            self._daily_counts[user_id] = {}
        if date not in self._daily_counts[user_id]:
            self._daily_counts[user_id][date] = 0
        self._daily_counts[user_id][date] += 1

    def get_usage_stats(self, user_id: str) -> dict[str, Any]:
        """Get usage statistics for a user."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return {
            "daily_count": self.get_daily_count(user_id, today),
            "date": today,
        }


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def reset_rate_limiter():
    """Reset the rate limiter state. Useful for testing."""
    global rate_limiter
    rate_limiter = InMemoryRateLimiter()


def get_user_tier(request: Request) -> UserTier:
    """Determine user tier from request."""
    # Check for user in request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user is None:
        return UserTier.ANONYMOUS

    # Check for admin role
    if hasattr(user, "is_admin") and user.is_admin:
        return UserTier.ADMIN

    # Check for premium flag (if exists)
    if hasattr(user, "is_premium") and user.is_premium:
        return UserTier.PREMIUM

    return UserTier.AUTHENTICATED


def get_rate_limit_key(request: Request) -> str:
    """Generate rate limit key based on user or IP."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        return f"user:{hash(token)}"
    return f"ip:{get_remote_address(request)}"


def get_endpoint_limit(path: str) -> int | None:
    """Get specific rate limit for an endpoint."""
    for pattern, limit in ENDPOINT_LIMITS.items():
        if path.startswith(pattern):
            return limit
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for enhanced rate limiting with headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/live", "/metrics"]:
            return await call_next(request)

        key = get_rate_limit_key(request)
        tier = get_user_tier(request)

        # Determine rate limit
        endpoint_limit = get_endpoint_limit(request.url.path)
        tier_limit = TIER_LIMITS.get(tier, TIER_LIMITS[UserTier.ANONYMOUS])
        limit = endpoint_limit if endpoint_limit else tier_limit

        # Check rate limit
        rate_info = rate_limiter.check_rate_limit(key, limit)

        if rate_info.remaining <= 0:
            logger.warning(f"Rate limit exceeded for {key} on {request.url.path}")
            response = Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
            )
            for header, value in rate_info.to_headers().items():
                response.headers[header] = value
            return response

        # Record the request
        rate_limiter.record_request(key)

        # Track daily quota
        if tier != UserTier.ANONYMOUS:
            user_id = key.replace("user:", "")
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            daily_limit = DAILY_QUOTA_LIMITS.get(tier)

            if daily_limit is not None:
                daily_count = rate_limiter.get_daily_count(user_id, today)
                if daily_count >= daily_limit:
                    logger.warning(f"Daily quota exceeded for {key}")
                    response = Response(
                        content='{"detail": "Daily API quota exceeded. Resets at midnight UTC."}',
                        status_code=429,
                        media_type="application/json",
                    )
                    response.headers["X-Quota-Limit"] = str(daily_limit)
                    response.headers["X-Quota-Remaining"] = "0"
                    return response

            rate_limiter.increment_daily_count(user_id, today)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        rate_info = rate_limiter.check_rate_limit(key, limit)
        for header, value in rate_info.to_headers().items():
            response.headers[header] = value

        # Add quota headers for authenticated users
        if tier != UserTier.ANONYMOUS:
            daily_limit = DAILY_QUOTA_LIMITS.get(tier)
            if daily_limit is not None:
                user_id = key.replace("user:", "")
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                daily_count = rate_limiter.get_daily_count(user_id, today)
                response.headers["X-Quota-Limit"] = str(daily_limit)
                response.headers["X-Quota-Remaining"] = str(
                    max(0, daily_limit - daily_count)
                )

        return response


def check_rate_limit(key: str, limit: int) -> RateLimitInfo:
    """Check rate limit for a key."""
    return rate_limiter.check_rate_limit(key, limit)


def get_usage_summary(user_id: str | None = None) -> dict[str, Any]:
    """Get rate limit usage summary."""
    if user_id:
        return rate_limiter.get_usage_stats(user_id)
    return {
        "tier_limits": {tier.value: limit for tier, limit in TIER_LIMITS.items()},
        "daily_quotas": {
            tier.value: limit for tier, limit in DAILY_QUOTA_LIMITS.items()
        },
        "endpoint_limits": ENDPOINT_LIMITS,
    }
