# app/services.py - Updated with timezone-aware datetime handling

"""Business logic layer for the Resource Reserver application.

This module provides the core service classes that implement business logic
for resource management, reservations, notifications, user management, and
waitlist operations. It maintains a clear separation of concerns between
the API layer and data access layer.

Features:
    - Resource management with real-time availability tracking
    - Reservation creation with conflict detection and validation
    - Recurring reservation support with customizable recurrence rules
    - Notification system for user alerts and updates
    - Waitlist management with automatic slot offering
    - Cursor-based pagination for efficient data retrieval
    - Timezone-aware datetime handling throughout

Example:
    Basic usage of the ResourceService::

        from sqlalchemy.orm import Session
        from app.services import ResourceService, ReservationService
        from app import schemas

        # Create a new resource
        resource_service = ResourceService(db_session)
        resource_data = schemas.ResourceCreate(name="Conference Room A")
        resource = resource_service.create_resource(resource_data)

        # Create a reservation
        reservation_service = ReservationService(db_session)
        reservation_data = schemas.ReservationCreate(
            resource_id=resource.id,
            start_time=datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
            end_time=datetime(2024, 1, 15, 10, 0, tzinfo=UTC),
        )
        reservation = reservation_service.create_reservation(reservation_data, user_id=1)

Author:
    Resource Reserver Development Team
"""

import base64
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import anyio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import hash_password
from app.core.cache import invalidate_resource_cache
from app.utils.recurrence import generate_occurrences
from app.websocket import manager as ws_manager

logger = logging.getLogger(__name__)


def _invalidate_cache_sync() -> None:
    """Invalidate the resource cache from a synchronous context.

    This is a wrapper function that runs the async cache invalidation
    function from a synchronous thread context using anyio.

    Note:
        Cache invalidation failures are logged but do not raise exceptions
        to prevent cache issues from affecting core functionality.
    """
    try:
        anyio.from_thread.run(invalidate_resource_cache)
        logger.debug("Resource cache invalidated")
    except Exception as e:
        logger.debug(f"Cache invalidation skipped: {e}")


