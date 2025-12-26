"""Bulk operations service for reservations.

Provides functionality for:
- Bulk create reservations
- Bulk cancel reservations
- CSV import with validation
- Dry-run mode for validation

Author: Sylvester-Francis
"""

import csv
import logging
from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import Any

from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)


def utcnow():
    """Get current UTC datetime that's timezone-aware."""
    return datetime.now(UTC)


def ensure_timezone_aware(dt):
    """Ensure datetime is timezone-aware (convert to UTC if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class BulkReservationService:
    """Service for bulk reservation operations."""

    def __init__(self, db: Session):
        self.db = db

    def bulk_create_reservations(
        self,
        reservations_data: list[dict],
        user_id: int,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Create multiple reservations in bulk.

        Args:
            reservations_data: List of reservation data dicts with keys:
                - resource_id: int
                - start_time: datetime or ISO string
                - end_time: datetime or ISO string
            user_id: ID of user creating reservations
            dry_run: If True, validate only without creating

        Returns:
            Dict with results summary
        """
        results = {
            "total": len(reservations_data),
            "success": 0,
            "failed": 0,
            "dry_run": dry_run,
            "created": [],
            "errors": [],
        }

        # Validate user exists
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            results["errors"].append({"index": -1, "error": "User not found"})
            return results

        now = utcnow()

        for idx, data in enumerate(reservations_data):
            try:
                # Parse and validate times
                start_time = self._parse_datetime(data.get("start_time"))
                end_time = self._parse_datetime(data.get("end_time"))
                resource_id = data.get("resource_id")

                # Validate required fields
                if not resource_id:
                    raise ValueError("resource_id is required")
                if not start_time:
                    raise ValueError("start_time is required")
                if not end_time:
                    raise ValueError("end_time is required")

                # Ensure timezone awareness
                start_time = ensure_timezone_aware(start_time)
                end_time = ensure_timezone_aware(end_time)

                # Validate time range
                if start_time <= now:
                    raise ValueError("start_time must be in the future")
                if end_time <= start_time:
                    raise ValueError("end_time must be after start_time")

                # Check duration limits
                duration = end_time - start_time
                if duration > timedelta(days=7):
                    raise ValueError("Reservation cannot exceed 7 days")
                if duration < timedelta(minutes=15):
                    raise ValueError("Reservation must be at least 15 minutes")

                # Validate resource exists and is available
                resource = (
                    self.db.query(models.Resource)
                    .filter(models.Resource.id == resource_id)
                    .first()
                )
                if not resource:
                    raise ValueError(f"Resource {resource_id} not found")
                if not resource.available:
                    raise ValueError(f"Resource {resource.name} is not available")

                # Check for conflicts
                conflict = (
                    self.db.query(models.Reservation)
                    .filter(
                        models.Reservation.resource_id == resource_id,
                        models.Reservation.status == "active",
                        models.Reservation.end_time > start_time,
                        models.Reservation.start_time < end_time,
                    )
                    .first()
                )
                if conflict:
                    raise ValueError(
                        f"Time slot conflicts with existing reservation {conflict.id}"
                    )

                # Create reservation if not dry run
                if not dry_run:
                    reservation = models.Reservation(
                        user_id=user_id,
                        resource_id=resource_id,
                        start_time=start_time,
                        end_time=end_time,
                        status="active",
                    )
                    self.db.add(reservation)
                    self.db.flush()  # Get ID without committing

                    results["created"].append(
                        {
                            "index": idx,
                            "reservation_id": reservation.id,
                            "resource_name": resource.name,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                        }
                    )
                else:
                    results["created"].append(
                        {
                            "index": idx,
                            "resource_name": resource.name,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                            "would_create": True,
                        }
                    )

                results["success"] += 1

            except (ValueError, TypeError) as e:
                results["failed"] += 1
                results["errors"].append(
                    {
                        "index": idx,
                        "data": data,
                        "error": str(e),
                    }
                )

        # Commit if not dry run and no errors
        if not dry_run and results["failed"] == 0:
            self.db.commit()
        elif not dry_run:
            # Rollback if any errors
            self.db.rollback()
            results["created"] = []
            results["success"] = 0
            results["message"] = "All operations rolled back due to errors"

        return results

    def bulk_cancel_reservations(
        self,
        reservation_ids: list[int],
        user_id: int,
        reason: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Cancel multiple reservations in bulk.

        Args:
            reservation_ids: List of reservation IDs to cancel
            user_id: ID of user cancelling
            reason: Cancellation reason
            force: If True, cancel even if not owned by user (admin only)

        Returns:
            Dict with results summary
        """
        results = {
            "total": len(reservation_ids),
            "success": 0,
            "failed": 0,
            "cancelled": [],
            "errors": [],
        }

        now = utcnow()

        for reservation_id in reservation_ids:
            try:
                reservation = (
                    self.db.query(models.Reservation)
                    .filter(models.Reservation.id == reservation_id)
                    .first()
                )

                if not reservation:
                    raise ValueError(f"Reservation {reservation_id} not found")

                if not force and reservation.user_id != user_id:
                    raise ValueError("Cannot cancel reservations owned by other users")

                if reservation.status == "cancelled":
                    raise ValueError("Reservation is already cancelled")

                # Cancel the reservation
                reservation.status = "cancelled"
                reservation.cancelled_at = now
                reservation.cancellation_reason = reason

                results["cancelled"].append(
                    {
                        "reservation_id": reservation_id,
                        "resource_id": reservation.resource_id,
                    }
                )
                results["success"] += 1

            except ValueError as e:
                results["failed"] += 1
                results["errors"].append(
                    {
                        "reservation_id": reservation_id,
                        "error": str(e),
                    }
                )

        self.db.commit()
        return results

    def import_from_csv(
        self,
        csv_content: str,
        user_id: int,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Import reservations from CSV content.

        Expected CSV columns:
        - resource_id or resource_name
        - start_time (ISO format or YYYY-MM-DD HH:MM)
        - end_time (ISO format or YYYY-MM-DD HH:MM)

        Args:
            csv_content: CSV file content as string
            user_id: ID of user importing
            dry_run: If True, validate only

        Returns:
            Dict with import results
        """
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "dry_run": dry_run,
            "created": [],
            "errors": [],
        }

        try:
            reader = csv.DictReader(StringIO(csv_content))
            reservations_data = []

            for row_num, row in enumerate(reader, start=1):
                results["total"] += 1

                # Handle resource lookup
                resource_id = row.get("resource_id")
                resource_name = row.get("resource_name")

                if not resource_id and resource_name:
                    # Look up by name
                    resource = (
                        self.db.query(models.Resource)
                        .filter(models.Resource.name == resource_name)
                        .first()
                    )
                    if resource:
                        resource_id = resource.id
                    else:
                        results["failed"] += 1
                        results["errors"].append(
                            {
                                "row": row_num,
                                "error": f"Resource '{resource_name}' not found",
                            }
                        )
                        continue

                try:
                    resource_id = int(resource_id)
                except (ValueError, TypeError):
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "row": row_num,
                            "error": "Invalid resource_id",
                        }
                    )
                    continue

                reservations_data.append(
                    {
                        "resource_id": resource_id,
                        "start_time": row.get("start_time"),
                        "end_time": row.get("end_time"),
                        "row_number": row_num,
                    }
                )

            # Process reservations
            bulk_results = self.bulk_create_reservations(
                reservations_data, user_id, dry_run
            )

            # Merge results
            results["success"] = bulk_results["success"]
            results["created"] = bulk_results["created"]

            # Add row numbers to errors
            for error in bulk_results["errors"]:
                idx = error.get("index", 0)
                if idx >= 0 and idx < len(reservations_data):
                    error["row"] = reservations_data[idx].get("row_number", idx + 1)
                results["errors"].append(error)
                results["failed"] += 1

        except csv.Error as e:
            results["errors"].append(
                {
                    "row": -1,
                    "error": f"CSV parsing error: {str(e)}",
                }
            )

        return results

    def export_to_csv(
        self,
        user_id: int | None = None,
        resource_id: int | None = None,
        start_from: datetime | None = None,
        start_until: datetime | None = None,
        status: str | None = None,
    ) -> str:
        """Export reservations to CSV format.

        Args:
            user_id: Filter by user
            resource_id: Filter by resource
            start_from: Filter by start time (from)
            start_until: Filter by start time (until)
            status: Filter by status

        Returns:
            CSV content as string
        """
        query = (
            self.db.query(models.Reservation).join(models.Resource).join(models.User)
        )

        if user_id is not None:
            query = query.filter(models.Reservation.user_id == user_id)

        if resource_id is not None:
            query = query.filter(models.Reservation.resource_id == resource_id)

        if status:
            query = query.filter(models.Reservation.status == status)

        if start_from:
            start_from = ensure_timezone_aware(start_from)
            query = query.filter(models.Reservation.start_time >= start_from)

        if start_until:
            start_until = ensure_timezone_aware(start_until)
            query = query.filter(models.Reservation.start_time <= start_until)

        reservations = query.order_by(models.Reservation.start_time).all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "reservation_id",
                "resource_id",
                "resource_name",
                "user_id",
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
                    res.resource_id,
                    res.resource.name if res.resource else "N/A",
                    res.user_id,
                    res.user.username if res.user else "N/A",
                    res.start_time.isoformat(),
                    res.end_time.isoformat(),
                    res.status,
                    res.created_at.isoformat() if res.created_at else "N/A",
                ]
            )

        return output.getvalue()

    def _parse_datetime(self, value: Any) -> datetime | None:
        """Parse datetime from various formats."""
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            # Try ISO format first
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

            # Try common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

            raise ValueError(f"Cannot parse datetime: {value}")

        raise ValueError(f"Invalid datetime type: {type(value)}")
