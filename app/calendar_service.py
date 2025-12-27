"""Calendar service for iCal feed generation.

Provides functionality for:
- Generating iCal feeds for user reservations
- Generating single event .ics files
- Managing calendar tokens for subscription URLs

Author: Sylvester-Francis
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from icalendar import Calendar, Event, vText
from sqlalchemy.orm import Session, joinedload

from app import models
from app.config import get_settings

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    """Get current UTC datetime that's timezone-aware."""
    return datetime.now(UTC)


class CalendarService:
    """Service for managing iCal calendar feeds."""

    # Calendar product identifier
    PRODID = "-//Resource-Reserver//EN"
    CALNAME = "Resource Reserver"

    def __init__(self, db: Session):
        self.db = db
        self._settings = get_settings()

    def generate_calendar_token(self) -> str:
        """Generate a secure random token for calendar feed URLs.

        Returns:
            64-character hex token
        """
        return secrets.token_hex(32)

    def get_or_create_token(self, user_id: int) -> str:
        """Get existing calendar token or create a new one.

        Args:
            user_id: User ID

        Returns:
            Calendar token string
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        if not user.calendar_token:
            user.calendar_token = self.generate_calendar_token()
            self.db.commit()
            self.db.refresh(user)

        return user.calendar_token

    def regenerate_token(self, user_id: int) -> str:
        """Regenerate calendar token (invalidates old subscription URLs).

        Args:
            user_id: User ID

        Returns:
            New calendar token string
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        user.calendar_token = self.generate_calendar_token()
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"Regenerated calendar token for user {user_id}")
        return user.calendar_token

    def get_user_by_token(self, token: str) -> models.User | None:
        """Get user by calendar token.

        Args:
            token: Calendar token

        Returns:
            User object or None
        """
        return (
            self.db.query(models.User)
            .filter(models.User.calendar_token == token)
            .first()
        )

    def generate_ical_feed(
        self, user_id: int, days_back: int = 30, days_ahead: int = 90
    ) -> str:
        """Generate iCal feed for user's reservations.

        Args:
            user_id: User ID
            days_back: Include reservations from this many days ago
            days_ahead: Include reservations up to this many days in future

        Returns:
            iCal formatted string
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        # Calculate date range
        now = utcnow()
        start_date = now - timedelta(days=days_back)
        end_date = now + timedelta(days=days_ahead)

        # Get reservations
        reservations = (
            self.db.query(models.Reservation)
            .options(joinedload(models.Reservation.resource))
            .filter(
                models.Reservation.user_id == user_id,
                models.Reservation.status == "active",
                models.Reservation.start_time >= start_date,
                models.Reservation.start_time <= end_date,
            )
            .order_by(models.Reservation.start_time)
            .all()
        )

        # Create calendar
        cal = Calendar()
        cal.add("prodid", self.PRODID)
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", self.CALNAME)

        # Add events
        for reservation in reservations:
            event = self._create_event(reservation, user.username)
            cal.add_component(event)

        return cal.to_ical().decode("utf-8")

    def generate_single_event(self, reservation_id: int, user_id: int) -> str:
        """Generate .ics file for a single reservation.

        Args:
            reservation_id: Reservation ID
            user_id: User ID (for verification)

        Returns:
            iCal formatted string
        """
        reservation = (
            self.db.query(models.Reservation)
            .options(joinedload(models.Reservation.resource))
            .filter(
                models.Reservation.id == reservation_id,
                models.Reservation.user_id == user_id,
            )
            .first()
        )

        if not reservation:
            raise ValueError("Reservation not found")

        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        # Create calendar with single event
        cal = Calendar()
        cal.add("prodid", self.PRODID)
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")

        event = self._create_event(reservation, user.username)
        cal.add_component(event)

        return cal.to_ical().decode("utf-8")

    def _create_event(self, reservation: models.Reservation, username: str) -> Event:
        """Create an iCal event from a reservation.

        Args:
            reservation: Reservation model
            username: Username for description

        Returns:
            iCal Event object
        """
        event = Event()

        # Unique identifier
        event.add("uid", f"reservation-{reservation.id}@resource-reserver")

        # Times - ensure timezone awareness
        start = reservation.start_time
        end = reservation.end_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)

        event.add("dtstart", start)
        event.add("dtend", end)
        event.add("dtstamp", utcnow())

        # Summary (title)
        resource_name = (
            reservation.resource.name if reservation.resource else "Resource"
        )
        event.add("summary", f"{resource_name} Reservation")

        # Description
        description = f"Reserved by {username}\nReservation ID: #{reservation.id}"
        if reservation.resource and reservation.resource.tags:
            description += f"\nTags: {', '.join(reservation.resource.tags)}"
        event["description"] = vText(description)

        # Location
        event["location"] = vText(resource_name)

        # Status
        if reservation.status == "active":
            event.add("status", "CONFIRMED")
        elif reservation.status == "cancelled":
            event.add("status", "CANCELLED")

        # Created timestamp
        if reservation.created_at:
            created = reservation.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            event.add("created", created)

        return event

    def get_subscription_url(self, user_id: int, base_url: str | None = None) -> str:
        """Get the subscription URL for a user's calendar feed.

        Args:
            user_id: User ID
            base_url: Optional base URL (e.g., from request); defaults to settings.api_url

        Returns:
            Full URL for calendar subscription
        """
        token = self.get_or_create_token(user_id)
        resolved_base = (base_url or self._settings.api_url).rstrip("/")
        return f"{resolved_base}/api/v1/calendar/feed/{token}.ics"


# Convenience functions
def get_user_calendar_feed(
    db: Session, user_id: int, days_back: int = 30, days_ahead: int = 90
) -> str:
    """Get iCal feed for a user."""
    service = CalendarService(db)
    return service.generate_ical_feed(user_id, days_back, days_ahead)


def get_reservation_ics(db: Session, reservation_id: int, user_id: int) -> str:
    """Get .ics for a single reservation."""
    service = CalendarService(db)
    return service.generate_single_event(reservation_id, user_id)
