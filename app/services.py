# app/services.py - Updated with timezone-aware datetime handling

"""Business logic layer with clear separation of concerns."""

import base64
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import hash_password


def ensure_timezone_aware(dt):
    """Ensure datetime is timezone-aware (convert to UTC if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If naive, assume it's UTC
        return dt.replace(tzinfo=UTC)
    return dt


def utcnow():
    """Get current UTC datetime that's timezone-aware."""
    return datetime.now(UTC)


def _encode_cursor(sort_value: Any, record_id: int) -> str:
    if isinstance(sort_value, datetime):
        sort_value = sort_value.isoformat()
    payload = {"v": sort_value, "id": record_id}
    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode_cursor(cursor: str) -> tuple[Any, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        payload = json.loads(raw)
        return payload["v"], int(payload["id"])
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid cursor") from exc


def _paginate_items(
    items: list[Any],
    sort_key: Callable[[Any], Any],
    sort_order: str,
    limit: int,
    cursor: str | None,
    value_parser: Callable[[Any], Any] | None = None,
) -> tuple[list[Any], str | None, bool]:
    reverse = sort_order == "desc"
    sorted_items = sorted(
        items, key=lambda item: (sort_key(item), item.id), reverse=reverse
    )

    if cursor:
        cursor_value_raw, cursor_id = _decode_cursor(cursor)
        cursor_value = (
            value_parser(cursor_value_raw) if value_parser else cursor_value_raw
        )

        def is_after(item: Any) -> bool:
            value = sort_key(item)
            if reverse:
                return value < cursor_value or (
                    value == cursor_value and item.id < cursor_id
                )
            return value > cursor_value or (
                value == cursor_value and item.id > cursor_id
            )

        sorted_items = [item for item in sorted_items if is_after(item)]

    page_items = sorted_items[:limit]
    has_more = len(sorted_items) > limit
    next_cursor = (
        _encode_cursor(sort_key(page_items[-1]), page_items[-1].id)
        if has_more and page_items
        else None
    )
    return page_items, next_cursor, has_more


class ResourceService:
    """Service for resource management operations with dynamic availability."""

    def __init__(self, db: Session):
        self.db = db

    def create_resource(self, resource_data: schemas.ResourceCreate) -> models.Resource:
        # Validate input data
        if not resource_data.name or not resource_data.name.strip():
            raise ValueError("Resource name cannot be empty")

        # Sanitize name
        name = resource_data.name.strip()[:200]  # Limit length

        resource = models.Resource(
            name=name,
            available=resource_data.available,
            tags=resource_data.tags or [],
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.db.add(resource)
                self.db.commit()
                self.db.refresh(resource)
                return resource
            except IntegrityError as e:
                self.db.rollback()
                if attempt == max_retries - 1:
                    raise ValueError(f"Resource '{name}' already exists.") from e
                # On retry, check if it was created by another process
                existing = (
                    self.db.query(models.Resource)
                    .filter(models.Resource.name == name)
                    .first()
                )
                if existing:
                    raise ValueError(f"Resource '{name}' already exists.") from e
            except Exception as e:
                self.db.rollback()
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to create resource: {str(e)}") from e
                # Wait a bit before retry
                import time

                time.sleep(0.1 * (attempt + 1))

    def get_all_resources(self) -> list[models.Resource]:
        """Get all resources with real-time availability status."""
        resources = self.db.query(models.Resource).all()

        # Add current availability as a computed field (read-only)
        for resource in resources:
            resource.current_availability = self._is_resource_currently_available(
                resource.id
            )

        return resources

    def search_resources(
        self,
        query: str = None,
        status_filter: str = "available",
        available_from: datetime = None,
        available_until: datetime = None,
        tags: list[str] | None = None,
    ) -> list[models.Resource]:
        """Search resources with optional time-based filtering and real-time availability."""  # noqa

        # Ensure timezone awareness for datetime parameters
        if available_from:
            available_from = ensure_timezone_aware(available_from)
        if available_until:
            available_until = ensure_timezone_aware(available_until)

        # If time period specified, filter out booked resources
        if available_from and available_until:
            available_resources = []

            # Get all resources that are not permanently disabled
            resources = (
                self.db.query(models.Resource)
                .filter(models.Resource.available)  # Only include enabled resources
                .all()
            )

            for resource in resources:
                if status_filter != "all":
                    if status_filter == "available" and not resource.available:
                        continue
                    if status_filter == "unavailable" and resource.available:
                        continue
                    if status_filter == "in_use" and resource.status != "in_use":
                        continue

                if tags:
                    tag_set = {tag.lower() for tag in tags}
                    resource_tags = {tag.lower() for tag in (resource.tags or [])}
                    if not tag_set.intersection(resource_tags):
                        continue

                if not self._has_conflict(resource.id, available_from, available_until):
                    # Set current availability for time-based search
                    resource.current_availability = True
                    available_resources.append(resource)

            # Apply text search if provided
            if query:
                query_lower = query.lower()
                available_resources = [
                    r for r in available_resources if query_lower in r.name.lower()
                ]

            return available_resources

        # Regular search without time filtering
        db_query = self.db.query(models.Resource)

        # Get base resources
        resources = db_query.all()

        # Filter resources without changing their status
        filtered_resources = []
        for resource in resources:
            # Apply status filter (use existing status, don't update it)
            if status_filter != "all":
                if status_filter == "available" and not resource.available:
                    continue
                if status_filter == "unavailable" and resource.available:
                    continue
                if status_filter == "in_use" and resource.status != "in_use":
                    continue

            if tags:
                tag_set = {tag.lower() for tag in tags}
                resource_tags = {tag.lower() for tag in (resource.tags or [])}
                if not tag_set.intersection(resource_tags):
                    continue

            # Apply text search filter
            if query:
                query_lower = query.lower()
                if not (
                    query_lower in resource.name.lower()
                    or any(query_lower in tag.lower() for tag in resource.tags)
                ):
                    continue

            # Set current availability for response (read-only check)
            resource.current_availability = self._is_resource_currently_available(
                resource.id
            )
            filtered_resources.append(resource)

        return filtered_resources

    def get_resources_paginated(
        self,
        pagination: schemas.PaginationParams,
        query: str | None = None,
        status_filter: str = "all",
        available_from: datetime | None = None,
        available_until: datetime | None = None,
        tags: list[str] | None = None,
        include_total: bool = False,
    ) -> tuple[list[models.Resource], str | None, bool, int | None]:
        resources = self.search_resources(
            query=query,
            status_filter=status_filter,
            available_from=available_from,
            available_until=available_until,
            tags=tags,
        )

        total_count = len(resources) if include_total else None
        sort_by = pagination.sort_by or "name"
        sort_order = (pagination.sort_order or "asc").lower()

        sort_options = {
            "id": lambda r: r.id,
            "name": lambda r: r.name.lower(),
            "status": lambda r: r.status,
            "created_at": lambda r: r.id,
        }

        if sort_order not in {"asc", "desc"}:
            raise ValueError("Invalid sort_order. Must be 'asc' or 'desc'.")
        if sort_by not in sort_options:
            raise ValueError(
                "Invalid sort_by. Must be one of: id, name, status, created_at."
            )

        page_items, next_cursor, has_more = _paginate_items(
            resources,
            sort_key=sort_options[sort_by],
            sort_order=sort_order,
            limit=pagination.limit,
            cursor=pagination.cursor,
        )

        return page_items, next_cursor, has_more, total_count


class NotificationService:
    """Service for user notifications."""

    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        user_id: int,
        type: schemas.NotificationType,
        title: str,
        message: str,
        link: str | None = None,
    ) -> models.Notification:
        type_value = type.value if hasattr(type, "value") else str(type)
        notification = models.Notification(
            user_id=user_id,
            type=type_value,
            title=title,
            message=message,
            link=link,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def list_notifications(
        self,
        user_id: int,
        pagination: schemas.PaginationParams,
        include_total: bool = False,
    ) -> tuple[list[models.Notification], str | None, bool, int | None]:
        notifications = (
            self.db.query(models.Notification)
            .filter(models.Notification.user_id == user_id)
            .all()
        )

        total_count = len(notifications) if include_total else None
        sort_by = pagination.sort_by or "created_at"
        sort_order = (pagination.sort_order or "desc").lower()

        sort_options = {
            "id": lambda n: n.id,
            "created_at": lambda n: ensure_timezone_aware(n.created_at),
            "type": lambda n: n.type,
            "read": lambda n: n.read,
        }

        if sort_order not in {"asc", "desc"}:
            raise ValueError("Invalid sort_order. Must be 'asc' or 'desc'.")
        if sort_by not in sort_options:
            raise ValueError(
                "Invalid sort_by. Must be one of: id, created_at, type, read."
            )

        def parse_datetime(value: Any) -> datetime:
            if isinstance(value, datetime):
                return value
            try:
                return ensure_timezone_aware(datetime.fromisoformat(str(value)))
            except ValueError as exc:
                raise ValueError("Invalid cursor value") from exc

        value_parser = parse_datetime if sort_by == "created_at" else None

        page_items, next_cursor, has_more = _paginate_items(
            notifications,
            sort_key=sort_options[sort_by],
            sort_order=sort_order,
            limit=pagination.limit,
            cursor=pagination.cursor,
            value_parser=value_parser,
        )

        return page_items, next_cursor, has_more, total_count

    def mark_as_read(self, notification_id: int, user_id: int) -> models.Notification:
        notification = (
            self.db.query(models.Notification)
            .filter(
                models.Notification.id == notification_id,
                models.Notification.user_id == user_id,
            )
            .first()
        )
        if not notification:
            raise ValueError("Notification not found")

        if not notification.read:
            notification.read = True
            self.db.commit()
            self.db.refresh(notification)

        return notification

    def mark_all_as_read(self, user_id: int) -> int:
        updated_count = (
            self.db.query(models.Notification)
            .filter(
                models.Notification.user_id == user_id,
                models.Notification.read.is_(False),
            )
            .update({models.Notification.read: True}, synchronize_session=False)
        )
        self.db.commit()
        return updated_count

    def _is_resource_currently_available(self, resource_id: int) -> bool:
        """Check if a resource is currently available (not in an active reservation)."""
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            return False

        # DO NOT update resource status here to avoid unwanted status resets
        # Just check current status

        # Resource is available if:
        # 1. It's not disabled (base available = True)
        # 2. It's not unavailable for maintenance
        # 3. It's not currently in use
        return resource.available and resource.status == "available"

    def _update_resource_status(self, resource: models.Resource):
        """Update resource status based on current reservations and auto-reset logic."""
        now = utcnow()

        # Check if resource should be auto-reset from unavailable
        if resource.should_auto_reset():
            resource.set_available()
            return

        # If resource is manually disabled, don't change status
        if not resource.available:
            return

        # Check if resource has any active reservations right now
        current_reservation = (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.resource_id == resource.id,
                models.Reservation.status == "active",
                models.Reservation.start_time <= now,
                models.Reservation.end_time > now,
            )
            .first()
        )

        # Update status based on reservation state
        if current_reservation:
            # Only change to in_use if not in maintenance mode
            if resource.status != "unavailable" and resource.status != "in_use":
                resource.set_in_use()
        else:
            # No active reservation, set to available only if currently in_use
            # DO NOT change unavailable (maintenance) status
            if resource.status == "in_use":
                resource.set_available()

    def _has_conflict(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> bool:
        """Check if resource has conflicting reservations during specified time period."""  # noqa
        # Ensure timezone awareness
        start_time = ensure_timezone_aware(start_time)
        end_time = ensure_timezone_aware(end_time)

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

        return conflict is not None

    def update_resource_availability(
        self, resource_id: int, available: bool
    ) -> models.Resource:
        """Manually update resource base availability (for maintenance, etc.)."""
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            raise ValueError("Resource not found")

        resource.available = available
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def set_resource_unavailable(
        self, resource_id: int, auto_reset_hours: int = 8
    ) -> models.Resource:
        """Set a resource as unavailable for maintenance/repair."""
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            raise ValueError("Resource not found")

        resource.set_unavailable(auto_reset_hours)
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def reset_resource_to_available(self, resource_id: int) -> models.Resource:
        """Reset a resource to available status."""
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            raise ValueError("Resource not found")

        resource.set_available()
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def get_resource_status(self, resource_id: int) -> dict:
        """Get detailed status information for a resource."""
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            raise ValueError("Resource not found")

        # Only update status when explicitly requested for status details
        # This is appropriate since the user is asking for current status info
        self._update_resource_status(resource)

        now = utcnow()
        current_reservation = (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.start_time <= now,
                models.Reservation.end_time > now,
            )
            .first()
        )

        status_info = {
            "resource_id": resource_id,
            "resource_name": resource.name,
            "base_available": resource.available,
            "status": resource.status,
            "is_available_for_reservation": resource.is_available_for_reservation,
            "is_currently_in_use": resource.is_currently_in_use,
            "is_unavailable": resource.is_unavailable,
            "current_time": now.isoformat(),
        }

        if resource.status == "unavailable" and resource.unavailable_since:
            hours_unavailable = (
                now - resource.unavailable_since
            ).total_seconds() / 3600
            hours_until_reset = max(0, resource.auto_reset_hours - hours_unavailable)

            status_info.update(
                {
                    "unavailable_since": resource.unavailable_since.isoformat(),
                    "auto_reset_hours": resource.auto_reset_hours,
                    "hours_unavailable": round(hours_unavailable, 2),
                    "hours_until_auto_reset": round(hours_until_reset, 2),
                    "will_auto_reset": hours_until_reset > 0,
                }
            )

        if current_reservation:
            status_info["current_reservation"] = {
                "id": current_reservation.id,
                "start_time": current_reservation.start_time.isoformat(),
                "end_time": current_reservation.end_time.isoformat(),
                "user_id": current_reservation.user_id,
            }

        return status_info

    def get_resource_schedule(self, resource_id: int, days_ahead: int = 7) -> list:
        """Get existing reservations for a resource over the next specified days,
        including any reservations since 12:00 AM today."""
        now = utcnow()
        start_of_today = datetime.combine(now.date(), datetime.min.time(), tzinfo=UTC)
        end_date = now + timedelta(days=days_ahead)

        # Get the resource
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            raise ValueError("Resource not found")

        # Get all reservations for this resource in the time period
        reservations = (
            self.db.query(models.Reservation, models.User.username)
            .join(models.User, models.Reservation.user_id == models.User.id)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.start_time < end_date,
                models.Reservation.end_time > start_of_today,
            )
            .order_by(models.Reservation.start_time)
            .all()
        )

        schedule = {
            "success": True,
            "data": {
                "resource_id": resource_id,
                "resource_name": resource.name,
                "current_time": now.isoformat(),
                "is_currently_available": self._is_resource_currently_available(
                    resource_id
                ),
                "base_available": resource.available,
                "reservations": [
                    {
                        "id": res.id,
                        "start_time": res.start_time.replace(tzinfo=UTC).isoformat(),
                        "end_time": res.end_time.replace(tzinfo=UTC).isoformat(),
                        "user_id": res.user_id,
                        "user_name": user_name,
                        "status": res.status,
                    }
                    for res, user_name in reservations
                ],
            },
        }
        return schedule


