"""Analytics endpoints for resource utilization insights.

Provides endpoints for:
- Resource utilization metrics
- Popular resources ranking
- Peak usage times analysis
- User booking patterns
- CSV exports

Author: Sylvester-Francis
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import models
from app.analytics_service import AnalyticsService
from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

settings = get_settings()


@router.get("/dashboard")
def get_analytics_dashboard(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get analytics dashboard summary.

    Returns a comprehensive summary of resource utilization,
    popular resources, and usage patterns for the specified period.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    service = AnalyticsService(db)
    return service.get_dashboard_summary(start_date=start_date, end_date=end_date)


@router.get("/utilization")
def get_resource_utilization(
    request: Request,
    resource_id: int | None = Query(None, description="Filter by resource ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get resource utilization metrics.

    Returns utilization percentage for each resource showing
    what percentage of time it was booked.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    service = AnalyticsService(db)
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days,
        },
        "utilization": service.get_resource_utilization(
            resource_id=resource_id, start_date=start_date, end_date=end_date
        ),
    }


@router.get("/popular-resources")
def get_popular_resources(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Number of resources to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get most popular resources by reservation count.

    Returns the top resources ranked by number of bookings
    in the specified period.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    service = AnalyticsService(db)
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days,
        },
        "resources": service.get_popular_resources(
            limit=limit, start_date=start_date, end_date=end_date
        ),
    }


@router.get("/peak-times")
def get_peak_usage_times(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get peak usage times analysis.

    Returns hourly and daily distribution of reservations
    to identify peak usage periods.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    service = AnalyticsService(db)
    return service.get_peak_usage_times(start_date=start_date, end_date=end_date)


@router.get("/user-patterns")
def get_user_booking_patterns(
    request: Request,
    user_id: int | None = Query(None, description="Filter by user ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of users to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get user booking patterns and statistics.

    Returns booking statistics for users including reservation
    counts and cancellation rates.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    service = AnalyticsService(db)
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days,
        },
        "users": service.get_user_booking_patterns(
            user_id=user_id, limit=limit, start_date=start_date, end_date=end_date
        ),
    }


@router.get("/export/utilization.csv")
def export_utilization_csv(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Export resource utilization data as CSV.

    Downloads a CSV file containing resource utilization metrics.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    service = AnalyticsService(db)
    csv_content = service.export_utilization_csv(
        start_date=start_date, end_date=end_date
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=utilization_{days}days.csv"
        },
    )


@router.get("/export/reservations.csv")
def export_reservations_csv(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Export reservations data as CSV.

    Downloads a CSV file containing reservation details.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    service = AnalyticsService(db)
    csv_content = service.export_reservations_csv(
        start_date=start_date, end_date=end_date
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=reservations_{days}days.csv"
        },
    )
