"""Admin endpoints for managing API rate limits and quotas.

This module provides a comprehensive API for managing rate limiting and quota
enforcement across the Resource Reserver application. It enables administrators
to configure, monitor, and manage API usage limits for all users.

Features:
    - View and retrieve rate limit configurations by tier
    - Manage individual user quotas with custom limits
    - Monitor API usage statistics and trends
    - Track rate limit violations and quota alerts
    - Reset daily quotas manually when needed
    - Endpoint-specific rate limiting configuration

Example Usage:
    To get the current rate limit configuration::

        GET /api/v1/quotas/config

    To check your personal usage::

        GET /api/v1/quotas/my-usage

    To update a user's quota (admin only)::

        PATCH /api/v1/quotas/users/123
        {
            "tier": "premium",
            "custom_rate_limit": 500,
            "custom_daily_quota": 50000
        }

    To get users approaching their limits::

        GET /api/v1/quotas/alerts?threshold=80

Note:
    Most endpoints in this module require admin privileges. Regular users
    can only access their own usage information via the /my-usage endpoint.

Author: Sylvester-Francis
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.core.rate_limiter import (
    DAILY_QUOTA_LIMITS,
    ENDPOINT_LIMITS,
    TIER_LIMITS,
    UserTier,
    get_usage_summary,
)
from app.database import get_db
from app.rbac import require_role

router = APIRouter(prefix="/api/v1/quotas", tags=["Rate Limits & Quotas"])


# ============================================================================
# Schemas
# ============================================================================


class TierConfig(BaseModel):
    """Rate limit tier configuration schema.

    Represents the rate limiting configuration for a specific user tier,
    including the per-minute rate limit and optional daily quota.

    Attributes:
        tier: The name of the user tier (e.g., 'anonymous', 'authenticated',
            'premium', 'admin').
        rate_limit_per_minute: Maximum number of API requests allowed per minute.
        daily_quota: Maximum number of API requests allowed per day, or None
            for unlimited.
    """

    tier: str
    rate_limit_per_minute: int
    daily_quota: int | None


class EndpointLimit(BaseModel):
    """Endpoint-specific rate limit schema.

    Defines a custom rate limit for a specific API endpoint that overrides
    the default tier-based limits.

    Attributes:
        endpoint: The API endpoint path pattern (e.g., '/api/v1/resources').
        limit_per_minute: Maximum requests allowed per minute for this endpoint.
    """

    endpoint: str
    limit_per_minute: int


class RateLimitConfigResponse(BaseModel):
    """Rate limit configuration response schema.

    Contains the complete rate limiting configuration including all tier
    definitions and endpoint-specific overrides.

    Attributes:
        tiers: List of tier configurations with their rate limits and quotas.
        endpoint_limits: List of endpoint-specific rate limit overrides.
    """

    tiers: list[TierConfig]
    endpoint_limits: list[EndpointLimit]


class UserQuotaResponse(BaseModel):
    """User quota information response schema.

    Provides comprehensive quota and usage information for a specific user,
    including their tier, limits, and current usage statistics.

    Attributes:
        user_id: Unique identifier of the user.
        username: The user's display name.
        tier: The user's current tier level.
        rate_limit_per_minute: Effective rate limit (custom or tier default).
        daily_quota: Effective daily quota (custom or tier default), or None
            for unlimited.
        custom_rate_limit: User-specific rate limit override, if set.
        custom_daily_quota: User-specific daily quota override, if set.
        daily_request_count: Number of requests made today.
        total_requests: Lifetime total request count.
        last_request_date: ISO format date of the last request, or None.
    """

    user_id: int
    username: str
    tier: str
    rate_limit_per_minute: int
    daily_quota: int | None
    custom_rate_limit: int | None
    custom_daily_quota: int | None
    daily_request_count: int
    total_requests: int
    last_request_date: str | None

    model_config = {"from_attributes": True}


class UserQuotaUpdate(BaseModel):
    """Update user quota settings schema.

    Used to modify a user's quota configuration, including their tier
    assignment and custom rate limits.

    Attributes:
        tier: New tier assignment. Valid values are 'anonymous',
            'authenticated', 'premium', 'admin'.
        custom_rate_limit: Custom per-minute rate limit override (1-10000).
        custom_daily_quota: Custom daily quota override (1-1000000).
        reset_daily_count: If True, resets the user's daily request counter.
    """

    tier: str | None = Field(
        None, description="User tier: anonymous, authenticated, premium, admin"
    )
    custom_rate_limit: int | None = Field(
        None, ge=1, le=10000, description="Custom rate limit per minute"
    )
    custom_daily_quota: int | None = Field(
        None, ge=1, le=1000000, description="Custom daily quota"
    )
    reset_daily_count: bool = Field(False, description="Reset daily request count")


class UsageStatsResponse(BaseModel):
    """API usage statistics response schema.

    Provides aggregated API usage metrics for monitoring and analytics,
    including request counts, response times, and usage patterns.

    Attributes:
        total_requests_today: Total API requests made today.
        total_requests_week: Total API requests in the last 7 days.
        total_requests_month: Total API requests in the last 30 days.
        unique_users_today: Number of unique users who made requests today.
        average_response_time_ms: Mean response time in milliseconds, or None
            if no data is available.
        rate_limit_hits_today: Number of 429 (rate limited) responses today.
        top_endpoints: List of most frequently accessed endpoints with counts.
        requests_by_hour: Hourly request distribution for the last 24 hours.
    """

    total_requests_today: int
    total_requests_week: int
    total_requests_month: int
    unique_users_today: int
    average_response_time_ms: float | None
    rate_limit_hits_today: int
    top_endpoints: list[dict[str, Any]]
    requests_by_hour: list[dict[str, Any]]


class QuotaAlertResponse(BaseModel):
    """Users approaching quota limits response schema.

    Represents a user who has consumed a significant portion of their
    daily quota and may need attention or quota adjustment.

    Attributes:
        user_id: Unique identifier of the user.
        username: The user's display name.
        tier: The user's current tier level.
        daily_quota: The user's daily quota limit.
        daily_used: Number of requests consumed today.
        percentage_used: Percentage of daily quota consumed (0-100+).
    """

    user_id: int
    username: str
    tier: str
    daily_quota: int | None
    daily_used: int
    percentage_used: float


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/config", response_model=RateLimitConfigResponse)
def get_rate_limit_config(
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve the current rate limit configuration.

    Returns the complete rate limiting configuration including all tier
    definitions and endpoint-specific rate limits. This endpoint is available
    to all authenticated users so they can understand their applicable limits.

    Args:
        current_user: The authenticated user making the request. Injected
            automatically via dependency injection.

    Returns:
        RateLimitConfigResponse: An object containing:
            - tiers: List of all tier configurations with their rate limits
              and daily quotas.
            - endpoint_limits: List of endpoint-specific rate limit overrides.

    Raises:
        HTTPException: 401 Unauthorized if the user is not authenticated.
    """
    tiers = [
        TierConfig(
            tier=tier.value,
            rate_limit_per_minute=limit,
            daily_quota=DAILY_QUOTA_LIMITS.get(tier),
        )
        for tier, limit in TIER_LIMITS.items()
    ]

    endpoint_limits = [
        EndpointLimit(endpoint=endpoint, limit_per_minute=limit)
        for endpoint, limit in ENDPOINT_LIMITS.items()
    ]

    return RateLimitConfigResponse(tiers=tiers, endpoint_limits=endpoint_limits)


