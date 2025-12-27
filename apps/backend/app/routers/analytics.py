"""Analytics endpoints for resource utilization insights.

This module provides a comprehensive set of RESTful API endpoints for analyzing
resource usage patterns, utilization metrics, and booking behaviors within the
Resource Reserver system. It enables administrators and authorized users to
gain actionable insights into how resources are being utilized.

Features:
    - Dashboard summary with key performance indicators
    - Resource utilization metrics with percentage calculations
    - Popular resources ranking by reservation count
    - Peak usage times analysis (hourly and daily distributions)
    - User booking pattern analysis with cancellation rates
    - CSV export functionality for utilization and reservation data

Example Usage:
    The endpoints are accessible via the /api/v1/analytics prefix::

        # Get dashboard summary for the last 30 days
        GET /api/v1/analytics/dashboard?days=30

        # Get utilization for a specific resource
        GET /api/v1/analytics/utilization?resource_id=5&days=60

        # Export utilization data as CSV
        GET /api/v1/analytics/export/utilization.csv?days=90

Note:
    All endpoints require authentication. The current user must be logged in
    to access analytics data.

Author:
    Sylvester-Francis
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
    """Retrieve the analytics dashboard summary.

    Provides a comprehensive overview of resource utilization, popular resources,
    and usage patterns for the specified time period. This endpoint aggregates
    multiple analytics metrics into a single dashboard view.

    Args:
        request: The incoming FastAPI request object.
        days: Number of days to include in the analysis. Must be between 1 and 365.
            Defaults to 30 days.
        db: Database session dependency for querying analytics data.
        current_user: The authenticated user making the request.

    Returns:
        dict: A dashboard summary containing:
            - total_reservations: Total number of reservations in the period.
            - active_resources: Number of resources with at least one booking.
            - average_utilization: Mean utilization percentage across resources.
            - top_resources: List of most frequently booked resources.
            - recent_activity: Summary of recent booking activity.

    Raises:
        HTTPException: 401 if the user is not authenticated.
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
    """Retrieve resource utilization metrics.

    Calculates and returns the utilization percentage for each resource,
    indicating what proportion of available time each resource was booked.
    Utilization is computed based on reservation durations within the
    specified analysis period.

    Args:
        request: The incoming FastAPI request object.
        resource_id: Optional filter to get utilization for a specific resource.
            If None, returns utilization for all resources.
        days: Number of days to include in the analysis. Must be between 1 and 365.
            Defaults to 30 days.
        db: Database session dependency for querying utilization data.
        current_user: The authenticated user making the request.

    Returns:
        dict: A dictionary containing:
            - period: Object with start date, end date, and days analyzed.
            - utilization: List of resource utilization records, each containing:
                - resource_id: The unique identifier of the resource.
                - resource_name: The name of the resource.
                - utilization_percent: Percentage of time the resource was booked.
                - total_hours_booked: Total hours the resource was reserved.

    Raises:
        HTTPException: 401 if the user is not authenticated.
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
    """Retrieve the most popular resources by reservation count.

    Returns a ranked list of resources sorted by the number of bookings
    they received during the specified time period. This helps identify
    high-demand resources for capacity planning.

    Args:
        request: The incoming FastAPI request object.
        limit: Maximum number of resources to return in the ranking.
            Must be between 1 and 100. Defaults to 10.
        days: Number of days to include in the analysis. Must be between 1 and 365.
            Defaults to 30 days.
        db: Database session dependency for querying reservation data.
        current_user: The authenticated user making the request.

    Returns:
        dict: A dictionary containing:
            - period: Object with start date, end date, and days analyzed.
            - resources: List of popular resources, each containing:
                - resource_id: The unique identifier of the resource.
                - resource_name: The name of the resource.
                - reservation_count: Number of reservations for this resource.
                - total_hours: Total hours booked for this resource.
                - unique_users: Number of distinct users who booked this resource.

    Raises:
        HTTPException: 401 if the user is not authenticated.
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
    """Retrieve peak usage times analysis.

    Analyzes reservation patterns to identify when resources are most
    frequently booked. Returns both hourly and daily distributions to
    help optimize resource availability and scheduling.

    Args:
        request: The incoming FastAPI request object.
        days: Number of days to include in the analysis. Must be between 1 and 365.
            Defaults to 30 days.
        db: Database session dependency for querying reservation timing data.
        current_user: The authenticated user making the request.

    Returns:
        dict: A dictionary containing:
            - period: Object with start date, end date, and days analyzed.
            - hourly_distribution: List of 24 entries (0-23) with reservation
                counts for each hour of the day.
            - daily_distribution: List of 7 entries (Monday-Sunday) with
                reservation counts for each day of the week.
            - peak_hour: The hour with the highest reservation activity.
            - peak_day: The day of the week with the highest reservation activity.

    Raises:
        HTTPException: 401 if the user is not authenticated.
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
    """Retrieve user booking patterns and statistics.

    Analyzes booking behavior for users, including reservation counts,
    cancellation rates, and usage trends. Useful for identifying power
    users and understanding booking habits.

    Args:
        request: The incoming FastAPI request object.
        user_id: Optional filter to get patterns for a specific user.
            If None, returns patterns for all users up to the limit.
        limit: Maximum number of users to include in the results.
            Must be between 1 and 100. Defaults to 20.
        days: Number of days to include in the analysis. Must be between 1 and 365.
            Defaults to 30 days.
        db: Database session dependency for querying user booking data.
        current_user: The authenticated user making the request.

    Returns:
        dict: A dictionary containing:
            - period: Object with start date, end date, and days analyzed.
            - users: List of user booking patterns, each containing:
                - user_id: The unique identifier of the user.
                - username: The username of the user.
                - total_reservations: Number of reservations made by this user.
                - cancelled_reservations: Number of cancelled reservations.
                - cancellation_rate: Percentage of reservations that were cancelled.
                - favorite_resources: Most frequently booked resources by this user.

    Raises:
        HTTPException: 401 if the user is not authenticated.
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
    """Export resource utilization data as a CSV file.

    Generates and downloads a CSV file containing detailed resource
    utilization metrics for the specified time period. The file includes
    headers and is suitable for import into spreadsheet applications.

    Args:
        request: The incoming FastAPI request object.
        days: Number of days to include in the export. Must be between 1 and 365.
            Defaults to 30 days.
        db: Database session dependency for querying utilization data.
        current_user: The authenticated user making the request.

    Returns:
        Response: A FastAPI Response object with:
            - content: CSV-formatted string containing utilization data.
            - media_type: Set to "text/csv" for proper browser handling.
            - headers: Content-Disposition header for file download with
                filename format "utilization_{days}days.csv".

    Raises:
        HTTPException: 401 if the user is not authenticated.

    Note:
        The CSV includes columns for resource ID, resource name,
        utilization percentage, total hours booked, and analysis period.
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
    """Export reservations data as a CSV file.

    Generates and downloads a CSV file containing detailed reservation
    records for the specified time period. The file includes all booking
    information and is suitable for auditing or external analysis.

    Args:
        request: The incoming FastAPI request object.
        days: Number of days to include in the export. Must be between 1 and 365.
            Defaults to 30 days.
        db: Database session dependency for querying reservation data.
        current_user: The authenticated user making the request.

    Returns:
        Response: A FastAPI Response object with:
            - content: CSV-formatted string containing reservation data.
            - media_type: Set to "text/csv" for proper browser handling.
            - headers: Content-Disposition header for file download with
                filename format "reservations_{days}days.csv".

    Raises:
        HTTPException: 401 if the user is not authenticated.

    Note:
        The CSV includes columns for reservation ID, resource name, user,
        start time, end time, status, and creation timestamp.
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
