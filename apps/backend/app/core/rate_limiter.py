"""Enhanced rate limiting with per-user quotas and role-based limits.

This module provides a comprehensive rate limiting solution for the Resource
Reservation System API. It includes per-user rate limits based on user roles,
API usage tracking with daily quotas, rate limit headers in HTTP responses,
and configurable limits for specific endpoints.

Features:
    - Per-user rate limits based on role (anonymous, authenticated, premium, admin)
    - API usage tracking and daily quotas
    - Rate limit headers in HTTP responses (X-RateLimit-*)
    - Configurable limits per endpoint pattern
    - Testing mode with higher limits for E2E testing

Example:
    The rate limiter is automatically applied via middleware::

        from app.core.rate_limiter import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)

Author:
    Sylvester-Francis
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
    """Enumeration of user tiers for rate limiting.

    Each tier has different rate limits and daily quotas. Higher tiers
    receive more generous limits.

    Attributes:
        ANONYMOUS: Unauthenticated users (most restrictive).
        AUTHENTICATED: Regular authenticated users.
        PREMIUM: Premium/paid tier users.
        ADMIN: Administrative users (most permissive).
    """

    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated"
    PREMIUM = "premium"
    ADMIN = "admin"


# Rate limit configurations per tier (requests per minute)
TIER_LIMITS: dict[UserTier, int] = {
    UserTier.ANONYMOUS: 60,
    UserTier.AUTHENTICATED: 200,
    UserTier.PREMIUM: 500,
    UserTier.ADMIN: 1000,
}

# Higher limits for E2E/integration testing
TIER_LIMITS_TESTING: dict[UserTier, int] = {
    UserTier.ANONYMOUS: 1000,
    UserTier.AUTHENTICATED: 2000,
    UserTier.PREMIUM: 5000,
    UserTier.ADMIN: 10000,
}

# Endpoint-specific rate limits (path pattern: requests per minute)
ENDPOINT_LIMITS: dict[str, int] = {
    "/api/v1/token": 30,
    "/api/v1/register": 20,
    "/api/v1/resources/upload": 20,
    "/api/v1/bulk/": 10,
    "/api/v1/analytics/export/": 20,
    "/api/v1/audit/export/": 20,
}

# Higher endpoint limits for testing
ENDPOINT_LIMITS_TESTING: dict[str, int] = {
    "/api/v1/token": 500,
    "/api/v1/register": 500,
    "/api/v1/resources/upload": 200,
    "/api/v1/bulk/": 100,
    "/api/v1/analytics/export/": 200,
    "/api/v1/audit/export/": 200,
}

# Daily quota limits per tier
DAILY_QUOTA_LIMITS: dict[UserTier, int | None] = {
    UserTier.ANONYMOUS: 500,
    UserTier.AUTHENTICATED: 5000,
    UserTier.PREMIUM: 50000,
    UserTier.ADMIN: None,  # Unlimited
}


class RateLimitInfo:
    """Container for rate limit information.

    This class holds the current rate limit state for a request, including
    the configured limit, remaining requests, reset time, and optional
    retry-after duration for rate-limited responses.

    Attributes:
        limit: Maximum number of requests allowed in the window.
        remaining: Number of requests remaining in the current window.
        reset_at: UTC datetime when the rate limit window resets.
        retry_after: Seconds until the client should retry (if rate limited).

    Example:
        >>> info = RateLimitInfo(limit=100, remaining=50, reset_at=datetime.now(UTC))
        >>> headers = info.to_headers()
        >>> print(headers["X-RateLimit-Remaining"])
        '50'
    """

    def __init__(
        self,
        limit: int,
        remaining: int,
        reset_at: datetime,
        retry_after: int | None = None,
    ) -> None:
        """Initialize rate limit information.

        Args:
            limit: Maximum number of requests allowed in the window.
            remaining: Number of requests remaining in the current window.
            reset_at: UTC datetime when the rate limit window resets.
            retry_after: Optional seconds until client should retry.
        """
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
        self.retry_after = retry_after

    def to_headers(self) -> dict[str, str]:
        """Convert rate limit info to HTTP headers.

        Generates standard rate limit headers that can be added to HTTP
        responses to inform clients of their rate limit status.

        Returns:
            Dictionary mapping header names to string values:
                - X-RateLimit-Limit: Maximum requests allowed
                - X-RateLimit-Remaining: Requests remaining (minimum 0)
                - X-RateLimit-Reset: Unix timestamp when window resets
                - Retry-After: Seconds to wait (only if rate limited)
        """
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

    This rate limiter uses in-memory dictionaries to track request counts
    per key within sliding time windows. It also tracks daily request
    counts for quota enforcement.

    Note:
        For production deployments with multiple server instances, this
        should be replaced with Redis-based storage to share state across
        instances.

    Attributes:
        _requests: Mapping of rate limit keys to lists of request timestamps.
        _daily_counts: Nested mapping of user_id -> date -> request count.

    Example:
        >>> limiter = InMemoryRateLimiter()
        >>> limiter.record_request("user:123")
        >>> info = limiter.check_rate_limit("user:123", limit=100)
        >>> print(info.remaining)
        99
    """

    def __init__(self) -> None:
        """Initialize the in-memory rate limiter with empty tracking stores."""
        self._requests: dict[str, list[float]] = {}
        self._daily_counts: dict[str, dict[str, int]] = {}

    def _cleanup_old_requests(self, key: str, window_seconds: int = 60) -> None:
        """Remove requests older than the sliding window.

        Filters out request timestamps that are older than the specified
        window duration to maintain accurate rate limit counting.

        Args:
            key: The rate limit key to clean up.
            window_seconds: Size of the sliding window in seconds. Defaults to 60.
        """
        if key not in self._requests:
            return
        cutoff = time.time() - window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check_rate_limit(
        self, key: str, limit: int, window_seconds: int = 60
    ) -> RateLimitInfo:
        """Check if a request is within rate limits.

        Examines the request history for the given key and determines
        if additional requests are allowed within the current window.

        Args:
            key: The rate limit key (e.g., "user:123" or "ip:192.168.1.1").
            limit: Maximum number of requests allowed in the window.
            window_seconds: Size of the sliding window in seconds. Defaults to 60.

        Returns:
            RateLimitInfo containing the current rate limit state including
            remaining requests and when the limit resets.
        """
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

    def record_request(self, key: str) -> None:
        """Record a request for rate limiting.

        Adds the current timestamp to the request history for the given key.

        Args:
            key: The rate limit key to record the request against.
        """
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key].append(time.time())

    def get_daily_count(self, user_id: str, date: str) -> int:
        """Get daily request count for a user.

        Args:
            user_id: The user identifier.
            date: The date string in YYYY-MM-DD format.

        Returns:
            The number of requests made by the user on the specified date.
        """
        if user_id not in self._daily_counts:
            return 0
        return self._daily_counts.get(user_id, {}).get(date, 0)

    def increment_daily_count(self, user_id: str, date: str) -> None:
        """Increment daily request count for a user.

        Args:
            user_id: The user identifier.
            date: The date string in YYYY-MM-DD format.
        """
        if user_id not in self._daily_counts:
            self._daily_counts[user_id] = {}
        if date not in self._daily_counts[user_id]:
            self._daily_counts[user_id][date] = 0
        self._daily_counts[user_id][date] += 1

    def get_usage_stats(self, user_id: str) -> dict[str, Any]:
        """Get usage statistics for a user.

        Args:
            user_id: The user identifier.

        Returns:
            Dictionary containing:
                - daily_count: Number of requests made today
                - date: Today's date in YYYY-MM-DD format
        """
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return {
            "daily_count": self.get_daily_count(user_id, today),
            "date": today,
        }


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def reset_rate_limiter() -> None:
    """Reset the rate limiter state.

    Creates a new InMemoryRateLimiter instance, clearing all tracked
    requests and daily counts. Useful for testing to ensure clean state
    between test runs.
    """
    global rate_limiter
    rate_limiter = InMemoryRateLimiter()


