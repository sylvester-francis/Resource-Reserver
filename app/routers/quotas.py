"""Admin endpoints for managing API rate limits and quotas.

Provides:
- View rate limit configurations
- Manage user quotas
- View API usage statistics
- Monitor rate limit hits

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
    """Rate limit tier configuration."""

    tier: str
    rate_limit_per_minute: int
    daily_quota: int | None


class EndpointLimit(BaseModel):
    """Endpoint-specific rate limit."""

    endpoint: str
    limit_per_minute: int


class RateLimitConfigResponse(BaseModel):
    """Rate limit configuration response."""

    tiers: list[TierConfig]
    endpoint_limits: list[EndpointLimit]


class UserQuotaResponse(BaseModel):
    """User quota information response."""

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
    """Update user quota settings."""

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
    """API usage statistics response."""

    total_requests_today: int
    total_requests_week: int
    total_requests_month: int
    unique_users_today: int
    average_response_time_ms: float | None
    rate_limit_hits_today: int
    top_endpoints: list[dict[str, Any]]
    requests_by_hour: list[dict[str, Any]]


class QuotaAlertResponse(BaseModel):
    """Users approaching quota limits."""

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
    """Get current rate limit configuration.

    Available to all authenticated users to understand their limits.
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
    """Get current user's API usage and quota status."""
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
    """List all user quotas (admin only).

    Requires admin role - regular users should use /my-usage.
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
    """Get quota for a specific user (admin only)."""
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
    """Update quota settings for a user (admin only)."""
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
    """Get API usage statistics (admin only)."""
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
    """Get users approaching their quota limits (admin only)."""
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
    """Reset all daily quota counts (admin only).

    This is typically done automatically at midnight UTC,
    but can be triggered manually if needed.
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
    """Get rate limit summary information."""
    return get_usage_summary()