def ensure_timezone_aware(dt: datetime | None) -> datetime | None:
    """Ensure a datetime object is timezone-aware.

    Converts naive datetime objects to UTC-aware datetimes. If the datetime
    already has timezone information, it is returned unchanged.

    Args:
        dt: A datetime object that may or may not be timezone-aware,
            or None.

    Returns:
        A timezone-aware datetime object with UTC timezone if the input
        was naive, the original datetime if already timezone-aware,
        or None if the input was None.

    Example:
        >>> from datetime import datetime, UTC
        >>> naive_dt = datetime(2024, 1, 15, 9, 0)
        >>> aware_dt = ensure_timezone_aware(naive_dt)
        >>> aware_dt.tzinfo
        datetime.timezone.utc
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If naive, assume it's UTC
        return dt.replace(tzinfo=UTC)
    return dt


def utcnow() -> datetime:
    """Get the current UTC datetime as a timezone-aware object.

    Returns:
        A timezone-aware datetime object representing the current time in UTC.

    Example:
        >>> now = utcnow()
        >>> now.tzinfo
        datetime.timezone.utc
    """
    return datetime.now(UTC)


def _encode_cursor(sort_value: Any, record_id: int) -> str:
    """Encode pagination cursor values into a URL-safe string.

    Creates a base64-encoded JSON string containing the sort value and
    record ID for cursor-based pagination.

    Args:
        sort_value: The value of the field being sorted on. If this is
            a datetime, it will be converted to ISO format string.
        record_id: The unique identifier of the record.

    Returns:
        A URL-safe base64-encoded string representing the cursor position.

    Example:
        >>> cursor = _encode_cursor("resource_name", 42)
        >>> isinstance(cursor, str)
        True
    """
    if isinstance(sort_value, datetime):
        sort_value = sort_value.isoformat()
    payload = {"v": sort_value, "id": record_id}
    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode_cursor(cursor: str) -> tuple[Any, int]:
    """Decode a pagination cursor string into its component values.

    Parses a base64-encoded cursor string and extracts the sort value
    and record ID.

    Args:
        cursor: A URL-safe base64-encoded cursor string created by
            _encode_cursor.

    Returns:
        A tuple containing (sort_value, record_id) extracted from the cursor.

    Raises:
        ValueError: If the cursor string is malformed, cannot be decoded,
            or contains invalid JSON.

    Example:
        >>> cursor = _encode_cursor("test_value", 123)
        >>> value, record_id = _decode_cursor(cursor)
        >>> record_id
        123
    """
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
    """Paginate a list of items using cursor-based pagination.

    Sorts the items according to the specified criteria and returns a page
    of results along with pagination metadata.

    Args:
        items: The complete list of items to paginate.
        sort_key: A callable that extracts the sort value from an item.
        sort_order: The sort direction, either "asc" or "desc".
        limit: The maximum number of items to return per page.
        cursor: An optional cursor string indicating where to start the page.
            If None, pagination starts from the beginning.
        value_parser: An optional callable to parse cursor values back to
            their original type (e.g., for datetime conversion).

    Returns:
        A tuple containing:
            - list: The items for the current page.
            - str | None: The cursor for the next page, or None if no more pages.
            - bool: Whether there are more items after this page.

    Example:
        >>> items = [obj1, obj2, obj3, obj4, obj5]
        >>> page, next_cursor, has_more = _paginate_items(
        ...     items, lambda x: x.name, "asc", limit=2, cursor=None
        ... )
        >>> len(page) <= 2
        True
    """
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
    """Service for resource management operations with dynamic availability.

    Provides methods for creating, retrieving, searching, and managing
    resources. Handles real-time availability tracking based on current
    reservations and supports maintenance mode with auto-reset functionality.

    Attributes:
        db: The SQLAlchemy database session for database operations.

    Example:
        >>> service = ResourceService(db_session)
        >>> resources = service.get_all_resources()
        >>> for resource in resources:
        ...     print(f"{resource.name}: {resource.status}")
    """

    def __init__(self, db: Session):
        """Initialize the ResourceService with a database session.

        Args:
            db: The SQLAlchemy database session to use for all operations.
        """
        self.db = db

    def create_resource(self, resource_data: schemas.ResourceCreate) -> models.Resource:
        """Create a new resource with retry logic for handling race conditions.

        Creates a resource with the specified name and availability settings.
        Implements retry logic to handle potential race conditions when
        multiple requests try to create resources simultaneously.

        Args:
            resource_data: The resource creation data containing name,
                availability status, and optional tags.

        Returns:
            The newly created Resource model instance.

        Raises:
            ValueError: If the resource name is empty, the resource already
                exists, or if creation fails after all retry attempts.

        Example:
            >>> data = schemas.ResourceCreate(name="Meeting Room 1", available=True)
            >>> resource = service.create_resource(data)
            >>> resource.name
            'Meeting Room 1'
        """
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
                _invalidate_cache_sync()  # Invalidate resource cache
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
        """Get all resources with real-time availability status.

        Retrieves all resources from the database and computes their
        current availability status based on active reservations.

        Returns:
            A list of all Resource model instances with current_availability
            attribute populated.

        Example:
            >>> resources = service.get_all_resources()
            >>> available = [r for r in resources if r.current_availability]
        """
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
        """Search resources with optional filtering and real-time availability.

        Searches for resources based on various criteria including name,
        availability status, time-based availability, and tags.

        Args:
            query: Optional text to search for in resource names.
            status_filter: Filter by status. Options are "all", "available",
                "unavailable", or "in_use". Defaults to "available".
            available_from: Optional start of time range for availability check.
            available_until: Optional end of time range for availability check.
            tags: Optional list of tags to filter by. Resources matching any
                of the provided tags will be included.

        Returns:
            A list of Resource model instances matching the search criteria,
            each with current_availability attribute populated.

        Example:
            >>> from datetime import datetime, timedelta, UTC
            >>> start = datetime.now(UTC) + timedelta(hours=1)
            >>> end = start + timedelta(hours=2)
            >>> available = service.search_resources(
            ...     query="conference",
            ...     available_from=start,
            ...     available_until=end,
            ...     tags=["large", "video"]
            ... )
        """
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
                    if not tag_set.issubset(resource_tags):
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
                if not tag_set.issubset(resource_tags):
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
            # Set current user name if resource is in use
            if resource.status == "in_use":
                resource.current_user_name = self._get_current_user_for_resource(
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
        """Get paginated resources with optional filtering.

        Combines search functionality with cursor-based pagination for
        efficient retrieval of large resource sets.

        Args:
            pagination: Pagination parameters including limit, cursor,
                sort_by, and sort_order.
            query: Optional text to search for in resource names.
            status_filter: Filter by status. Defaults to "all".
            available_from: Optional start of time range for availability check.
            available_until: Optional end of time range for availability check.
            tags: Optional list of tags to filter by.
            include_total: Whether to include total count in response.

        Returns:
            A tuple containing:
                - list: The resources for the current page.
                - str | None: The cursor for the next page.
                - bool: Whether there are more items.
                - int | None: Total count if include_total is True.

        Raises:
            ValueError: If sort_by or sort_order values are invalid.

        Example:
            >>> params = schemas.PaginationParams(limit=10, sort_by="name")
            >>> resources, cursor, has_more, total = service.get_resources_paginated(
            ...     params, query="room", include_total=True
            ... )
        """
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

    def _is_resource_currently_available(self, resource_id: int) -> bool:
        """Check if a resource is currently available for reservation.

        Determines availability based on the resource's base availability
        setting and whether it has any active reservations at the current time.

        Args:
            resource_id: The ID of the resource to check.

        Returns:
            True if the resource exists, is enabled, and has no active
            reservations at the current time. False otherwise.
        """
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            return False

        # Reuse status update logic so status and availability stay in sync
        self._update_resource_status(resource)
        return resource.available and resource.status == "available"

    def _get_current_user_for_resource(self, resource_id: int) -> str | None:
        """Get the username of who is currently using a resource.

        Checks for active reservations at the current time and returns
        the username of the user who has the reservation.

        Args:
            resource_id: The ID of the resource to check.

        Returns:
            The username of the current user if the resource is in use,
            None otherwise.
        """
        now = utcnow()
        current_reservation = (
            self.db.query(models.Reservation)
            .join(models.User)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.start_time <= now,
                models.Reservation.end_time > now,
            )
            .first()
        )

        if current_reservation:
            return current_reservation.user.username
        return None

    def _update_resource_status(self, resource: models.Resource) -> None:
        """Update resource status based on current reservations and auto-reset logic.

        Updates the resource status to reflect its current state based on
        active reservations and auto-reset timing for maintenance mode.

        Args:
            resource: The Resource model instance to update.

        Note:
            This method commits changes to the database if the status changes.
            It respects manual "unavailable" status and will not change it
            based on reservations.
        """
        now = utcnow()
        changed = False

        # Check if resource should be auto-reset from unavailable
        if resource.should_auto_reset():
            resource.set_available()
            changed = True

        # If resource is manually disabled, don't change status
        if not resource.available:
            if changed:
                self.db.commit()
                self.db.refresh(resource)
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
                changed = True
        else:
            # No active reservation, set to available only if currently in_use
            # DO NOT change unavailable (maintenance) status
            if resource.status == "in_use":
                resource.set_available()
                changed = True

        if changed:
            self.db.commit()
            self.db.refresh(resource)

    def _has_conflict(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> bool:
        """Check if resource has conflicting reservations during specified time period.

        Args:
            resource_id: The ID of the resource to check.
            start_time: The start of the time period to check.
            end_time: The end of the time period to check.

        Returns:
            True if there are any active reservations that overlap with
            the specified time period. False otherwise.
        """
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
        """Manually update resource base availability.

        Sets the resource's availability flag, typically used for
        maintenance or administrative purposes.

        Args:
            resource_id: The ID of the resource to update.
            available: The new availability status.

        Returns:
            The updated Resource model instance.

        Raises:
            ValueError: If the resource is not found.

        Note:
            This method broadcasts a WebSocket notification to all
            connected clients about the status change.
        """
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
        _invalidate_cache_sync()  # Invalidate resource cache

        anyio.from_thread.run(
            ws_manager.broadcast_all,
            {
                "type": "resource_status_changed",
                "resource_id": resource.id,
                "status": resource.status,
                "available": resource.available,
                "auto_reset_hours": resource.auto_reset_hours,
            },
        )
        return resource

    def update_resource(
        self, resource_id: int, update_data: schemas.ResourceUpdate
    ) -> models.Resource:
        """Update resource details (name, description, tags).

        Only admins should call this method. The resource must not be
        currently in use to be updated.

        Args:
            resource_id: The ID of the resource to update.
            update_data: The update data containing optional name,
                description, and tags fields.

        Returns:
            The updated Resource model instance.

        Raises:
            ValueError: If the resource is not found, is currently in use,
                or if the new name conflicts with an existing resource.
        """
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            raise ValueError("Resource not found")

        # Check if resource is currently in use
        if resource.status == "in_use":
            raise ValueError("Cannot edit a resource that is currently in use")

        # Update name if provided
        if update_data.name is not None:
            # Check for duplicate name (excluding current resource)
            existing = (
                self.db.query(models.Resource)
                .filter(
                    models.Resource.name == update_data.name,
                    models.Resource.id != resource_id,
                )
                .first()
            )
            if existing:
                raise ValueError(
                    f"A resource with the name '{update_data.name}' already exists"
                )
            resource.name = update_data.name

        # Update description if provided (can be set to empty string)
        if update_data.description is not None:
            resource.description = (
                update_data.description if update_data.description else None
            )

        # Update tags if provided
        if update_data.tags is not None:
            resource.tags = update_data.tags

        self.db.commit()
        self.db.refresh(resource)
        _invalidate_cache_sync()  # Invalidate resource cache

        anyio.from_thread.run(
            ws_manager.broadcast_all,
            {
                "type": "resource_updated",
                "resource_id": resource.id,
                "name": resource.name,
                "description": resource.description,
                "tags": resource.tags,
            },
        )
        return resource

    def set_resource_unavailable(
        self, resource_id: int, auto_reset_hours: int = 8
    ) -> models.Resource:
        """Set a resource as unavailable for maintenance or repair.

        Marks the resource as unavailable and sets up automatic reset
        after the specified number of hours.

        Args:
            resource_id: The ID of the resource to set unavailable.
            auto_reset_hours: Number of hours after which the resource
                will automatically become available again. Defaults to 8.

        Returns:
            The updated Resource model instance.

        Raises:
            ValueError: If the resource is not found.

        Note:
            This method broadcasts a WebSocket notification about the
            status change.
        """
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
        _invalidate_cache_sync()  # Invalidate resource cache

        anyio.from_thread.run(
            ws_manager.broadcast_all,
            {
                "type": "resource_status_changed",
                "resource_id": resource.id,
                "status": resource.status,
                "available": resource.available,
                "auto_reset_hours": resource.auto_reset_hours,
            },
        )
        return resource

    def reset_resource_to_available(self, resource_id: int) -> models.Resource:
        """Reset a resource to available status.

        Manually resets a resource from unavailable or in_use status
        back to available.

        Args:
            resource_id: The ID of the resource to reset.

        Returns:
            The updated Resource model instance.

        Raises:
            ValueError: If the resource is not found.

        Note:
            This method broadcasts a WebSocket notification about the
            status change.
        """
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
        _invalidate_cache_sync()  # Invalidate resource cache

        anyio.from_thread.run(
            ws_manager.broadcast_all,
            {
                "type": "resource_status_changed",
                "resource_id": resource.id,
                "status": resource.status,
                "available": resource.available,
            },
        )
        return resource

    def get_resource_status(self, resource_id: int) -> dict:
        """Get detailed status information for a resource.

        Retrieves comprehensive status information including availability,
        current reservation details, and maintenance information.

        Args:
            resource_id: The ID of the resource to get status for.

        Returns:
            A dictionary containing:
                - resource_id: The resource ID.
                - resource_name: The resource name.
                - base_available: The base availability setting.
                - status: Current status (available, in_use, unavailable).
                - is_available_for_reservation: Whether reservations can be made.
                - is_currently_in_use: Whether resource is currently in use.
                - is_unavailable: Whether resource is in maintenance mode.
                - current_time: The current server time.
                - unavailable_since: When maintenance mode started (if applicable).
                - auto_reset_hours: Hours until auto-reset (if applicable).
                - current_reservation: Details of current reservation (if any).

        Raises:
            ValueError: If the resource is not found.
        """
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
        """Get existing reservations for a resource over a specified time period.

        Retrieves all active reservations for a resource from the start of
        the current day through the specified number of days ahead.

        Args:
            resource_id: The ID of the resource to get the schedule for.
            days_ahead: Number of days into the future to include.
                Defaults to 7.

        Returns:
            A dictionary containing:
                - success: Boolean indicating success.
                - data: Dictionary with resource info and reservations list.

        Raises:
            ValueError: If the resource is not found.

        Example:
            >>> schedule = service.get_resource_schedule(1, days_ahead=14)
            >>> for res in schedule["data"]["reservations"]:
            ...     print(f"{res['start_time']} - {res['end_time']}")
        """
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

    def get_all_tags_with_counts(self) -> list[dict]:
        """Get all unique tags with their usage counts.

        Returns:
            A list of dictionaries with tag name and resource count.
        """
        resources = self.db.query(models.Resource).all()
        tag_counts: dict[str, int] = {}

        for resource in resources:
            for tag in resource.tags or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return [
            {"name": tag, "resource_count": count}
            for tag, count in sorted(tag_counts.items())
        ]

    def rename_tag_globally(self, old_name: str, new_name: str) -> int:
        """Rename a tag across all resources.

        Args:
            old_name: The current tag name to rename.
            new_name: The new tag name.

        Returns:
            The number of resources updated.

        Raises:
            ValueError: If old_name doesn't exist or new_name already exists.
        """
        old_name = old_name.strip()
        new_name = new_name.strip()

        if old_name == new_name:
            raise ValueError("New tag name must be different from the old name")

        # Check if old_name exists
        resources_with_old_tag = []
        all_tags = set()

        for resource in self.db.query(models.Resource).all():
            for tag in resource.tags or []:
                all_tags.add(tag.lower())
                if tag.lower() == old_name.lower():
                    resources_with_old_tag.append(resource)

        if not resources_with_old_tag:
            raise ValueError(f"Tag '{old_name}' does not exist")

        # Check if new_name already exists (case-insensitive)
        if new_name.lower() in all_tags and new_name.lower() != old_name.lower():
            raise ValueError(f"Tag '{new_name}' already exists")

        # Update all resources with the old tag
        updated_count = 0
        for resource in resources_with_old_tag:
            new_tags = []
            for tag in resource.tags or []:
                if tag.lower() == old_name.lower():
                    new_tags.append(new_name)
                else:
                    new_tags.append(tag)
            resource.tags = new_tags
            updated_count += 1

        self.db.commit()
        _invalidate_cache_sync()

        # Broadcast update
        anyio.from_thread.run(
            ws_manager.broadcast_all,
            {
                "type": "tag_renamed",
                "old_name": old_name,
                "new_name": new_name,
                "updated_count": updated_count,
            },
        )

        return updated_count

    def delete_tag_globally(self, tag_name: str) -> int:
        """Delete a tag from all resources.

        Args:
            tag_name: The tag name to delete.

        Returns:
            The number of resources updated.

        Raises:
            ValueError: If the tag doesn't exist.
        """
        tag_name = tag_name.strip()

        # Find all resources with this tag
        resources_with_tag = []
        for resource in self.db.query(models.Resource).all():
            for tag in resource.tags or []:
                if tag.lower() == tag_name.lower():
                    resources_with_tag.append(resource)
                    break

        if not resources_with_tag:
            raise ValueError(f"Tag '{tag_name}' does not exist")

        # Remove the tag from all resources
        updated_count = 0
        for resource in resources_with_tag:
            new_tags = [
                tag for tag in (resource.tags or []) if tag.lower() != tag_name.lower()
            ]
            resource.tags = new_tags
            updated_count += 1

        self.db.commit()
        _invalidate_cache_sync()

        # Broadcast update
        anyio.from_thread.run(
            ws_manager.broadcast_all,
            {
                "type": "tag_deleted",
                "name": tag_name,
                "updated_count": updated_count,
            },
        )

        return updated_count


class NotificationService:
    """Service for managing user notifications.

    Provides methods for creating, listing, and managing notifications
    for users within the system.

    Attributes:
        db: The SQLAlchemy database session for database operations.

    Example:
        >>> service = NotificationService(db_session)
        >>> notification = service.create_notification(
        ...     user_id=1,
        ...     type=NotificationType.RESERVATION_CONFIRMED,
        ...     title="Booking Confirmed",
        ...     message="Your reservation has been confirmed."
        ... )
    """

    def __init__(self, db: Session):
        """Initialize the NotificationService with a database session.

        Args:
            db: The SQLAlchemy database session to use for all operations.
        """
        self.db = db

    def create_notification(
        self,
        user_id: int,
        type: schemas.NotificationType,
        title: str,
        message: str,
        link: str | None = None,
    ) -> models.Notification:
        """Create a new notification for a user.

        Args:
            user_id: The ID of the user to notify.
            type: The type of notification from NotificationType enum.
            title: The notification title.
            message: The notification message body.
            link: Optional URL link associated with the notification.

        Returns:
            The newly created Notification model instance.

        Example:
            >>> notification = service.create_notification(
            ...     user_id=1,
            ...     type=schemas.NotificationType.SYSTEM_ANNOUNCEMENT,
            ...     title="System Update",
            ...     message="Scheduled maintenance tonight at 10 PM.",
            ...     link="/announcements/123"
            ... )
        """
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
        """List notifications for a user with pagination.

        Args:
            user_id: The ID of the user to get notifications for.
            pagination: Pagination parameters including limit, cursor,
                sort_by, and sort_order.
            include_total: Whether to include total count in response.

        Returns:
            A tuple containing:
                - list: The notifications for the current page.
                - str | None: The cursor for the next page.
                - bool: Whether there are more items.
                - int | None: Total count if include_total is True.

        Raises:
            ValueError: If sort_by or sort_order values are invalid.
        """
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
        """Mark a specific notification as read.

        Args:
            notification_id: The ID of the notification to mark as read.
            user_id: The ID of the user who owns the notification.

        Returns:
            The updated Notification model instance.

        Raises:
            ValueError: If the notification is not found or does not
                belong to the specified user.
        """
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
        """Mark all unread notifications for a user as read.

        Args:
            user_id: The ID of the user whose notifications to mark as read.

        Returns:
            The number of notifications that were marked as read.
        """
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


class ReservationService:
    """Service for reservation management operations.

    Provides methods for creating, cancelling, and managing reservations
    including support for recurring reservations and conflict detection.

    Attributes:
        db: The SQLAlchemy database session for database operations.

    Example:
        >>> service = ReservationService(db_session)
        >>> data = schemas.ReservationCreate(
        ...     resource_id=1,
        ...     start_time=datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
        ...     end_time=datetime(2024, 1, 15, 10, 0, tzinfo=UTC),
        ... )
        >>> reservation = service.create_reservation(data, user_id=1)
    """

    def __init__(self, db: Session):
        """Initialize the ReservationService with a database session.

        Args:
            db: The SQLAlchemy database session to use for all operations.
        """
        self.db = db

    def create_reservation(
        self, reservation_data: schemas.ReservationCreate, user_id: int
    ) -> models.Reservation:
        """Create a new reservation with conflict validation and retry logic.

        Creates a reservation for a specified resource and time period,
        validating against conflicts with existing reservations.

        Args:
            reservation_data: The reservation creation data containing
                resource_id, start_time, and end_time.
            user_id: The ID of the user making the reservation.

        Returns:
            The newly created Reservation model instance.

        Raises:
            ValueError: If start/end times are missing, end time is before
                start time, reservation is in the past, duration exceeds
                24 hours, resource is not found or unavailable, or there
                are conflicts with existing reservations.

        Note:
            This method implements retry logic for handling race conditions
            and broadcasts WebSocket notifications upon successful creation.
        """
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
                # Validate resource exists and is available (check each time for concurrent updates)
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
                _invalidate_cache_sync()  # Invalidate resource cache

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

                # Broadcast to user about new reservation

                try:
                    anyio.from_thread.run(
                        ws_manager.broadcast_to_user,
                        user_id,
                        {
                            "type": "reservation_created",
                            "reservation_id": reservation.id,
                            "resource_id": reservation.resource_id,
                            "start_time": reservation.start_time.isoformat(),
                            "end_time": reservation.end_time.isoformat(),
                        },
                    )
                except Exception as exc:  # pragma: no cover - best-effort notification
                    logger.warning(
                        "Failed to broadcast reservation creation for user %s: %s",
                        user_id,
                        exc,
                    )

                # Update resource status immediately if the reservation is active
                ResourceService(self.db)._update_resource_status(resource)

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
            except Exception as exc:
                logger.exception(
                    "Reservation creation attempt %s failed: %s", attempt + 1, exc
                )
                self.db.rollback()
                if attempt == max_retries - 1:
                    raise
                # Wait before retry for other exceptions too
                import time

                time.sleep(0.1 * (attempt + 1))

    def create_recurring_reservations(
        self, data: schemas.RecurringReservationCreate, user_id: int
    ) -> list[models.Reservation]:
        """Create a series of recurring reservations.

        Creates multiple reservations based on a recurrence pattern,
        checking for conflicts across all occurrences before creating any.

        Args:
            data: The recurring reservation data containing resource_id,
                start_time, end_time, and recurrence pattern.
            user_id: The ID of the user making the reservations.

        Returns:
            A list of all created Reservation model instances.

        Raises:
            ValueError: If the resource is not found, unavailable, times
                are invalid, or any occurrence has conflicts.

        Example:
            >>> recurrence = schemas.RecurrencePattern(
            ...     frequency=RecurrenceFrequency.WEEKLY,
            ...     interval=1,
            ...     days_of_week=[0, 2, 4],  # Mon, Wed, Fri
            ...     end_type=RecurrenceEndType.COUNT,
            ...     occurrence_count=10
            ... )
            >>> data = schemas.RecurringReservationCreate(
            ...     resource_id=1,
            ...     start_time=start,
            ...     end_time=end,
            ...     recurrence=recurrence
            ... )
            >>> reservations = service.create_recurring_reservations(data, user_id=1)
        """
        # Validate resource exists
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == data.resource_id)
            .first()
        )
        if not resource:
            raise ValueError("Resource not found")
        if not resource.available:
            raise ValueError("Resource is not available for reservations")

        start_time = ensure_timezone_aware(data.start_time)
        end_time = ensure_timezone_aware(data.end_time)

        if end_time <= start_time:
            raise ValueError("End time must be after start time")

        occurrences = generate_occurrences(start_time, end_time, data.recurrence)

        # Check conflicts for all occurrences first
        for occ_start, occ_end in occurrences:
            conflicts = self._get_conflicts(data.resource_id, occ_start, occ_end)
            if conflicts:
                raise ValueError(
                    f"Conflicts detected for recurring reservation starting at {occ_start.isoformat()}"
                )

        # Create recurrence rule
        rule = models.RecurrenceRule(
            frequency=data.recurrence.frequency.value,
            interval=data.recurrence.interval,
            days_of_week=data.recurrence.days_of_week,
            end_type=data.recurrence.end_type.value,
            end_date=data.recurrence.end_date,
            occurrence_count=data.recurrence.occurrence_count,
        )
        self.db.add(rule)
        self.db.flush()

        reservations: list[models.Reservation] = []
        parent_id: int | None = None

        for idx, (occ_start, occ_end) in enumerate(occurrences):
            reservation = models.Reservation(
                user_id=user_id,
                resource_id=data.resource_id,
                start_time=occ_start,
                end_time=occ_end,
                status="active",
                recurrence_rule_id=rule.id,
                parent_reservation_id=parent_id,
                is_recurring_instance=idx > 0,
            )
            self.db.add(reservation)
            self.db.flush()
            if parent_id is None:
                parent_id = reservation.id
            self._log_action(
                reservation.id,
                "created",
                user_id,
                f"Created recurring reservation #{idx + 1}",
            )
            reservations.append(reservation)

        self.db.commit()

        for res in reservations:
            self.db.refresh(res)

        return reservations

    def cancel_reservation(
        self,
        reservation_id: int,
        cancellation: schemas.ReservationCancel,
        user_id: int,
        is_admin: bool = False,
    ) -> models.Reservation:
        """Cancel an existing reservation.

        Cancels a reservation and notifies waitlist users if the slot
        becomes available. Admins can cancel any reservation.

        Args:
            reservation_id: The ID of the reservation to cancel.
            cancellation: Cancellation data including optional reason.
            user_id: The ID of the user cancelling the reservation.
            is_admin: Whether the user has admin privileges.

        Returns:
            The updated Reservation model instance with cancelled status.

        Raises:
            ValueError: If the reservation is not found, does not belong
                to the user (and user is not admin), or is already cancelled.

        Note:
            This method broadcasts WebSocket notifications and triggers
            waitlist processing for the freed time slot.
        """
        reservation = (
            self.db.query(models.Reservation)
            .filter(models.Reservation.id == reservation_id)
            .first()
        )

        if not reservation:
            raise ValueError("Reservation not found")

        if reservation.user_id != user_id and not is_admin:
            raise ValueError("You can only cancel your own reservations")

        if reservation.status == "cancelled":
            raise ValueError("Reservation is already cancelled")

        # Update reservation
        reservation.status = "cancelled"
        reservation.cancelled_at = utcnow()
        reservation.cancellation_reason = cancellation.reason

        self.db.commit()
        self.db.refresh(reservation)
        _invalidate_cache_sync()  # Invalidate resource cache

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

        try:
            anyio.from_thread.run(
                ws_manager.broadcast_to_user,
                user_id,
                {
                    "type": "reservation_cancelled",
                    "reservation_id": reservation.id,
                    "resource_id": reservation.resource_id,
                    "status": reservation.status,
                    "cancelled_at": (
                        reservation.cancelled_at.isoformat()
                        if reservation.cancelled_at
                        else None
                    ),
                },
            )
        except Exception as exc:  # pragma: no cover - best-effort notification
            logger.warning(
                "Failed to broadcast reservation cancellation for user %s: %s",
                user_id,
                exc,
            )

        # Update resource status after cancellation
        if resource:
            ResourceService(self.db)._update_resource_status(resource)

        # Check if anyone is waiting for this slot and offer it to them
        # Import here to avoid circular imports
        from app.services import WaitlistService

        waitlist_service = WaitlistService(self.db)
        waitlist_service.check_and_offer_slot(
            reservation.resource_id,
            reservation.start_time,
            reservation.end_time,
        )

        return reservation

    def get_user_reservations(
        self, user_id: int, include_cancelled: bool = False
    ) -> list[models.Reservation]:
        """Get reservations for a specific user.

        Retrieves all reservations belonging to a user, optionally
        including cancelled reservations.

        Args:
            user_id: The ID of the user to get reservations for.
            include_cancelled: Whether to include cancelled reservations.
                Defaults to False.

        Returns:
            A list of Reservation model instances ordered by start time
            descending, with resource relationship eagerly loaded.
        """
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
        """Get paginated reservations for a user.

        Args:
            user_id: The ID of the user to get reservations for.
            include_cancelled: Whether to include cancelled reservations.
            pagination: Pagination parameters including limit, cursor,
                sort_by, and sort_order.
            include_total: Whether to include total count in response.

        Returns:
            A tuple containing:
                - list: The reservations for the current page.
                - str | None: The cursor for the next page.
                - bool: Whether there are more items.
                - int | None: Total count if include_total is True.

        Raises:
            ValueError: If sort_by or sort_order values are invalid.
        """
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
        """Get the action history for a specific reservation.

        Retrieves all history entries for a reservation, ordered by
        timestamp descending.

        Args:
            reservation_id: The ID of the reservation to get history for.

        Returns:
            A list of ReservationHistory model instances.
        """
        return (
            self.db.query(models.ReservationHistory)
            .filter(models.ReservationHistory.reservation_id == reservation_id)
            .order_by(models.ReservationHistory.timestamp.desc())
            .all()
        )

    def _get_conflicts(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> list[models.Reservation]:
        """Get all conflicting reservations for a time slot.

        Finds all active reservations that overlap with the specified
        time period.

        Args:
            resource_id: The ID of the resource to check.
            start_time: The start of the time period to check.
            end_time: The end of the time period to check.

        Returns:
            A list of Reservation model instances that conflict with
            the specified time period.
        """
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

    def _log_action(
        self, reservation_id: int, action: str, user_id: int, details: str
    ) -> None:
        """Log a reservation action for audit trail.

        Creates a history entry recording an action taken on a reservation.

        Args:
            reservation_id: The ID of the reservation.
            action: The action type (e.g., "created", "cancelled").
            user_id: The ID of the user who performed the action.
            details: A description of the action.
        """
        history = models.ReservationHistory(
            reservation_id=reservation_id,
            action=action,
            user_id=user_id,
            details=details,
        )
        self.db.add(history)
        self.db.commit()


class UserService:
    """Service for user management operations.

    Provides methods for creating users and retrieving user information.

    Attributes:
        db: The SQLAlchemy database session for database operations.

    Example:
        >>> service = UserService(db_session)
        >>> user_data = schemas.UserCreate(username="john", password="secure123")
        >>> user = service.create_user(user_data)
    """

    def __init__(self, db: Session):
        """Initialize the UserService with a database session.

        Args:
            db: The SQLAlchemy database session to use for all operations.
        """
        self.db = db

    def create_user(self, user_data: schemas.UserCreate) -> models.User:
        """Create a new user with hashed password.

        Creates a user account with the provided credentials. If this is
        the first user and setup has not been completed, the user will
        be automatically assigned the admin role.

        Args:
            user_data: The user creation data containing username and password.

        Returns:
            The newly created User model instance.

        Note:
            The first user created when setup is incomplete will be assigned
            the admin role and setup will be marked as complete.
        """
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
        """Get a user by their username.

        Performs a case-insensitive search for a user by username.

        Args:
            username: The username to search for.

        Returns:
            The User model instance if found, None otherwise.

        Example:
            >>> user = service.get_user_by_username("John")
            >>> if user:
            ...     print(f"Found user: {user.username}")
        """
        # Normalize username to lowercase for case-insensitive search
        normalized_username = username.lower()
        return (
            self.db.query(models.User)
            .filter(models.User.username == normalized_username)
            .first()
        )


class WaitlistService:
    """Service for waitlist management operations.

    Manages the waitlist queue for resources, including joining, leaving,
    and automatic slot offering when reservations are cancelled.

    Attributes:
        db: The SQLAlchemy database session for database operations.
        OFFER_EXPIRY_MINUTES: Number of minutes before an offer expires.
            Defaults to 30.

    Example:
        >>> service = WaitlistService(db_session)
        >>> data = schemas.WaitlistCreate(
        ...     resource_id=1,
        ...     desired_start=start_time,
        ...     desired_end=end_time,
        ...     flexible_time=True
        ... )
        >>> entry = service.join_waitlist(data, user_id=1)
    """

    # Offer expires after 30 minutes
    OFFER_EXPIRY_MINUTES = 30

    def __init__(self, db: Session):
        """Initialize the WaitlistService with a database session.

        Args:
            db: The SQLAlchemy database session to use for all operations.
        """
        self.db = db

    def join_waitlist(
        self, waitlist_data: schemas.WaitlistCreate, user_id: int
    ) -> models.Waitlist:
        """Add a user to the waitlist for a resource.

        Adds the user to the waitlist queue for a specific resource and
        time slot. Users cannot join the same waitlist entry twice.

        Args:
            waitlist_data: The waitlist entry data containing resource_id,
                desired_start, desired_end, and flexible_time flag.
            user_id: The ID of the user joining the waitlist.

        Returns:
            The newly created Waitlist model instance.

        Raises:
            ValueError: If the resource is not found or the user is
                already on the waitlist for this time slot.

        Note:
            The user will be notified of their position in the queue.
        """
        # Validate resource exists
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == waitlist_data.resource_id)
            .first()
        )
        if not resource:
            raise ValueError("Resource not found")

        # Check if user is already on waitlist for this resource/time slot
        existing_entry = (
            self.db.query(models.Waitlist)
            .filter(
                models.Waitlist.resource_id == waitlist_data.resource_id,
                models.Waitlist.user_id == user_id,
                models.Waitlist.status.in_(["waiting", "offered"]),
                models.Waitlist.desired_start == waitlist_data.desired_start,
                models.Waitlist.desired_end == waitlist_data.desired_end,
            )
            .first()
        )
        if existing_entry:
            raise ValueError("Already on waitlist for this time slot")

        # Get current position (last position + 1)
        last_position = (
            self.db.query(models.Waitlist)
            .filter(
                models.Waitlist.resource_id == waitlist_data.resource_id,
                models.Waitlist.status == "waiting",
            )
            .count()
        )

        waitlist_entry = models.Waitlist(
            resource_id=waitlist_data.resource_id,
            user_id=user_id,
            desired_start=ensure_timezone_aware(waitlist_data.desired_start),
            desired_end=ensure_timezone_aware(waitlist_data.desired_end),
            flexible_time=waitlist_data.flexible_time,
            status="waiting",
            position=last_position + 1,
        )

        self.db.add(waitlist_entry)
        self.db.commit()
        self.db.refresh(waitlist_entry)

        # Notify user
        NotificationService(self.db).create_notification(
            user_id=user_id,
            type=schemas.NotificationType.SYSTEM_ANNOUNCEMENT,
            title="Joined waitlist",
            message=f"You're #{waitlist_entry.position} on the waitlist for {resource.name}",
            link=f"/waitlist/{waitlist_entry.id}",
        )

        return waitlist_entry

    def leave_waitlist(self, waitlist_id: int, user_id: int) -> models.Waitlist:
        """Remove a user from the waitlist.

        Cancels the user's waitlist entry and updates positions for
        remaining entries.

        Args:
            waitlist_id: The ID of the waitlist entry to remove.
            user_id: The ID of the user leaving the waitlist.

        Returns:
            The updated Waitlist model instance with cancelled status.

        Raises:
            ValueError: If the waitlist entry is not found or is no
                longer active.
        """
        entry = (
            self.db.query(models.Waitlist)
            .filter(
                models.Waitlist.id == waitlist_id,
                models.Waitlist.user_id == user_id,
            )
            .first()
        )
        if not entry:
            raise ValueError("Waitlist entry not found")

        if entry.status not in ["waiting", "offered"]:
            raise ValueError("Cannot leave waitlist - entry is no longer active")

        old_position = entry.position
        entry.status = "cancelled"
        self.db.commit()

        # Update positions for remaining entries
        self._update_positions_after_removal(entry.resource_id, old_position)

        self.db.refresh(entry)
        return entry

    def get_user_waitlist_entries(
        self,
        user_id: int,
        pagination: schemas.PaginationParams,
        include_completed: bool = False,
    ) -> tuple[list[models.Waitlist], str | None, bool, int | None]:
        """Get all waitlist entries for a user with pagination.

        Args:
            user_id: The ID of the user to get waitlist entries for.
            pagination: Pagination parameters including limit, cursor,
                sort_by, and sort_order.
            include_completed: Whether to include completed/cancelled entries.
                Defaults to False.

        Returns:
            A tuple containing:
                - list: The waitlist entries for the current page.
                - str | None: The cursor for the next page.
                - bool: Whether there are more items.
                - int | None: Total count of entries.

        Raises:
            ValueError: If sort_by or sort_order values are invalid.
        """
        query = self.db.query(models.Waitlist).filter(
            models.Waitlist.user_id == user_id
        )

        if not include_completed:
            query = query.filter(models.Waitlist.status.in_(["waiting", "offered"]))

        entries = query.options(joinedload(models.Waitlist.resource)).all()

        total_count = len(entries)
        sort_by = pagination.sort_by or "created_at"
        sort_order = (pagination.sort_order or "desc").lower()

        sort_options = {
            "id": lambda w: w.id,
            "created_at": lambda w: ensure_timezone_aware(w.created_at),
            "position": lambda w: w.position,
            "desired_start": lambda w: ensure_timezone_aware(w.desired_start),
        }

        if sort_order not in {"asc", "desc"}:
            raise ValueError("Invalid sort_order. Must be 'asc' or 'desc'.")
        if sort_by not in sort_options:
            raise ValueError(
                "Invalid sort_by. Must be one of: id, created_at, position, desired_start."
            )

        def parse_datetime(value: Any) -> datetime:
            if isinstance(value, datetime):
                return value
            try:
                return ensure_timezone_aware(datetime.fromisoformat(str(value)))
            except ValueError as exc:
                raise ValueError("Invalid cursor value") from exc

        value_parser = (
            parse_datetime if sort_by in {"created_at", "desired_start"} else None
        )

        page_items, next_cursor, has_more = _paginate_items(
            entries,
            sort_key=sort_options[sort_by],
            sort_order=sort_order,
            limit=pagination.limit,
            cursor=pagination.cursor,
            value_parser=value_parser,
        )

        return page_items, next_cursor, has_more, total_count

    def get_waitlist_for_resource(self, resource_id: int) -> list[models.Waitlist]:
        """Get all active waitlist entries for a specific resource.

        Retrieves waitlist entries ordered by position.

        Args:
            resource_id: The ID of the resource to get the waitlist for.

        Returns:
            A list of Waitlist model instances ordered by position.
        """
        return (
            self.db.query(models.Waitlist)
            .filter(
                models.Waitlist.resource_id == resource_id,
                models.Waitlist.status == "waiting",
            )
            .order_by(models.Waitlist.position)
            .all()
        )

    def check_and_offer_slot(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> None:
        """Check if a slot became available and offer it to the next person.

        Called when a reservation is cancelled to offer the freed slot
        to waitlist users who match the time period.

        Args:
            resource_id: The ID of the resource that became available.
            start_time: The start time of the available slot.
            end_time: The end time of the available slot.

        Note:
            Only users with matching time slots or flexible_time=True
            will receive offers. Offers are made in position order.
        """
        start_time = ensure_timezone_aware(start_time)
        end_time = ensure_timezone_aware(end_time)

        # Find matching waitlist entries
        matching_entries = (
            self.db.query(models.Waitlist)
            .filter(
                models.Waitlist.resource_id == resource_id,
                models.Waitlist.status == "waiting",
                models.Waitlist.desired_start <= end_time,
                models.Waitlist.desired_end >= start_time,
            )
            .order_by(models.Waitlist.position)
            .all()
        )

        for entry in matching_entries:
            # Check if the slot matches exactly or user is flexible
            exact_match = (
                entry.desired_start == start_time and entry.desired_end == end_time
            )
            if exact_match or entry.flexible_time:
                self._offer_slot_to_user(entry)
                break

    def _offer_slot_to_user(self, entry: models.Waitlist) -> None:
        """Offer a slot to a waitlist entry holder.

        Updates the waitlist entry status and sends notifications to
        the user about the available slot.

        Args:
            entry: The Waitlist model instance to offer the slot to.

        Note:
            The offer expires after OFFER_EXPIRY_MINUTES (default 30).
            Users are notified via both in-app notification and WebSocket.
        """
        now = utcnow()
        entry.status = "offered"
        entry.offered_at = now
        entry.offer_expires_at = now + timedelta(minutes=self.OFFER_EXPIRY_MINUTES)
        self.db.commit()

        # Get resource for notification
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == entry.resource_id)
            .first()
        )

        # Notify user
        NotificationService(self.db).create_notification(
            user_id=entry.user_id,
            type=schemas.NotificationType.RESOURCE_AVAILABLE,
            title="Slot available!",
            message=f"{resource.name if resource else 'Resource'} is now available! "
            f"Accept within {self.OFFER_EXPIRY_MINUTES} minutes.",
            link=f"/waitlist/{entry.id}/accept",
        )

        # Broadcast to user via WebSocket
        anyio.from_thread.run(
            ws_manager.broadcast_to_user,
            entry.user_id,
            {
                "type": "waitlist_offer",
                "waitlist_id": entry.id,
                "resource_id": entry.resource_id,
                "resource_name": resource.name if resource else "Resource",
                "expires_at": entry.offer_expires_at.isoformat(),
            },
        )

    def accept_offer(self, waitlist_id: int, user_id: int) -> models.Reservation:
        """Accept a waitlist offer and create a reservation.

        Converts an offered waitlist entry into an actual reservation.

        Args:
            waitlist_id: The ID of the waitlist entry with the offer.
            user_id: The ID of the user accepting the offer.

        Returns:
            The newly created Reservation model instance.

        Raises:
            ValueError: If the waitlist entry is not found, has no active
                offer, the offer has expired, or the reservation cannot
                be created due to conflicts.
        """
        entry = (
            self.db.query(models.Waitlist)
            .filter(
                models.Waitlist.id == waitlist_id,
                models.Waitlist.user_id == user_id,
            )
            .first()
        )
        if not entry:
            raise ValueError("Waitlist entry not found")

        if entry.status != "offered":
            raise ValueError("No active offer for this waitlist entry")

        # Check if offer has expired
        now = utcnow()
        if entry.offer_expires_at and now > entry.offer_expires_at:
            entry.status = "expired"
            self.db.commit()
            raise ValueError("Offer has expired")

        # Create the reservation
        reservation_service = ReservationService(self.db)
        try:
            reservation_data = schemas.ReservationCreate(
                resource_id=entry.resource_id,
                start_time=entry.desired_start,
                end_time=entry.desired_end,
            )
            reservation = reservation_service.create_reservation(
                reservation_data, user_id
            )

            # Update waitlist entry
            entry.status = "fulfilled"
            self.db.commit()

            # Update positions for remaining entries
            self._update_positions_after_removal(entry.resource_id, entry.position)

            return reservation
        except ValueError as e:
            # If reservation fails (conflict), mark offer as expired
            entry.status = "expired"
            self.db.commit()
            raise ValueError(f"Could not create reservation: {str(e)}") from e

    def expire_old_offers(self) -> None:
        """Expire offers that have passed their expiry time.

        Processes all offers that have expired and notifies affected users.
        After expiring an offer, checks if there's another person in the
        queue who might want the slot.

        Note:
            This method should be called periodically (e.g., via a
            background task) to clean up expired offers.
        """
        now = utcnow()
        expired_offers = (
            self.db.query(models.Waitlist)
            .filter(
                models.Waitlist.status == "offered",
                models.Waitlist.offer_expires_at < now,
            )
            .all()
        )

        for offer in expired_offers:
            offer.status = "expired"

            # Notify user that offer expired
            NotificationService(self.db).create_notification(
                user_id=offer.user_id,
                type=schemas.NotificationType.SYSTEM_ANNOUNCEMENT,
                title="Offer expired",
                message="Your waitlist offer has expired.",
            )

            # Check if there's another person in line who might want it
            self.check_and_offer_slot(
                offer.resource_id, offer.desired_start, offer.desired_end
            )

        self.db.commit()

    def _update_positions_after_removal(
        self, resource_id: int, removed_position: int
    ) -> None:
        """Update positions for remaining waitlist entries after a removal.

        Decrements the position of all entries that were after the
        removed entry.

        Args:
            resource_id: The ID of the resource.
            removed_position: The position of the removed entry.
        """
        entries_to_update = (
            self.db.query(models.Waitlist)
            .filter(
                models.Waitlist.resource_id == resource_id,
                models.Waitlist.status == "waiting",
                models.Waitlist.position > removed_position,
            )
            .all()
        )

        for entry in entries_to_update:
            entry.position -= 1

        self.db.commit()

    def get_waitlist_entry(self, waitlist_id: int) -> models.Waitlist | None:
        """Get a single waitlist entry by ID.

        Args:
            waitlist_id: The ID of the waitlist entry to retrieve.

        Returns:
            The Waitlist model instance if found, None otherwise.
            The resource relationship is eagerly loaded.
        """
        return (
            self.db.query(models.Waitlist)
            .options(joinedload(models.Waitlist.resource))
            .filter(models.Waitlist.id == waitlist_id)
            .first()
        )