def get_user_tier(request: Request) -> UserTier:
    """Determine user tier from request.

    Examines the request state to determine the user's tier for rate
    limiting purposes. The tier is determined by checking for user
    attributes set by authentication middleware.

    Args:
        request: The FastAPI request object.

    Returns:
        The UserTier enum value corresponding to the user's tier:
            - ADMIN if user has is_admin=True
            - PREMIUM if user has is_premium=True
            - AUTHENTICATED if user is logged in
            - ANONYMOUS if no user is present
    """
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
    """Generate rate limit key based on user or IP.

    Creates a unique key for rate limiting based on the request's
    authentication status. Authenticated requests use a hash of the
    token, while unauthenticated requests use the client IP address.

    Args:
        request: The FastAPI request object.

    Returns:
        A string key in the format "user:{token_hash}" for authenticated
        requests or "ip:{client_ip}" for unauthenticated requests.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        return f"user:{hash(token)}"
    return f"ip:{get_remote_address(request)}"


def get_endpoint_limit(
    path: str, endpoint_limits: dict[str, int] | None = None
) -> int | None:
    """Get specific rate limit for an endpoint.

    Checks if a specific rate limit is configured for the given path.
    Supports prefix matching, so "/api/v1/bulk/" matches "/api/v1/bulk/upload".

    Args:
        path: The request path to check.
        endpoint_limits: Optional custom endpoint limits dictionary.
            Defaults to ENDPOINT_LIMITS if not provided.

    Returns:
        The rate limit for the endpoint if configured, or None if no
        specific limit exists for the path.
    """
    limits = endpoint_limits if endpoint_limits is not None else ENDPOINT_LIMITS
    for pattern, limit in limits.items():
        if path.startswith(pattern):
            return limit
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for enhanced rate limiting with headers.

    This middleware applies per-request rate limiting based on user tier
    and endpoint-specific limits. It adds rate limit headers to all
    responses and returns 429 responses when limits are exceeded.

    The middleware supports:
        - Per-user rate limits based on authentication tier
        - Endpoint-specific rate limits for sensitive endpoints
        - Daily quota tracking for authenticated users
        - Testing mode with higher limits for E2E testing
        - Skip paths for health checks and WebSocket connections

    Example:
        Add to FastAPI application::

            from fastapi import FastAPI
            from app.core.rate_limiter import RateLimitMiddleware

            app = FastAPI()
            app.add_middleware(RateLimitMiddleware)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting.

        Checks if the request is within rate limits and either processes
        it normally or returns a 429 response. Rate limit headers are
        added to all responses.

        Args:
            request: The incoming FastAPI request.
            call_next: The next middleware or route handler to call.

        Returns:
            The response from the next handler with rate limit headers,
            or a 429 response if rate limits are exceeded.
        """
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Skip rate limiting for health checks, setup status, and WebSocket
        skip_paths = [
            "/health",
            "/ready",
            "/live",
            "/metrics",
            "/setup/status",
            "/api/v1/setup/status",
            "/ws",  # WebSocket connections
        ]
        if request.url.path in skip_paths:
            return await call_next(request)

        key = get_rate_limit_key(request)
        tier = get_user_tier(request)

        # Use testing mode limits if enabled
        testing_mode = settings.rate_limit_testing_mode
        tier_limits = TIER_LIMITS_TESTING if testing_mode else TIER_LIMITS
        endpoint_limits = ENDPOINT_LIMITS_TESTING if testing_mode else ENDPOINT_LIMITS

        # Determine rate limit
        endpoint_limit = None
        for pattern, limit_value in endpoint_limits.items():
            if request.url.path.startswith(pattern):
                endpoint_limit = limit_value
                break
        tier_limit = tier_limits.get(tier, tier_limits[UserTier.ANONYMOUS])
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
    """Check rate limit for a key.

    Convenience function that wraps the global rate limiter's
    check_rate_limit method.

    Args:
        key: The rate limit key to check.
        limit: Maximum number of requests allowed.

    Returns:
        RateLimitInfo containing the current rate limit state.
    """
    return rate_limiter.check_rate_limit(key, limit)


def get_usage_summary(user_id: str | None = None) -> dict[str, Any]:
    """Get rate limit usage summary.

    Returns either user-specific usage statistics or the overall
    rate limit configuration depending on whether a user_id is provided.

    Args:
        user_id: Optional user identifier. If provided, returns user-specific
            statistics. If None, returns the rate limit configuration.

    Returns:
        If user_id is provided:
            Dictionary with daily_count and date for the user.
        If user_id is None:
            Dictionary containing:
                - tier_limits: Rate limits per user tier
                - daily_quotas: Daily quotas per user tier
                - endpoint_limits: Endpoint-specific rate limits
    """
    if user_id:
        return rate_limiter.get_usage_stats(user_id)
    return {
        "tier_limits": {tier.value: limit for tier, limit in TIER_LIMITS.items()},
        "daily_quotas": {
            tier.value: limit for tier, limit in DAILY_QUOTA_LIMITS.items()
        },
        "endpoint_limits": ENDPOINT_LIMITS,
    }