@router.get("/my-usage")
def get_my_usage(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve the current user's API usage and quota status.

    Returns detailed information about the authenticated user's quota
    configuration and current usage statistics. This allows users to
    monitor their API consumption and avoid hitting rate limits.

    The daily request count is automatically reset when a new day begins
    (based on UTC time).

    Args:
        db: Database session for quota queries. Injected via dependency.
        current_user: The authenticated user making the request. Injected
            via dependency injection.

    Returns:
        dict: A dictionary containing the user's quota information:
            - user_id (int): The user's unique identifier.
            - username (str): The user's display name.
            - tier (str): The user's current tier level.
            - rate_limit_per_minute (int): Maximum requests per minute.
            - daily_quota (int | None): Maximum daily requests, or None
              for unlimited.
            - daily_used (int): Requests made today.
            - daily_remaining (int | None): Requests remaining today, or
              None for unlimited quotas.
            - total_requests (int): Lifetime request count.
            - percentage_used (float): Percentage of daily quota consumed.

    Raises:
        HTTPException: 401 Unauthorized if the user is not authenticated.
    """
    # Get or create quota record
    quota = (
        db.query(models.APIQuota)
        .filter(models.APIQuota.user_id == current_user.id)
        .first()
    )

    today = datetime.now(UTC).date()

    if quota:
        # Reset daily count if new day
        if quota.last_request_date != today:
            quota.daily_request_count = 0
            quota.last_request_date = today
            quota.quota_reset_notified = False
            db.commit()

        tier = UserTier(quota.tier)
        rate_limit = quota.custom_rate_limit or TIER_LIMITS.get(tier, 100)
        daily_quota = quota.custom_daily_quota or DAILY_QUOTA_LIMITS.get(tier)
    else:
        tier = UserTier.AUTHENTICATED
        rate_limit = TIER_LIMITS.get(tier, 100)
        daily_quota = DAILY_QUOTA_LIMITS.get(tier)
        quota = models.APIQuota(
            user_id=current_user.id,
            tier=tier.value,
        )
        db.add(quota)
        db.commit()
        db.refresh(quota)

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "tier": tier.value,
        "rate_limit_per_minute": rate_limit,
        "daily_quota": daily_quota,
        "daily_used": quota.daily_request_count,
        "daily_remaining": (
            daily_quota - quota.daily_request_count if daily_quota else None
        ),
        "total_requests": quota.total_requests,
        "percentage_used": (
            round((quota.daily_request_count / daily_quota) * 100, 2)
            if daily_quota
            else 0
        ),
    }


@router.get("/users", response_model=list[UserQuotaResponse])
def list_user_quotas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tier: str | None = Query(None, description="Filter by tier"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _: bool = Depends(require_role("admin")),
):
    """List quota information for all users.

    Retrieves paginated quota information for all users in the system.
    Results can be filtered by tier. This endpoint requires admin privileges;
    regular users should use the /my-usage endpoint instead.

    Args:
        skip: Number of records to skip for pagination. Defaults to 0.
        limit: Maximum number of records to return (1-100). Defaults to 50.
        tier: Optional tier name to filter results (e.g., 'premium').
        db: Database session for quota queries. Injected via dependency.
        current_user: The authenticated admin user. Injected via dependency.
        _: Admin role verification result. Injected via dependency.

    Returns:
        list[UserQuotaResponse]: A list of user quota records, each containing:
            - user_id: The user's unique identifier.
            - username: The user's display name.
            - tier: The user's tier level.
            - rate_limit_per_minute: Effective rate limit.
            - daily_quota: Effective daily quota.
            - custom_rate_limit: Custom rate limit override, if set.
            - custom_daily_quota: Custom quota override, if set.
            - daily_request_count: Requests made today.
            - total_requests: Lifetime request count.
            - last_request_date: ISO date of last request.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
        HTTPException: 403 Forbidden if the user lacks admin privileges.
    """
    query = db.query(models.APIQuota).join(models.User)

    if tier:
        query = query.filter(models.APIQuota.tier == tier)

    quotas = query.offset(skip).limit(limit).all()

    results = []
    for quota in quotas:
        tier_enum = UserTier(quota.tier)
        results.append(
            UserQuotaResponse(
                user_id=quota.user_id,
                username=quota.user.username,
                tier=quota.tier,
                rate_limit_per_minute=quota.custom_rate_limit
                or TIER_LIMITS.get(tier_enum, 100),
                daily_quota=quota.custom_daily_quota
                or DAILY_QUOTA_LIMITS.get(tier_enum),
                custom_rate_limit=quota.custom_rate_limit,
                custom_daily_quota=quota.custom_daily_quota,
                daily_request_count=quota.daily_request_count,
                total_requests=quota.total_requests,
                last_request_date=(
                    quota.last_request_date.isoformat()
                    if quota.last_request_date
                    else None
                ),
            )
        )

    return results


@router.get("/users/{user_id}", response_model=UserQuotaResponse)
def get_user_quota(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _: bool = Depends(require_role("admin")),
):
    """Retrieve quota information for a specific user.

    Gets detailed quota and usage information for the specified user.
    If the user exists but has no quota record, a default quota record
    is created with the 'authenticated' tier. This endpoint requires
    admin privileges.

    Args:
        user_id: The unique identifier of the user to query.
        db: Database session for quota queries. Injected via dependency.
        current_user: The authenticated admin user. Injected via dependency.
        _: Admin role verification result. Injected via dependency.

    Returns:
        UserQuotaResponse: The user's quota information containing:
            - user_id: The user's unique identifier.
            - username: The user's display name.
            - tier: The user's tier level.
            - rate_limit_per_minute: Effective rate limit.
            - daily_quota: Effective daily quota.
            - custom_rate_limit: Custom rate limit override, if set.
            - custom_daily_quota: Custom quota override, if set.
            - daily_request_count: Requests made today.
            - total_requests: Lifetime request count.
            - last_request_date: ISO date of last request.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
        HTTPException: 403 Forbidden if the user lacks admin privileges.
        HTTPException: 404 Not Found if the specified user does not exist.
    """
    quota = db.query(models.APIQuota).filter(models.APIQuota.user_id == user_id).first()

    if not quota:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Create default quota for user
        quota = models.APIQuota(user_id=user_id, tier=UserTier.AUTHENTICATED.value)
        db.add(quota)
        db.commit()
        db.refresh(quota)

    tier_enum = UserTier(quota.tier)
    return UserQuotaResponse(
        user_id=quota.user_id,
        username=quota.user.username,
        tier=quota.tier,
        rate_limit_per_minute=quota.custom_rate_limit
        or TIER_LIMITS.get(tier_enum, 100),
        daily_quota=quota.custom_daily_quota or DAILY_QUOTA_LIMITS.get(tier_enum),
        custom_rate_limit=quota.custom_rate_limit,
        custom_daily_quota=quota.custom_daily_quota,
        daily_request_count=quota.daily_request_count,
        total_requests=quota.total_requests,
        last_request_date=(
            quota.last_request_date.isoformat() if quota.last_request_date else None
        ),
    )


@router.patch("/users/{user_id}", response_model=UserQuotaResponse)
def update_user_quota(
    user_id: int,
    update: UserQuotaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _: bool = Depends(require_role("admin")),
):
    """Update quota settings for a specific user.

    Modifies the quota configuration for the specified user. Administrators
    can change the user's tier, set custom rate limits, custom daily quotas,
    or reset the daily request counter. If the user has no existing quota
    record, one is created with default settings before applying updates.

    Args:
        user_id: The unique identifier of the user to update.
        update: The quota update payload containing:
            - tier: New tier assignment (optional).
            - custom_rate_limit: Custom per-minute limit override (optional).
            - custom_daily_quota: Custom daily quota override (optional).
            - reset_daily_count: Whether to reset the daily counter.
        db: Database session for quota operations. Injected via dependency.
        current_user: The authenticated admin user. Injected via dependency.
        _: Admin role verification result. Injected via dependency.

    Returns:
        UserQuotaResponse: The updated user quota information.

    Raises:
        HTTPException: 400 Bad Request if an invalid tier is specified.
        HTTPException: 401 Unauthorized if not authenticated.
        HTTPException: 403 Forbidden if the user lacks admin privileges.
        HTTPException: 404 Not Found if the specified user does not exist.
    """
    quota = db.query(models.APIQuota).filter(models.APIQuota.user_id == user_id).first()

    if not quota:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        quota = models.APIQuota(user_id=user_id, tier=UserTier.AUTHENTICATED.value)
        db.add(quota)

    if update.tier is not None:
        valid_tiers = [t.value for t in UserTier]
        if update.tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {valid_tiers}",
            )
        quota.tier = update.tier

    if update.custom_rate_limit is not None:
        quota.custom_rate_limit = update.custom_rate_limit

    if update.custom_daily_quota is not None:
        quota.custom_daily_quota = update.custom_daily_quota

    if update.reset_daily_count:
        quota.daily_request_count = 0
        quota.quota_reset_notified = False

    db.commit()
    db.refresh(quota)

    tier_enum = UserTier(quota.tier)
    return UserQuotaResponse(
        user_id=quota.user_id,
        username=quota.user.username,
        tier=quota.tier,
        rate_limit_per_minute=quota.custom_rate_limit
        or TIER_LIMITS.get(tier_enum, 100),
        daily_quota=quota.custom_daily_quota or DAILY_QUOTA_LIMITS.get(tier_enum),
        custom_rate_limit=quota.custom_rate_limit,
        custom_daily_quota=quota.custom_daily_quota,
        daily_request_count=quota.daily_request_count,
        total_requests=quota.total_requests,
        last_request_date=(
            quota.last_request_date.isoformat() if quota.last_request_date else None
        ),
    )


@router.get("/stats", response_model=UsageStatsResponse)
def get_usage_statistics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _: bool = Depends(require_role("admin")),
):
    """Retrieve aggregated API usage statistics.

    Provides comprehensive API usage metrics for monitoring and analytics
    purposes. Statistics include request counts by time period, unique user
    counts, response times, rate limit violations, and usage patterns.
    This endpoint requires admin privileges.

    Args:
        db: Database session for statistics queries. Injected via dependency.
        current_user: The authenticated admin user. Injected via dependency.
        _: Admin role verification result. Injected via dependency.

    Returns:
        UsageStatsResponse: Aggregated usage statistics containing:
            - total_requests_today: Request count for the current day.
            - total_requests_week: Request count for the last 7 days.
            - total_requests_month: Request count for the last 30 days.
            - unique_users_today: Distinct users who made requests today.
            - average_response_time_ms: Mean response time in milliseconds.
            - rate_limit_hits_today: Count of 429 responses today.
            - top_endpoints: Top 10 most accessed endpoints with counts.
            - requests_by_hour: Hourly request distribution (last 24 hours).

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
        HTTPException: 403 Forbidden if the user lacks admin privileges.
    """
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # Total requests by period
    total_today = (
        db.query(func.count(models.APIUsageLog.id))
        .filter(models.APIUsageLog.timestamp >= today_start)
        .scalar()
        or 0
    )

    total_week = (
        db.query(func.count(models.APIUsageLog.id))
        .filter(models.APIUsageLog.timestamp >= week_start)
        .scalar()
        or 0
    )

    total_month = (
        db.query(func.count(models.APIUsageLog.id))
        .filter(models.APIUsageLog.timestamp >= month_start)
        .scalar()
        or 0
    )

    # Unique users today
    unique_users = (
        db.query(func.count(func.distinct(models.APIUsageLog.user_id)))
        .filter(
            models.APIUsageLog.timestamp >= today_start,
            models.APIUsageLog.user_id.isnot(None),
        )
        .scalar()
        or 0
    )

    # Average response time
    avg_response = (
        db.query(func.avg(models.APIUsageLog.response_time_ms))
        .filter(
            models.APIUsageLog.timestamp >= today_start,
            models.APIUsageLog.response_time_ms.isnot(None),
        )
        .scalar()
    )

    # Rate limit hits (429 responses)
    rate_limit_hits = (
        db.query(func.count(models.APIUsageLog.id))
        .filter(
            models.APIUsageLog.timestamp >= today_start,
            models.APIUsageLog.status_code == 429,
        )
        .scalar()
        or 0
    )

    # Top endpoints
    top_endpoints_query = (
        db.query(
            models.APIUsageLog.endpoint,
            func.count(models.APIUsageLog.id).label("count"),
        )
        .filter(models.APIUsageLog.timestamp >= today_start)
        .group_by(models.APIUsageLog.endpoint)
        .order_by(func.count(models.APIUsageLog.id).desc())
        .limit(10)
        .all()
    )

    top_endpoints = [
        {"endpoint": endpoint, "count": count}
        for endpoint, count in top_endpoints_query
    ]

    # Requests by hour (last 24 hours)
    requests_by_hour = []
    for i in range(24):
        hour_start = today_start - timedelta(hours=23 - i)
        hour_end = hour_start + timedelta(hours=1)
        count = (
            db.query(func.count(models.APIUsageLog.id))
            .filter(
                models.APIUsageLog.timestamp >= hour_start,
                models.APIUsageLog.timestamp < hour_end,
            )
            .scalar()
            or 0
        )
        requests_by_hour.append({"hour": hour_start.strftime("%H:00"), "count": count})

    return UsageStatsResponse(
        total_requests_today=total_today,
        total_requests_week=total_week,
        total_requests_month=total_month,
        unique_users_today=unique_users,
        average_response_time_ms=round(avg_response, 2) if avg_response else None,
        rate_limit_hits_today=rate_limit_hits,
        top_endpoints=top_endpoints,
        requests_by_hour=requests_by_hour,
    )


@router.get("/alerts", response_model=list[QuotaAlertResponse])
def get_quota_alerts(
    threshold: float = Query(
        80.0, ge=0, le=100, description="Alert threshold percentage"
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _: bool = Depends(require_role("admin")),
):
    """Retrieve users who are approaching their quota limits.

    Identifies and returns users whose daily quota consumption has exceeded
    the specified threshold percentage. This helps administrators proactively
    manage quotas and prevent service disruptions. Users with unlimited
    quotas are excluded from the results. Results are sorted by usage
    percentage in descending order.

    Args:
        threshold: Minimum percentage of quota consumed to trigger an alert.
            Defaults to 80.0. Must be between 0 and 100.
        db: Database session for quota queries. Injected via dependency.
        current_user: The authenticated admin user. Injected via dependency.
        _: Admin role verification result. Injected via dependency.

    Returns:
        list[QuotaAlertResponse]: A list of users exceeding the threshold,
            sorted by percentage used (highest first). Each entry contains:
            - user_id: The user's unique identifier.
            - username: The user's display name.
            - tier: The user's tier level.
            - daily_quota: The user's daily quota limit.
            - daily_used: Number of requests consumed today.
            - percentage_used: Percentage of quota consumed.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
        HTTPException: 403 Forbidden if the user lacks admin privileges.
    """
    quotas = db.query(models.APIQuota).join(models.User).all()

    alerts = []
    for quota in quotas:
        tier_enum = UserTier(quota.tier)
        daily_quota = quota.custom_daily_quota or DAILY_QUOTA_LIMITS.get(tier_enum)

        if daily_quota is None:
            continue  # Skip unlimited quotas

        percentage = (quota.daily_request_count / daily_quota) * 100

        if percentage >= threshold:
            alerts.append(
                QuotaAlertResponse(
                    user_id=quota.user_id,
                    username=quota.user.username,
                    tier=quota.tier,
                    daily_quota=daily_quota,
                    daily_used=quota.daily_request_count,
                    percentage_used=round(percentage, 2),
                )
            )

    # Sort by percentage used (highest first)
    alerts.sort(key=lambda x: x.percentage_used, reverse=True)

    return alerts


@router.post("/reset-daily")
def reset_daily_quotas(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _: bool = Depends(require_role("admin")),
):
    """Reset daily quota counts for all users.

    Manually resets the daily request counters for all users who have
    made at least one request. This operation is typically performed
    automatically at midnight UTC, but can be triggered manually when
    needed (e.g., after resolving a service incident).

    The reset also clears the quota notification flag, allowing users
    to receive quota warning notifications again.

    Args:
        db: Database session for quota operations. Injected via dependency.
        current_user: The authenticated admin user. Injected via dependency.
        _: Admin role verification result. Injected via dependency.

    Returns:
        dict: A confirmation message containing:
            - message (str): Human-readable confirmation of the reset.
            - reset_count (int): Number of user quotas that were reset.
            - timestamp (str): ISO format timestamp of when the reset occurred.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
        HTTPException: 403 Forbidden if the user lacks admin privileges.
    """
    updated = (
        db.query(models.APIQuota)
        .filter(models.APIQuota.daily_request_count > 0)
        .update(
            {
                "daily_request_count": 0,
                "quota_reset_notified": False,
                "last_request_date": datetime.now(UTC).date(),
            }
        )
    )

    db.commit()

    return {
        "message": f"Reset daily quotas for {updated} users",
        "reset_count": updated,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/summary")
def get_rate_limit_summary(
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve a summary of rate limit information.

    Returns a high-level summary of the rate limiting system configuration
    and status. This endpoint delegates to the rate limiter module's
    get_usage_summary function. Available to all authenticated users.

    Args:
        current_user: The authenticated user making the request. Injected
            via dependency injection.

    Returns:
        dict: A summary of rate limit information as returned by the
            rate limiter module's get_usage_summary function.

    Raises:
        HTTPException: 401 Unauthorized if the user is not authenticated.
    """
    return get_usage_summary()
