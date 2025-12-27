"""Calendar service for iCal feed generation.

This module provides functionality for generating and managing iCal calendar feeds
for the Resource Reserver application. It enables users to subscribe to their
reservations in external calendar applications (Google Calendar, Outlook, Apple
Calendar, etc.) and export individual reservations as .ics files.

Features:
    - Generate iCal feeds for user reservations with configurable date ranges
    - Generate single event .ics files for individual reservations
    - Manage secure calendar tokens for subscription URLs
    - Support for timezone-aware datetime handling
    - Automatic token generation and regeneration for security

Example Usage:
    Basic usage with a database session::

        from sqlalchemy.orm import Session
        from app.calendar_service import CalendarService, get_user_calendar_feed

        # Using the service class directly
        service = CalendarService(db_session)
        token = service.get_or_create_token(user_id=1)
        ical_feed = service.generate_ical_feed(user_id=1, days_back=30, days_ahead=90)

        # Using convenience functions
        feed = get_user_calendar_feed(db_session, user_id=1)
        ics_file = get_reservation_ics(db_session, reservation_id=42, user_id=1)

    Getting a subscription URL::

        service = CalendarService(db_session)
        url = service.get_subscription_url(user_id=1, base_url="https://api.example.com")
        # Returns: "https://api.example.com/api/v1/calendar/feed/{token}.ics"

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
    """Get the current UTC datetime with timezone awareness.

    Returns:
        datetime: The current datetime in UTC with tzinfo set to UTC.

    Example:
        >>> now = utcnow()
        >>> now.tzinfo
        datetime.timezone.utc
    """
    return datetime.now(UTC)


class CalendarService:
    """Service for managing iCal calendar feeds and subscription tokens.

    This service handles the generation of iCal formatted calendar feeds from user
    reservations, manages secure tokens for calendar subscription URLs, and provides
    functionality for exporting individual reservations as .ics files.

    Attributes:
        PRODID (str): The iCal product identifier for generated calendars.
            Set to "-//Resource-Reserver//EN".
        CALNAME (str): The display name for the calendar feed.
            Set to "Resource Reserver".
        db (Session): The SQLAlchemy database session for database operations.

    Example:
        >>> service = CalendarService(db_session)
        >>> token = service.get_or_create_token(user_id=1)
        >>> feed = service.generate_ical_feed(user_id=1)
    """

    PRODID = "-//Resource-Reserver//EN"
    CALNAME = "Resource Reserver"

    def __init__(self, db: Session) -> None:
        """Initialize the CalendarService with a database session.

        Args:
            db: SQLAlchemy database session for performing database operations.
        """
        self.db = db
        self._settings = get_settings()

    def generate_calendar_token(self) -> str:
        """Generate a secure random token for calendar feed URLs.

        Creates a cryptographically secure random token suitable for use
        in calendar subscription URLs. The token is URL-safe and provides
        sufficient entropy to prevent guessing attacks.

        Returns:
            str: A 64-character hexadecimal token string.

        Example:
            >>> service = CalendarService(db)
            >>> token = service.generate_calendar_token()
            >>> len(token)
            64
        """
        return secrets.token_hex(32)

    def get_or_create_token(self, user_id: int) -> str:
        """Get an existing calendar token or create a new one for a user.

        If the user already has a calendar token, it is returned. Otherwise,
        a new token is generated, saved to the database, and returned.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            str: The calendar token string for the user.

        Raises:
            ValueError: If no user exists with the given user_id.

        Example:
            >>> service = CalendarService(db)
            >>> token = service.get_or_create_token(user_id=42)
            >>> len(token)
            64
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
        """Regenerate the calendar token for a user.

        Creates a new calendar token for the user, invalidating any existing
        subscription URLs. This is useful when a user wants to revoke access
        to their calendar feed or if the token has been compromised.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            str: The newly generated calendar token string.

        Raises:
            ValueError: If no user exists with the given user_id.

        Note:
            This operation invalidates all existing subscription URLs for
            the user. They will need to re-subscribe with the new URL.

        Example:
            >>> service = CalendarService(db)
            >>> old_token = service.get_or_create_token(user_id=1)
            >>> new_token = service.regenerate_token(user_id=1)
            >>> old_token != new_token
            True
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
        """Retrieve a user by their calendar token.

        Looks up a user in the database by matching the provided calendar
        token. This is used to authenticate calendar feed requests.

        Args:
            token: The calendar token to look up.

        Returns:
            models.User | None: The User object if found, None otherwise.

        Example:
            >>> service = CalendarService(db)
            >>> user = service.get_user_by_token("abc123...")
            >>> if user:
            ...     print(f"Found user: {user.username}")
        """
        return (
            self.db.query(models.User)
            .filter(models.User.calendar_token == token)
            .first()
        )

    def generate_ical_feed(
        self, user_id: int, days_back: int = 30, days_ahead: int = 90
    ) -> str:
        """Generate an iCal feed containing a user's reservations.

        Creates a complete iCal formatted calendar containing all active
        reservations for the specified user within the given date range.
        The generated feed is compatible with all major calendar applications.

        Args:
            user_id: The unique identifier of the user.
            days_back: Number of days in the past to include reservations from.
                Defaults to 30.
            days_ahead: Number of days in the future to include reservations for.
                Defaults to 90.

        Returns:
            str: The iCal formatted calendar as a UTF-8 encoded string.

        Raises:
            ValueError: If no user exists with the given user_id.

        Example:
            >>> service = CalendarService(db)
            >>> ical_content = service.generate_ical_feed(
            ...     user_id=1,
            ...     days_back=7,
            ...     days_ahead=30
            ... )
            >>> ical_content.startswith("BEGIN:VCALENDAR")
            True
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        # Calculate date range for reservation query
        now = utcnow()
        start_date = now - timedelta(days=days_back)
        end_date = now + timedelta(days=days_ahead)

        # Query active reservations within the date range
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

        # Initialize the calendar with required properties
        cal = Calendar()
        cal.add("prodid", self.PRODID)
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", self.CALNAME)

        # Convert each reservation to an iCal event
        for reservation in reservations:
            event = self._create_event(reservation, user.username)
            cal.add_component(event)

        return cal.to_ical().decode("utf-8")

    def generate_single_event(self, reservation_id: int, user_id: int) -> str:
        """Generate an .ics file for a single reservation.

        Creates an iCal formatted file containing a single reservation event.
        This is useful for downloading and importing individual reservations
        into calendar applications.

        Args:
            reservation_id: The unique identifier of the reservation.
            user_id: The unique identifier of the user. Used to verify
                ownership of the reservation.

        Returns:
            str: The iCal formatted event as a UTF-8 encoded string.

        Raises:
            ValueError: If the reservation does not exist or does not
                belong to the specified user.
            ValueError: If no user exists with the given user_id.

        Example:
            >>> service = CalendarService(db)
            >>> ics_content = service.generate_single_event(
            ...     reservation_id=42,
            ...     user_id=1
            ... )
            >>> "BEGIN:VEVENT" in ics_content
            True
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

        # Create a calendar container with a single event
        cal = Calendar()
        cal.add("prodid", self.PRODID)
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")

        event = self._create_event(reservation, user.username)
        cal.add_component(event)

        return cal.to_ical().decode("utf-8")

    def _create_event(self, reservation: models.Reservation, username: str) -> Event:
        """Create an iCal Event object from a reservation.

        Converts a Reservation model instance into an iCalendar Event object
        with all relevant properties including times, summary, description,
        location, and status.

        Args:
            reservation: The Reservation model instance to convert.
            username: The username of the reservation owner, used in the
                event description.

        Returns:
            Event: An iCalendar Event object ready to be added to a Calendar.

        Note:
            This is an internal method. Timezone-naive datetimes are
            automatically converted to UTC.
        """
        event = Event()

        # Set unique identifier for the event
        event.add("uid", f"reservation-{reservation.id}@resource-reserver")

        # Ensure start and end times are timezone-aware
        start = reservation.start_time
        end = reservation.end_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)

        event.add("dtstart", start)
        event.add("dtend", end)
        event.add("dtstamp", utcnow())

        # Set event summary (title) with resource name
        resource_name = (
            reservation.resource.name if reservation.resource else "Resource"
        )
        event.add("summary", f"{resource_name} Reservation")

        # Build description with reservation details
        description = f"Reserved by {username}\nReservation ID: #{reservation.id}"
        if reservation.resource and reservation.resource.tags:
            description += f"\nTags: {', '.join(reservation.resource.tags)}"
        event["description"] = vText(description)

        # Set location to resource name
        event["location"] = vText(resource_name)

        # Map reservation status to iCal status
        if reservation.status == "active":
            event.add("status", "CONFIRMED")
        elif reservation.status == "cancelled":
            event.add("status", "CANCELLED")

        # Add creation timestamp if available
        if reservation.created_at:
            created = reservation.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            event.add("created", created)

        return event

    def get_subscription_url(self, user_id: int, base_url: str | None = None) -> str:
        """Get the subscription URL for a user's calendar feed.

        Generates the full URL that can be used to subscribe to a user's
        calendar feed in external calendar applications. If the user does
        not have a calendar token, one is automatically created.

        Args:
            user_id: The unique identifier of the user.
            base_url: Optional base URL to use for the subscription URL.
                If not provided, defaults to the API URL from application
                settings.

        Returns:
            str: The complete subscription URL ending in .ics.

        Raises:
            ValueError: If no user exists with the given user_id.

        Example:
            >>> service = CalendarService(db)
            >>> url = service.get_subscription_url(
            ...     user_id=1,
            ...     base_url="https://api.example.com"
            ... )
            >>> url
            'https://api.example.com/api/v1/calendar/feed/{token}.ics'
        """
        token = self.get_or_create_token(user_id)
        resolved_base = (base_url or self._settings.api_url).rstrip("/")
        return f"{resolved_base}/api/v1/calendar/feed/{token}.ics"


def get_user_calendar_feed(
    db: Session, user_id: int, days_back: int = 30, days_ahead: int = 90
) -> str:
    """Get an iCal feed for a user's reservations.

    Convenience function that creates a CalendarService instance and
    generates an iCal feed for the specified user.

    Args:
        db: SQLAlchemy database session.
        user_id: The unique identifier of the user.
        days_back: Number of days in the past to include reservations from.
            Defaults to 30.
        days_ahead: Number of days in the future to include reservations for.
            Defaults to 90.

    Returns:
        str: The iCal formatted calendar as a UTF-8 encoded string.

    Raises:
        ValueError: If no user exists with the given user_id.

    Example:
        >>> feed = get_user_calendar_feed(db_session, user_id=1)
        >>> feed.startswith("BEGIN:VCALENDAR")
        True
    """
    service = CalendarService(db)
    return service.generate_ical_feed(user_id, days_back, days_ahead)


def get_reservation_ics(db: Session, reservation_id: int, user_id: int) -> str:
    """Get an .ics file for a single reservation.

    Convenience function that creates a CalendarService instance and
    generates an .ics file for a specific reservation.

    Args:
        db: SQLAlchemy database session.
        reservation_id: The unique identifier of the reservation.
        user_id: The unique identifier of the user. Used to verify
            ownership of the reservation.

    Returns:
        str: The iCal formatted event as a UTF-8 encoded string.

    Raises:
        ValueError: If the reservation does not exist or does not
            belong to the specified user.
        ValueError: If no user exists with the given user_id.

    Example:
        >>> ics = get_reservation_ics(db_session, reservation_id=42, user_id=1)
        >>> "BEGIN:VEVENT" in ics
        True
    """
    service = CalendarService(db)
    return service.generate_single_event(reservation_id, user_id)