class ReservationService:
    """Service for reservation management operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_reservation(
        self, reservation_data: schemas.ReservationCreate, user_id: int
    ) -> models.Reservation:
        """Create a new reservation with conflict validation and retry logic."""

        # Validate input data
        if not reservation_data.start_time or not reservation_data.end_time:
            raise ValueError("Start time and end time are required")

        # Ensure timezone awareness
        start_time = ensure_timezone_aware(reservation_data.start_time)
        end_time = ensure_timezone_aware(reservation_data.end_time)

        # Validate time range
        if end_time <= start_time:
            raise ValueError("End time must be after start time")

        now = utcnow()
        if start_time <= now:
            raise ValueError("Cannot create reservations in the past")

        # Validate reservation duration (max 24 hours)
        duration = end_time - start_time
        if duration.total_seconds() > 24 * 3600:
            raise ValueError("Reservations cannot exceed 24 hours")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Validate resource exists and is available (check each time for concurrent updates)  # noqa
                resource = (
                    self.db.query(models.Resource)
                    .filter(models.Resource.id == reservation_data.resource_id)
                    .first()
                )

                if not resource:
                    raise ValueError("Resource not found")

                if not resource.available:
                    raise ValueError("Resource is not available for reservations")

                # Check for conflicts with latest data
                conflicts = self._get_conflicts(
                    reservation_data.resource_id,
                    start_time,
                    end_time,
                )

                if conflicts:
                    conflict_times = []
                    for conflict in conflicts:
                        conflict_times.append(
                            f"{conflict.start_time.strftime('%H:%M')} to "
                            f"{conflict.end_time.strftime('%H:%M')}"
                        )
                    raise ValueError(
                        f"Time slot conflicts with existing reservations: "
                        f"{', '.join(conflict_times)}"
                    )

                # Create reservation
                reservation = models.Reservation(
                    user_id=user_id,
                    resource_id=reservation_data.resource_id,
                    start_time=start_time,
                    end_time=end_time,
                    status="active",
                )

                self.db.add(reservation)
                self.db.commit()
                self.db.refresh(reservation)

                # Log the action
                self._log_action(
                    reservation.id,
                    "created",
                    user_id,
                    f"Reserved {resource.name} from {start_time} to {end_time}",
                )

                # Notify user
                NotificationService(self.db).create_notification(
                    user_id=user_id,
                    type=schemas.NotificationType.RESERVATION_CONFIRMED,
                    title="Reservation confirmed",
                    message=(
                        f"{resource.name} booked from "
                        f"{start_time.isoformat()} to {end_time.isoformat()}"
                    ),
                    link=f"/reservations/{reservation.id}",
                )

                return reservation

            except IntegrityError as e:
                self.db.rollback()
                if attempt == max_retries - 1:
                    raise ValueError(
                        "Failed to create reservation due to conflicts. "
                        "Please try again."
                    ) from e
                # Wait before retry
                import time

                time.sleep(0.1 * (attempt + 1))
            except Exception:
                self.db.rollback()
                if attempt == max_retries - 1:
                    raise
                # Wait before retry for other exceptions too
                import time

                time.sleep(0.1 * (attempt + 1))

    def cancel_reservation(
        self,
        reservation_id: int,
        cancellation: schemas.ReservationCancel,
        user_id: int,
    ) -> models.Reservation:
        """Cancel a reservation."""
        reservation = (
            self.db.query(models.Reservation)
            .filter(models.Reservation.id == reservation_id)
            .first()
        )

        if not reservation:
            raise ValueError("Reservation not found")

        if reservation.user_id != user_id:
            raise ValueError("You can only cancel your own reservations")

        if reservation.status == "cancelled":
            raise ValueError("Reservation is already cancelled")

        # Update reservation
        reservation.status = "cancelled"
        reservation.cancelled_at = utcnow()
        reservation.cancellation_reason = cancellation.reason

        self.db.commit()
        self.db.refresh(reservation)

        # Log the action
        reason_text = f" (Reason: {cancellation.reason})" if cancellation.reason else ""
        self._log_action(
            reservation_id,
            "cancelled",
            user_id,
            f"Cancelled reservation{reason_text}",
        )

        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == reservation.resource_id)
            .first()
        )

        NotificationService(self.db).create_notification(
            user_id=user_id,
            type=schemas.NotificationType.RESERVATION_CANCELLED,
            title="Reservation cancelled",
            message=f"Reservation for {resource.name if resource else 'resource'} was cancelled.",
            link=f"/reservations/{reservation.id}",
        )

        return reservation

    def get_user_reservations(
        self, user_id: int, include_cancelled: bool = False
    ) -> list[models.Reservation]:
        """Get reservations for a specific user."""
        query = (
            self.db.query(models.Reservation)
            .options(joinedload(models.Reservation.resource))
            .filter(models.Reservation.user_id == user_id)
        )

        if not include_cancelled:
            query = query.filter(models.Reservation.status == "active")

        return query.order_by(models.Reservation.start_time.desc()).all()

    def get_user_reservations_paginated(
        self,
        user_id: int,
        include_cancelled: bool,
        pagination: schemas.PaginationParams,
        include_total: bool = False,
    ) -> tuple[list[models.Reservation], str | None, bool, int | None]:
        reservations = self.get_user_reservations(user_id, include_cancelled)
        total_count = len(reservations) if include_total else None

        sort_by = pagination.sort_by or "start_time"
        sort_order = (pagination.sort_order or "desc").lower()

        sort_options = {
            "id": lambda r: r.id,
            "start_time": lambda r: ensure_timezone_aware(r.start_time),
            "end_time": lambda r: ensure_timezone_aware(r.end_time),
            "created_at": lambda r: ensure_timezone_aware(r.created_at),
        }

        if sort_order not in {"asc", "desc"}:
            raise ValueError("Invalid sort_order. Must be 'asc' or 'desc'.")
        if sort_by not in sort_options:
            raise ValueError(
                "Invalid sort_by. Must be one of: id, start_time, end_time, created_at."
            )

        def parse_datetime(value: Any) -> datetime:
            if isinstance(value, datetime):
                return value
            try:
                return ensure_timezone_aware(datetime.fromisoformat(str(value)))
            except ValueError as exc:
                raise ValueError("Invalid cursor value") from exc

        value_parser = (
            parse_datetime
            if sort_by in {"start_time", "end_time", "created_at"}
            else None
        )

        page_items, next_cursor, has_more = _paginate_items(
            reservations,
            sort_key=sort_options[sort_by],
            sort_order=sort_order,
            limit=pagination.limit,
            cursor=pagination.cursor,
            value_parser=value_parser,
        )

        return page_items, next_cursor, has_more, total_count

    def get_reservation_history(
        self, reservation_id: int
    ) -> list[models.ReservationHistory]:
        """Get history for a specific reservation."""
        return (
            self.db.query(models.ReservationHistory)
            .filter(models.ReservationHistory.reservation_id == reservation_id)
            .order_by(models.ReservationHistory.timestamp.desc())
            .all()
        )

    def _get_conflicts(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> list[models.Reservation]:
        """Get all conflicting reservations for a time slot."""
        # Ensure timezone awareness
        start_time = ensure_timezone_aware(start_time)
        end_time = ensure_timezone_aware(end_time)

        return (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.end_time > start_time,
                models.Reservation.start_time < end_time,
            )
            .all()
        )

    def _log_action(self, reservation_id: int, action: str, user_id: int, details: str):
        """Log a reservation action for audit trail."""
        history = models.ReservationHistory(
            reservation_id=reservation_id,
            action=action,
            user_id=user_id,
            details=details,
        )
        self.db.add(history)
        self.db.commit()


class UserService:
    """Service for user management operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_data: schemas.UserCreate) -> models.User:
        """Create a new user with hashed password."""
        existing_users = self.db.query(models.User).count()
        setup_complete = None
        setup_reopened = None
        if existing_users == 0:
            from app import setup

            setup_complete, setup_reopened = setup.get_setup_status(self.db)

        hashed_password = hash_password(user_data.password)
        user = models.User(username=user_data.username, hashed_password=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        if existing_users == 0 and setup_complete is False and setup_reopened is False:
            from app import rbac, setup

            rbac.create_default_roles(self.db)
            rbac.assign_role(user.id, "admin", self.db)
            setup.mark_setup_complete(self.db)

        return user

    def get_user_by_username(self, username: str) -> models.User | None:
        """Get user by username (case-insensitive)."""
        # Normalize username to lowercase for case-insensitive search
        normalized_username = username.lower()
        return (
            self.db.query(models.User)
            .filter(models.User.username == normalized_username)
            .first()
        )
