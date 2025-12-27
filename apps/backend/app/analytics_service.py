"""Analytics service for resource utilization insights.

This module provides comprehensive analytics and reporting capabilities for
the Resource Reserver system. It enables stakeholders to gain insights into
resource usage patterns, identify bottlenecks, and make data-driven decisions
about resource allocation.

Features:
    - Resource utilization metrics: Calculate percentage-based utilization for
      any resource over configurable time periods.
    - Popular resources ranking: Identify the most frequently booked resources
      to understand demand patterns.
    - Peak usage times analysis: Determine when resources are most in-demand
      by analyzing hourly and daily booking distributions.
    - User booking patterns: Track user behavior including booking frequency
      and cancellation rates.
    - Exportable reports: Generate CSV exports for utilization and reservation
      data for external analysis or reporting.

Example usage:
    >>> from sqlalchemy.orm import Session
    >>> from app.analytics_service import AnalyticsService
    >>> from datetime import datetime, timedelta, UTC
    >>>
    >>> # Initialize the service with a database session
    >>> db: Session = get_db_session()
    >>> analytics = AnalyticsService(db)
    >>>
    >>> # Get resource utilization for the last 7 days
    >>> end_date = datetime.now(UTC)
    >>> start_date = end_date - timedelta(days=7)
    >>> utilization = analytics.get_resource_utilization(
    ...     start_date=start_date,
    ...     end_date=end_date
    ... )
    >>>
    >>> # Get dashboard summary
    >>> summary = analytics.get_dashboard_summary()
    >>>
    >>> # Export data to CSV
    >>> csv_data = analytics.export_utilization_csv()

Author:
    Sylvester-Francis
"""

import csv
from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models


