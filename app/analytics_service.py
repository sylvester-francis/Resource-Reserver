"""Analytics service for resource utilization insights.

Provides functionality for:
- Resource utilization metrics
- Popular resources ranking
- Peak usage times analysis
- User booking patterns
- Exportable reports

Author: Sylvester-Francis
"""

import csv
from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models


class AnalyticsService:
    """Service for generating analytics and reports."""

    def __init__(self, db: Session):
        self.db = db

    def get_resource_utilization(
        self,
        resource_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Calculate resource utilization percentage.

        Args:
            resource_id: Optional specific resource ID
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            List of resource utilization data
        """
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(UTC)
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
        """Get most popular resources by reservation count.

        Args:
            limit: Maximum number of resources to return
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            List of popular resources with booking counts
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
        """Analyze peak usage times by hour and day of week.

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            Peak usage analysis data
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

        Args:
            user_id: Optional specific user ID
            limit: Maximum number of users to return
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            List of user booking statistics
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
        """Get a summary of all analytics for the dashboard.

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            Complete analytics summary
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

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            CSV string
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

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            CSV string
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
