"""Availability service for managing business hours and time slots.

Provides functionality for:
- Calculating available time slots based on business hours
- Validating reservations against business hours
- Managing blackout dates
- Finding next available slots for waitlist

Author: Sylvester-Francis
"""

import logging
from datetime import UTC, date, datetime, time, timedelta

import anyio
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import get_settings
from app.core.cache import invalidate_resource_cache

logger = logging.getLogger(__name__)


def _invalidate_cache_sync() -> None:
    """Invalidate resource cache from a synchronous context."""
    try:
        anyio.from_thread.run(invalidate_resource_cache)
        logger.debug("Resource cache invalidated")
    except Exception as e:
        logger.debug(f"Cache invalidation skipped: {e}")


def utcnow() -> datetime:
    """Get current UTC datetime that's timezone-aware."""
    return datetime.now(UTC)


class AvailabilityService:
    """Service for managing resource availability and time slots."""

    # Default slot duration in minutes
    DEFAULT_SLOT_DURATION = 30

    # Default business hours (9 AM - 5 PM)
    DEFAULT_OPEN_TIME = time(9, 0)
    DEFAULT_CLOSE_TIME = time(17, 0)

    def __init__(self, db: Session):
        self.db = db
        self._settings = get_settings()

    def get_business_hours(
        self, resource_id: int | None, day_of_week: int
    ) -> models.BusinessHours | None:
        """Get business hours for a resource on a specific day.

        Args:
            resource_id: Resource ID (None for global defaults)
            day_of_week: Day of week (0=Monday, 6=Sunday)

        Returns:
            BusinessHours object or None if not configured
        """
        # First try resource-specific hours
        if resource_id:
            hours = (
                self.db.query(models.BusinessHours)
                .filter(
                    models.BusinessHours.resource_id == resource_id,
                    models.BusinessHours.day_of_week == day_of_week,
                )
                .first()
            )
            if hours:
                return hours

        # Fall back to global hours
        return (
            self.db.query(models.BusinessHours)
            .filter(
                models.BusinessHours.resource_id.is_(None),
                models.BusinessHours.day_of_week == day_of_week,
            )
            .first()
        )

    def get_all_business_hours(
        self, resource_id: int | None = None
    ) -> list[models.BusinessHours]:
        """Get all business hours for a resource.

        Args:
            resource_id: Resource ID (None for global defaults)

        Returns:
            List of BusinessHours for all days
        """
        if resource_id:
            # Get resource-specific hours
            hours = (
                self.db.query(models.BusinessHours)
                .filter(models.BusinessHours.resource_id == resource_id)
                .order_by(models.BusinessHours.day_of_week)
                .all()
            )
            if hours:
                return hours

        # Fall back to global hours
        return (
            self.db.query(models.BusinessHours)
            .filter(models.BusinessHours.resource_id.is_(None))
            .order_by(models.BusinessHours.day_of_week)
            .all()
        )

    def set_business_hours(
        self, resource_id: int | None, hours_data: schemas.BusinessHoursBulkUpdate
    ) -> list[models.BusinessHours]:
        """Set business hours for a resource.

        Args:
            resource_id: Resource ID (None for global defaults)
            hours_data: Bulk update with hours for each day

        Returns:
            List of created/updated BusinessHours
        """
        # Delete existing hours for this resource
        self.db.query(models.BusinessHours).filter(
            models.BusinessHours.resource_id == resource_id
            if resource_id
            else models.BusinessHours.resource_id.is_(None)
        ).delete()

        # Create new hours
        created_hours = []
        for hour_data in hours_data.hours:
            open_time = time.fromisoformat(hour_data.open_time)
            close_time = time.fromisoformat(hour_data.close_time)

            business_hours = models.BusinessHours(
                resource_id=resource_id,
                day_of_week=hour_data.day_of_week,
                open_time=open_time,
                close_time=close_time,
                is_closed=hour_data.is_closed,
            )
            self.db.add(business_hours)
            created_hours.append(business_hours)

        self.db.commit()
        for h in created_hours:
            self.db.refresh(h)

        self._sync_resource_availability(resource_id, hours_data)

        return created_hours

    def _sync_resource_availability(
        self, resource_id: int | None, hours_data: schemas.BusinessHoursBulkUpdate
    ) -> None:
        """Update resource availability when all business hours are closed.

        Marks a resource as unavailable when every configured day is closed.
        If hours are reopened, restores availability when the unavailable
        status was set by schedule (no unavailable_since timestamp).
        """
        if resource_id is None:
            return

        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )
        if not resource:
            return

        all_closed = not hours_data.hours or all(
            hour.is_closed for hour in hours_data.hours
        )
        changed = False

        if all_closed:
            if resource.available:
                resource.available = False
                resource.status = "unavailable"
                resource.unavailable_since = None
                changed = True
        else:
            if (
                resource.status == "unavailable"
                and resource.unavailable_since is None
                and not resource.available
            ):
                resource.available = True
                resource.status = "available"
                changed = True

        if changed:
            self.db.commit()
            self.db.refresh(resource)
            _invalidate_cache_sync()

    def is_blackout_date(
        self, resource_id: int | None, check_date: date
    ) -> tuple[bool, str | None]:
        """Check if a date is a blackout date.

        Args:
            resource_id: Resource ID (None checks global blackouts only)
            check_date: Date to check

        Returns:
            Tuple of (is_blackout, reason)
        """
        # Check resource-specific blackout
        if resource_id:
            blackout = (
                self.db.query(models.BlackoutDate)
                .filter(
                    models.BlackoutDate.resource_id == resource_id,
                    models.BlackoutDate.date == check_date,
                )
                .first()
            )
            if blackout:
                return True, blackout.reason

        # Check global blackout
        global_blackout = (
            self.db.query(models.BlackoutDate)
            .filter(
                models.BlackoutDate.resource_id.is_(None),
                models.BlackoutDate.date == check_date,
            )
            .first()
        )
        if global_blackout:
            return True, global_blackout.reason

        return False, None

    def add_blackout_date(
        self, resource_id: int | None, blackout_data: schemas.BlackoutDateCreate
    ) -> models.BlackoutDate:
        """Add a blackout date.

        Args:
            resource_id: Resource ID (None for global blackout)
            blackout_data: Blackout date data

        Returns:
            Created BlackoutDate
        """
        blackout = models.BlackoutDate(
            resource_id=resource_id,
            date=blackout_data.date,
            reason=blackout_data.reason,
        )
        self.db.add(blackout)
        self.db.commit()
        self.db.refresh(blackout)
        return blackout

    def remove_blackout_date(self, blackout_id: int) -> bool:
        """Remove a blackout date.

        Args:
            blackout_id: Blackout date ID

        Returns:
            True if deleted, False if not found
        """
        result = (
            self.db.query(models.BlackoutDate)
            .filter(models.BlackoutDate.id == blackout_id)
            .delete()
        )
        self.db.commit()
        return result > 0

    def get_blackout_dates(
        self, resource_id: int | None = None, include_global: bool = True
    ) -> list[models.BlackoutDate]:
        """Get blackout dates for a resource.

        Args:
            resource_id: Resource ID (None for global only)
            include_global: Whether to include global blackouts

        Returns:
            List of BlackoutDate objects
        """
        query = self.db.query(models.BlackoutDate)

        if resource_id:
            if include_global:
                query = query.filter(
                    (models.BlackoutDate.resource_id == resource_id)
                    | (models.BlackoutDate.resource_id.is_(None))
                )
            else:
                query = query.filter(models.BlackoutDate.resource_id == resource_id)
        else:
            query = query.filter(models.BlackoutDate.resource_id.is_(None))

        return query.order_by(models.BlackoutDate.date).all()

    def get_available_slots(
        self, resource_id: int, target_date: date, slot_duration: int | None = None
    ) -> schemas.AvailableSlotsResponse:
        """Get available time slots for a resource on a specific date.

        Args:
            resource_id: Resource ID
            target_date: Date to get slots for
            slot_duration: Slot duration in minutes (default: 30)

        Returns:
            AvailableSlotsResponse with slots and business hours info
        """
        slot_duration = slot_duration or self.DEFAULT_SLOT_DURATION

        # Check if it's a blackout date
        is_blackout, blackout_reason = self.is_blackout_date(resource_id, target_date)
        if is_blackout:
            return schemas.AvailableSlotsResponse(
                date=target_date,
                slots=[],
                business_hours=None,
                is_blackout=True,
                blackout_reason=blackout_reason,
            )

        # Get business hours for this day
        day_of_week = target_date.weekday()
        hours = self.get_business_hours(resource_id, day_of_week)

        # If no hours configured or day is closed, return empty slots
        if not hours or hours.is_closed:
            return schemas.AvailableSlotsResponse(
                date=target_date,
                slots=[],
                business_hours=(
                    schemas.BusinessHoursResponse.model_validate(hours)
                    if hours
                    else None
                ),
                is_blackout=False,
            )

        # Generate time slots
        slots = self._generate_slots(
            resource_id, target_date, hours.open_time, hours.close_time, slot_duration
        )

        return schemas.AvailableSlotsResponse(
            date=target_date,
            slots=slots,
            business_hours=schemas.BusinessHoursResponse.model_validate(hours),
            is_blackout=False,
        )

    def _generate_slots(
        self,
        resource_id: int,
        target_date: date,
        open_time: time,
        close_time: time,
        slot_duration: int,
    ) -> list[schemas.TimeSlot]:
        """Generate time slots for a day.

        Args:
            resource_id: Resource ID
            target_date: Date to generate slots for
            open_time: Opening time
            close_time: Closing time
            slot_duration: Slot duration in minutes

        Returns:
            List of TimeSlot objects
        """
        slots = []
        now = utcnow()

        # Create datetime objects for the day
        current_slot_start = datetime.combine(target_date, open_time, tzinfo=UTC)
        day_end = datetime.combine(target_date, close_time, tzinfo=UTC)

        # Get existing reservations for this day
        existing_reservations = self._get_reservations_for_date(
            resource_id, target_date
        )

        while current_slot_start + timedelta(minutes=slot_duration) <= day_end:
            slot_end = current_slot_start + timedelta(minutes=slot_duration)

            # Check if slot is in the past
            if current_slot_start < now:
                available = False
            else:
                # Check for conflicts with existing reservations
                available = not self._has_conflict(
                    existing_reservations, current_slot_start, slot_end
                )

            slots.append(
                schemas.TimeSlot(
                    start=current_slot_start,
                    end=slot_end,
                    available=available,
                )
            )

            current_slot_start = slot_end

        return slots

    def _get_reservations_for_date(
        self, resource_id: int, target_date: date
    ) -> list[models.Reservation]:
        """Get all active reservations for a resource on a specific date."""
        day_start = datetime.combine(target_date, time(0, 0), tzinfo=UTC)
        day_end = datetime.combine(target_date, time(23, 59, 59), tzinfo=UTC)

        return (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.start_time < day_end,
                models.Reservation.end_time > day_start,
            )
            .all()
        )

    def _has_conflict(
        self,
        reservations: list[models.Reservation],
        start: datetime,
        end: datetime,
    ) -> bool:
        """Check if a time range conflicts with any reservations."""
        for res in reservations:
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
            if res_start < end and res_end > start:
                return True
        return False

    def is_within_business_hours(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> tuple[bool, str | None]:
        """Check if a time range is within business hours.

        Args:
            resource_id: Resource ID
            start_time: Start time of the range
            end_time: End time of the range

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if start and end are on the same day
        if start_time.date() != end_time.date():
            # For multi-day reservations, check each day
            current_date = start_time.date()
            while current_date <= end_time.date():
                if current_date == start_time.date():
                    day_start = start_time
                    day_end = datetime.combine(
                        current_date, time(23, 59, 59), tzinfo=UTC
                    )
                elif current_date == end_time.date():
                    day_start = datetime.combine(current_date, time(0, 0), tzinfo=UTC)
                    day_end = end_time
                else:
                    day_start = datetime.combine(current_date, time(0, 0), tzinfo=UTC)
                    day_end = datetime.combine(
                        current_date, time(23, 59, 59), tzinfo=UTC
                    )

                valid, error = self._check_single_day(
                    resource_id, current_date, day_start.time(), day_end.time()
                )
                if not valid:
                    return False, error

                current_date += timedelta(days=1)

            return True, None

        # Single day reservation
        return self._check_single_day(
            resource_id, start_time.date(), start_time.time(), end_time.time()
        )

    def _check_single_day(
        self,
        resource_id: int,
        check_date: date,
        start_time: time,
        end_time: time,
    ) -> tuple[bool, str | None]:
        """Check if a time range is within business hours for a single day."""
        # Check blackout date
        is_blackout, reason = self.is_blackout_date(resource_id, check_date)
        if is_blackout:
            return False, f"Date is blocked: {reason or 'Unavailable'}"

        # Get business hours
        day_of_week = check_date.weekday()
        hours = self.get_business_hours(resource_id, day_of_week)

        # If no business hours configured, allow any time
        if not hours:
            return True, None

        # Check if day is closed
        if hours.is_closed:
            day_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            return False, f"Resource is closed on {day_names[day_of_week]}s"

        # Check if time is within hours
        if start_time < hours.open_time:
            return (
                False,
                f"Start time {start_time.strftime('%H:%M')} is before opening time {hours.open_time.strftime('%H:%M')}",
            )

        if end_time > hours.close_time:
            return (
                False,
                f"End time {end_time.strftime('%H:%M')} is after closing time {hours.close_time.strftime('%H:%M')}",
            )

        return True, None

    def get_next_available_slot(
        self, resource_id: int, slot_duration: int | None = None, days_ahead: int = 14
    ) -> schemas.TimeSlot | None:
        """Find the next available time slot for a resource.

        Args:
            resource_id: Resource ID
            slot_duration: Desired slot duration in minutes
            days_ahead: How many days ahead to search

        Returns:
            Next available TimeSlot or None if none found
        """
        slot_duration = slot_duration or self.DEFAULT_SLOT_DURATION
        current_date = date.today()

        for _ in range(days_ahead):
            response = self.get_available_slots(
                resource_id, current_date, slot_duration
            )

            # Find first available slot
            for slot in response.slots:
                if slot.available:
                    return slot

            current_date += timedelta(days=1)

        return None


# Convenience functions for direct use
def get_available_slots(
    db: Session, resource_id: int, target_date: date, slot_duration: int | None = None
) -> schemas.AvailableSlotsResponse:
    """Get available time slots for a resource on a specific date."""
    service = AvailabilityService(db)
    return service.get_available_slots(resource_id, target_date, slot_duration)


def is_within_business_hours(
    db: Session, resource_id: int, start_time: datetime, end_time: datetime
) -> tuple[bool, str | None]:
    """Check if a time range is within business hours."""
    service = AvailabilityService(db)
    return service.is_within_business_hours(resource_id, start_time, end_time)