class AnalyticsService:
    """Service for generating analytics and reports on resource usage.

    This class provides methods to analyze resource utilization, identify
    popular resources, determine peak usage times, track user booking patterns,
    and export analytical data to various formats.

    The service operates on a SQLAlchemy database session and queries the
    Resource, Reservation, and User models to generate insights.

    Attributes:
        db (Session): The SQLAlchemy database session used for all database
            operations. This session should be managed externally and passed
            to the constructor.

    Example:
        >>> db = SessionLocal()
        >>> analytics = AnalyticsService(db)
        >>> top_resources = analytics.get_popular_resources(limit=5)
        >>> for resource in top_resources:
        ...     print(f"{resource['resource_name']}: {resource['reservation_count']} bookings")
    """

    def __init__(self, db: Session) -> None:
        """Initialize the AnalyticsService with a database session.

        Args:
            db: A SQLAlchemy Session object used for querying the database.
                The session should be properly configured and connected to
                the application database.
        """
        self.db = db

    def get_resource_utilization(
        self,
        resource_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Calculate resource utilization percentage over a time period.

        Computes the utilization percentage for each resource by comparing
        the total booked hours against the total available hours in the
        specified time period. Only reservations with 'active' or 'expired'
        status are considered.

        Args:
            resource_id: Optional ID of a specific resource to analyze.
                If None, all resources are included in the analysis.
            start_date: The beginning of the analysis period. If None,
                defaults to 30 days before the current time. Timezone-naive
                datetimes are treated as UTC.
            end_date: The end of the analysis period. If None, defaults
                to the current time. Timezone-naive datetimes are treated
                as UTC.

        Returns:
            A list of dictionaries containing utilization data for each
            resource, sorted by utilization percentage in descending order.
            Each dictionary contains:
                - resource_id (int): The unique identifier of the resource.
                - resource_name (str): The display name of the resource.
                - total_hours_available (float): Total hours in the period,
                  rounded to 2 decimal places.
                - booked_hours (float): Hours the resource was reserved,
                  rounded to 2 decimal places.
                - utilization_percent (float): Percentage of time utilized,
                  rounded to 2 decimal places (0-100).
                - status (str): Current status of the resource.

        Example:
            >>> analytics = AnalyticsService(db)
            >>> utilization = analytics.get_resource_utilization(
            ...     start_date=datetime(2024, 1, 1, tzinfo=UTC),
            ...     end_date=datetime(2024, 1, 31, tzinfo=UTC)
            ... )
            >>> for item in utilization:
            ...     print(f"{item['resource_name']}: {item['utilization_percent']}%")
        """
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(UTC)

        # Ensure timezone awareness for consistent datetime comparisons
        start_date = (
            start_date.replace(tzinfo=UTC) if start_date.tzinfo is None else start_date
        )
        end_date = end_date.replace(tzinfo=UTC) if end_date.tzinfo is None else end_date

        # Get resources
        query = self.db.query(models.Resource)
        if resource_id:
            query = query.filter(models.Resource.id == resource_id)
        resources = query.all()

        utilization_data = []
        total_hours = (end_date - start_date).total_seconds() / 3600

        for resource in resources:
            # Get completed/active reservations for this resource in the period
            reservations = (
                self.db.query(models.Reservation)
                .filter(
                    models.Reservation.resource_id == resource.id,
                    models.Reservation.status.in_(["active", "expired"]),
                    models.Reservation.start_time < end_date,
                    models.Reservation.end_time > start_date,
                )
                .all()
            )

            # Calculate total booked hours
            booked_hours = 0.0
            for res in reservations:
                # Clip to analysis period with timezone-aware datetimes
                res_start = (
                    res.start_time.replace(tzinfo=UTC)
                    if res.start_time.tzinfo is None
                    else res.start_time
                )
                res_end = (
                    res.end_time.replace(tzinfo=UTC)
                    if res.end_time.tzinfo is None
                    else res.end_time
                )
                res_start = max(res_start, start_date)
                res_end = min(res_end, end_date)
                booked_hours += (res_end - res_start).total_seconds() / 3600

            utilization_pct = (
                (booked_hours / total_hours * 100) if total_hours > 0 else 0
            )

            utilization_data.append(
                {
                    "resource_id": resource.id,
                    "resource_name": resource.name,
                    "total_hours_available": round(total_hours, 2),
                    "booked_hours": round(booked_hours, 2),
                    "utilization_percent": round(utilization_pct, 2),
                    "status": resource.status,
                }
            )

        return sorted(
            utilization_data, key=lambda x: x["utilization_percent"], reverse=True
        )

    def get_popular_resources(
        self,
        limit: int = 10,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get the most popular resources ranked by reservation count.

        Queries the database to find resources with the highest number of
        reservations within the specified time period. Only reservations
        with 'active' or 'expired' status are counted.

        Args:
            limit: Maximum number of resources to return. Defaults to 10.
                Must be a positive integer.
            start_date: The beginning of the analysis period. If None,
                defaults to 30 days before the current time.
            end_date: The end of the analysis period. If None, defaults
                to the current time.

        Returns:
            A list of dictionaries containing popularity data for each
            resource, ordered by reservation count (most popular first).
            Each dictionary contains:
                - resource_id (int): The unique identifier of the resource.
                - resource_name (str): The display name of the resource.
                - reservation_count (int): Total number of reservations.
                - rank (int): The popularity rank (1 = most popular).

        Example:
            >>> analytics = AnalyticsService(db)
            >>> top_5 = analytics.get_popular_resources(limit=5)
            >>> print(f"Most popular: {top_5[0]['resource_name']}")
        """
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(UTC)

        results = (
            self.db.query(
                models.Resource.id,
                models.Resource.name,
                func.count(models.Reservation.id).label("reservation_count"),
            )
            .join(
                models.Reservation,
                models.Resource.id == models.Reservation.resource_id,
            )
            .filter(
                models.Reservation.start_time >= start_date,
                models.Reservation.start_time < end_date,
                models.Reservation.status.in_(["active", "expired"]),
            )
            .group_by(models.Resource.id, models.Resource.name)
            .order_by(func.count(models.Reservation.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "resource_id": r.id,
                "resource_name": r.name,
                "reservation_count": r.reservation_count,
                "rank": idx + 1,
            }
            for idx, r in enumerate(results)
        ]

    def get_peak_usage_times(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Analyze peak usage times by hour of day and day of week.

        Aggregates reservation data to identify when resources are most
        frequently booked. This helps in understanding usage patterns
        and planning for high-demand periods.

        Args:
            start_date: The beginning of the analysis period. If None,
                defaults to 30 days before the current time.
            end_date: The end of the analysis period. If None, defaults
                to the current time.

        Returns:
            A dictionary containing comprehensive peak usage analysis:
                - period (dict): Contains 'start' and 'end' ISO format strings.
                - total_reservations (int): Total reservation count analyzed.
                - hourly_distribution (list): List of dicts with 'hour' (0-23)
                  and 'count' for each hour of the day.
                - daily_distribution (list): List of dicts with 'day' (name),
                  'day_number' (0=Monday, 6=Sunday), and 'count'.
                - peak_hour (int): Hour with highest reservation count (0-23).
                - peak_hour_count (int): Number of reservations at peak hour.
                - peak_day (str): Day name with highest reservation count.
                - peak_day_count (int): Number of reservations on peak day.

        Example:
            >>> analytics = AnalyticsService(db)
            >>> peak_times = analytics.get_peak_usage_times()
            >>> print(f"Busiest hour: {peak_times['peak_hour']}:00")
            >>> print(f"Busiest day: {peak_times['peak_day']}")
        """
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(UTC)

        reservations = (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.start_time >= start_date,
                models.Reservation.start_time < end_date,
                models.Reservation.status.in_(["active", "expired"]),
            )
            .all()
        )

        # Aggregate by hour of day and day of week
        hourly_counts = [0] * 24
        daily_counts = [0] * 7  # 0 = Monday, 6 = Sunday

        for res in reservations:
            hour = res.start_time.hour
            day = res.start_time.weekday()
            hourly_counts[hour] += 1
            daily_counts[day] += 1

        # Find peaks
        peak_hour = hourly_counts.index(max(hourly_counts))
        peak_day = daily_counts.index(max(daily_counts))

        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_reservations": len(reservations),
            "hourly_distribution": [
                {"hour": h, "count": c} for h, c in enumerate(hourly_counts)
            ],
            "daily_distribution": [
                {"day": days[d], "day_number": d, "count": c}
                for d, c in enumerate(daily_counts)
            ],
            "peak_hour": peak_hour,
            "peak_hour_count": hourly_counts[peak_hour],
            "peak_day": days[peak_day],
            "peak_day_count": daily_counts[peak_day],
        }

    def get_user_booking_patterns(
        self,
        user_id: int | None = None,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get user booking patterns and statistics.

        Analyzes user behavior by aggregating their reservation activity,
        including total bookings and cancellation rates. This data can be
        used to identify power users or detect unusual booking patterns.

        Args:
            user_id: Optional ID of a specific user to analyze. If None,
                returns statistics for all users up to the limit.
            limit: Maximum number of users to return when user_id is None.
                Defaults to 20. Ignored when user_id is specified.
            start_date: The beginning of the analysis period. If None,
                defaults to 30 days before the current time.
            end_date: The end of the analysis period. If None, defaults
                to the current time.

        Returns:
            A list of dictionaries containing booking pattern data for each
            user, ordered by total reservations (most active first).
            Each dictionary contains:
                - user_id (int): The unique identifier of the user.
                - username (str): The user's username.
                - total_reservations (int): Total reservation count.
                - cancelled_count (int): Number of cancelled reservations.
                - cancellation_rate (float): Percentage of reservations
                  cancelled, rounded to 2 decimal places (0-100).

        Example:
            >>> analytics = AnalyticsService(db)
            >>> patterns = analytics.get_user_booking_patterns(limit=10)
            >>> for user in patterns:
            ...     if user['cancellation_rate'] > 50:
            ...         print(f"High cancellation rate: {user['username']}")
        """
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(UTC)

        query = (
            self.db.query(
                models.User.id,
                models.User.username,
                func.count(models.Reservation.id).label("total_reservations"),
                func.count(models.Reservation.id)
                .filter(models.Reservation.status == "cancelled")
                .label("cancelled_count"),
            )
            .join(
                models.Reservation,
                models.User.id == models.Reservation.user_id,
            )
            .filter(
                models.Reservation.created_at >= start_date,
                models.Reservation.created_at < end_date,
            )
            .group_by(models.User.id, models.User.username)
            .order_by(func.count(models.Reservation.id).desc())
        )

        if user_id:
            query = query.filter(models.User.id == user_id)
        else:
            query = query.limit(limit)

        results = query.all()

        patterns = []
        for r in results:
            cancellation_rate = (
                (r.cancelled_count / r.total_reservations * 100)
                if r.total_reservations > 0
                else 0
            )
            patterns.append(
                {
                    "user_id": r.id,
                    "username": r.username,
                    "total_reservations": r.total_reservations,
                    "cancelled_count": r.cancelled_count,
                    "cancellation_rate": round(cancellation_rate, 2),
                }
            )

        return patterns

    def get_dashboard_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get a comprehensive summary of all analytics for the dashboard.

        Aggregates multiple analytics metrics into a single response suitable
        for displaying on a dashboard or overview page. This method combines
        overview statistics, top resources, and peak usage information.

        Args:
            start_date: The beginning of the analysis period. If None,
                defaults to 30 days before the current time.
            end_date: The end of the analysis period. If None, defaults
                to the current time.

        Returns:
            A dictionary containing a complete analytics summary:
                - period (dict): Contains 'start' and 'end' ISO format strings.
                - overview (dict): Contains:
                    - total_resources (int): Total number of resources.
                    - total_users (int): Total number of users.
                    - total_reservations (int): Reservations in the period.
                    - active_reservations (int): Currently active reservations.
                    - cancelled_reservations (int): Cancelled reservations.
                    - cancellation_rate (float): Percentage cancelled (0-100).
                    - average_utilization (float): Mean utilization across
                      all resources, rounded to 2 decimal places.
                - top_resources (list): Top 5 most popular resources, each with
                  resource_id, resource_name, reservation_count, and rank.
                - peak_times (dict): Contains 'peak_hour' (int) and 'peak_day'
                  (str) indicating when usage is highest.

        Example:
            >>> analytics = AnalyticsService(db)
            >>> summary = analytics.get_dashboard_summary()
            >>> print(f"Total reservations: {summary['overview']['total_reservations']}")
            >>> print(f"Avg utilization: {summary['overview']['average_utilization']}%")
        """
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(UTC)

        # Basic counts
        total_resources = self.db.query(func.count(models.Resource.id)).scalar()
        total_users = self.db.query(func.count(models.User.id)).scalar()

        # Reservation counts for the period
        reservations_query = self.db.query(models.Reservation).filter(
            models.Reservation.created_at >= start_date,
            models.Reservation.created_at < end_date,
        )

        total_reservations = reservations_query.count()
        active_reservations = reservations_query.filter(
            models.Reservation.status == "active"
        ).count()
        cancelled_reservations = reservations_query.filter(
            models.Reservation.status == "cancelled"
        ).count()

        # Average utilization
        utilization = self.get_resource_utilization(
            start_date=start_date, end_date=end_date
        )
        avg_utilization = (
            sum(r["utilization_percent"] for r in utilization) / len(utilization)
            if utilization
            else 0
        )

        # Top 5 resources
        top_resources = self.get_popular_resources(
            limit=5, start_date=start_date, end_date=end_date
        )

        # Peak times
        peak_times = self.get_peak_usage_times(start_date=start_date, end_date=end_date)

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "overview": {
                "total_resources": total_resources,
                "total_users": total_users,
                "total_reservations": total_reservations,
                "active_reservations": active_reservations,
                "cancelled_reservations": cancelled_reservations,
                "cancellation_rate": (
                    round(cancelled_reservations / total_reservations * 100, 2)
                    if total_reservations > 0
                    else 0
                ),
                "average_utilization": round(avg_utilization, 2),
            },
            "top_resources": top_resources,
            "peak_times": {
                "peak_hour": peak_times["peak_hour"],
                "peak_day": peak_times["peak_day"],
            },
        }

    def export_utilization_csv(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> str:
        """Export resource utilization data to CSV format.

        Generates a CSV-formatted string containing utilization metrics
        for all resources. This can be used for external analysis,
        reporting, or importing into spreadsheet applications.

        Args:
            start_date: The beginning of the analysis period. If None,
                defaults to 30 days before the current time (inherited
                from get_resource_utilization).
            end_date: The end of the analysis period. If None, defaults
                to the current time (inherited from get_resource_utilization).

        Returns:
            A CSV-formatted string with headers and data rows. The columns
            are: resource_id, resource_name, total_hours_available,
            booked_hours, utilization_percent, and status.

        Example:
            >>> analytics = AnalyticsService(db)
            >>> csv_content = analytics.export_utilization_csv()
            >>> with open('utilization_report.csv', 'w') as f:
            ...     f.write(csv_content)
        """
        utilization = self.get_resource_utilization(
            start_date=start_date, end_date=end_date
        )

        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "resource_id",
                "resource_name",
                "total_hours_available",
                "booked_hours",
                "utilization_percent",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(utilization)

        return output.getvalue()

    def export_reservations_csv(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> str:
        """Export reservations data to CSV format.

        Generates a CSV-formatted string containing detailed reservation
        records including resource and user information. This provides
        a complete audit trail of booking activity.

        Args:
            start_date: The beginning of the export period. If None,
                defaults to 30 days before the current time.
            end_date: The end of the export period. If None, defaults
                to the current time.

        Returns:
            A CSV-formatted string with headers and data rows. The columns
            are: reservation_id, resource_name, username, start_time,
            end_time, status, and created_at. Missing relationships
            (resource or user) are represented as 'N/A'.

        Example:
            >>> analytics = AnalyticsService(db)
            >>> csv_content = analytics.export_reservations_csv(
            ...     start_date=datetime(2024, 1, 1, tzinfo=UTC),
            ...     end_date=datetime(2024, 1, 31, tzinfo=UTC)
            ... )
            >>> with open('january_reservations.csv', 'w') as f:
            ...     f.write(csv_content)
        """
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(UTC)

        reservations = (
            self.db.query(models.Reservation)
            .join(models.Resource)
            .join(models.User)
            .filter(
                models.Reservation.created_at >= start_date,
                models.Reservation.created_at < end_date,
            )
            .all()
        )

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "reservation_id",
                "resource_name",
                "username",
                "start_time",
                "end_time",
                "status",
                "created_at",
            ]
        )

        for res in reservations:
            writer.writerow(
                [
                    res.id,
                    res.resource.name if res.resource else "N/A",
                    res.user.username if res.user else "N/A",
                    res.start_time.isoformat(),
                    res.end_time.isoformat(),
                    res.status,
                    res.created_at.isoformat() if res.created_at else "N/A",
                ]
            )

        return output.getvalue()
