"""Pydantic schemas for request/response validation in the Resource Reserver API.

This module defines all Pydantic models used for data validation, serialization,
and deserialization across the Resource Reserver application. It provides type-safe
request and response schemas for users, resources, reservations, notifications,
waitlists, business hours, approvals, and search functionality.

Features:
    - User authentication and profile schemas with password validation
    - Resource management schemas with availability tracking
    - Reservation schemas with recurrence rule support
    - Notification system schemas with type enumeration
    - Waitlist management schemas with offer tracking
    - Business hours and blackout date schemas
    - Approval workflow schemas for resource access control
    - Advanced search and filtering schemas
    - Pagination support for list responses

Example Usage:
    Creating a new user::

        from app.schemas import UserCreate

        user_data = UserCreate(
            username="john_doe",
            password="SecureP@ssw0rd123"
        )

    Creating a reservation::

        from app.schemas import ReservationCreate
        from datetime import datetime, timedelta, UTC

        reservation = ReservationCreate(
            resource_id=1,
            start_time=datetime.now(UTC) + timedelta(hours=1),
            end_time=datetime.now(UTC) + timedelta(hours=2)
        )

    Searching for resources::

        from app.schemas import ResourceSearchParams

        search_params = ResourceSearchParams(
            query="conference room",
            available_only=True,
            tags=["large", "video"]
        )

Author:
    Resource Reserver Development Team

Note:
    All datetime fields are timezone-aware and default to UTC. Naive datetimes
    are automatically converted to UTC.
"""

from datetime import UTC, date, datetime, time, timedelta
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.utils.password import PasswordPolicy


def ensure_timezone_aware(dt):
    """Ensure a datetime object is timezone-aware.

    Converts naive datetime objects to UTC timezone-aware datetimes.
    If the datetime is already timezone-aware, it is returned unchanged.

    Args:
        dt: A datetime object that may or may not be timezone-aware,
            or None.

    Returns:
        A timezone-aware datetime object with UTC timezone if the input
        was naive, the original datetime if already timezone-aware,
        or None if the input was None.

    Example:
        >>> from datetime import datetime, UTC
        >>> naive_dt = datetime(2024, 1, 15, 10, 30)
        >>> aware_dt = ensure_timezone_aware(naive_dt)
        >>> aware_dt.tzinfo is not None
        True
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If naive, assume it's UTC
        return dt.replace(tzinfo=UTC)
    return dt


def utcnow():
    """Get the current UTC datetime as a timezone-aware object.

    Returns:
        A timezone-aware datetime object representing the current time in UTC.

    Example:
        >>> now = utcnow()
        >>> now.tzinfo is not None
        True
    """
    return datetime.now(UTC)


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper for list endpoints.

    Provides cursor-based pagination support for any list response type,
    allowing efficient traversal of large datasets.

    Attributes:
        data: The list of items for the current page.
        next_cursor: Opaque cursor string for fetching the next page,
            or None if this is the last page.
        prev_cursor: Opaque cursor string for fetching the previous page,
            or None if this is the first page.
        has_more: Boolean indicating whether more items exist beyond
            the current page.
        total_count: Optional total count of all items matching the query,
            may be None if counting is expensive.

    Example:
        >>> response = PaginatedResponse[ResourceResponse](
        ...     data=[resource1, resource2],
        ...     next_cursor="eyJpZCI6IDEwfQ==",
        ...     prev_cursor=None,
        ...     has_more=True,
        ...     total_count=50
        ... )
    """

    data: list[T]
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_more: bool
    total_count: int | None = None


class PaginationParams(BaseModel):
    """Parameters for cursor-based pagination requests.

    Encapsulates pagination configuration including cursor position,
    page size limits, and sorting options.

    Attributes:
        cursor: Opaque cursor string from a previous response for
            continuation, or None to start from the beginning.
        limit: Maximum number of items to return per page.
            Must be between 1 and 100, defaults to 20.
        sort_by: Field name to sort results by. Defaults to "created_at".
        sort_order: Sort direction, either "asc" or "desc".
            Defaults to "desc".
    """

    cursor: str | None = None
    limit: int = Field(default=20, le=100, ge=1)
    sort_by: str | None = "created_at"
    sort_order: str | None = "desc"


class UserCreate(BaseModel):
    """Schema for user registration requests.

    Validates username format and password strength during user creation.
    Usernames are normalized to lowercase after validation.

    Attributes:
        username: The desired username. Must be 3-50 characters and contain
            only letters, numbers, hyphens, and underscores.
        password: The user's password. Must meet the password policy
            requirements including length, complexity, and must not
            contain the username.
    """

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate and normalize the username.

        Args:
            v: The username string to validate.

        Returns:
            The validated username converted to lowercase.

        Raises:
            ValueError: If the username is not 3-50 characters or contains
                invalid characters.
        """
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3-50 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, hyphens and underscores"  # noqa : E501
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str, info: ValidationInfo) -> str:
        """Validate password against the password policy.

        Args:
            v: The password string to validate.
            info: Validation context containing other field values.

        Returns:
            The validated password if it meets all policy requirements.

        Raises:
            ValueError: If the password fails any policy requirements,
                with error messages joined by semicolons.
        """
        username = ""
        if info.data:
            username = info.data.get("username") or ""
        is_valid, errors = PasswordPolicy.validate(v, username=username)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v


class UserResponse(BaseModel):
    """Schema for basic user information in API responses.

    Provides minimal user data suitable for embedding in other responses
    or for public-facing user information.

    Attributes:
        id: The unique identifier of the user.
        username: The user's username.
    """

    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(BaseModel):
    """Extended user response with email and notification preferences.

    Provides complete user profile information including email verification
    status, MFA configuration, and notification settings.

    Attributes:
        id: The unique identifier of the user.
        username: The user's username.
        email: The user's email address, or None if not set.
        email_verified: Whether the email address has been verified.
        mfa_enabled: Whether multi-factor authentication is enabled.
        email_notifications: Whether email notifications are enabled.
        reminder_hours: Hours before a reservation to send reminder
            notifications.
    """

    id: int
    username: str
    email: str | None = None
    email_verified: bool = False
    mfa_enabled: bool = False
    email_notifications: bool = True
    reminder_hours: int = 24

    model_config = ConfigDict(from_attributes=True)


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user notification preferences.

    Allows partial updates to user notification settings. Only provided
    fields will be updated.

    Attributes:
        email_notifications: Whether to enable email notifications,
            or None to leave unchanged.
        reminder_hours: Hours before reservation for reminder notifications.
            Must be between 1 and 168 (1 week), or None to leave unchanged.
    """

    email_notifications: bool | None = None
    reminder_hours: int | None = Field(None, ge=1, le=168)  # 1 hour to 1 week


class SetupInitializeRequest(BaseModel):
    """Schema for system initialization during first-time setup.

    Supports creating a new admin user or promoting an existing user
    during initial system configuration.

    Attributes:
        username: Username for new admin account, or None if using
            existing user.
        password: Password for new admin account, or None if using
            existing user.
        existing_username: Username of existing user to promote to admin,
            or None if creating new user.
    """

    username: str | None = None
    password: str | None = None
    existing_username: str | None = None

    @field_validator("username")
    @classmethod
    def validate_setup_username(cls, v: str | None) -> str | None:
        """Validate and normalize the setup username.

        Args:
            v: The username string to validate, or None.

        Returns:
            The validated username converted to lowercase, or None.

        Raises:
            ValueError: If provided and not 3-50 characters or contains
                invalid characters.
        """
        if v is None:
            return v
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3-50 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, hyphens and underscores"  # noqa : E501
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_setup_password(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Validate setup password against the password policy.

        Args:
            v: The password string to validate, or None.
            info: Validation context containing other field values.

        Returns:
            The validated password, or None if not provided.

        Raises:
            ValueError: If provided and fails any policy requirements.
        """
        if v is None:
            return v
        username = ""
        if info.data:
            username = (
                info.data.get("username") or info.data.get("existing_username") or ""
            )
        is_valid, errors = PasswordPolicy.validate(v, username=username)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v


class ResourceCreate(BaseModel):
    """Schema for creating a new resource.

    Validates resource name format and provides defaults for optional fields.

    Attributes:
        name: The resource name. Must be 1-200 characters after trimming
            whitespace.
        tags: List of tags for categorizing the resource. Defaults to
            an empty list.
        available: Initial availability status. Defaults to True.
    """

    name: str
    tags: list[str] | None = []
    available: bool | None = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize the resource name.

        Args:
            v: The resource name to validate.

        Returns:
            The validated name with leading and trailing whitespace removed.

        Raises:
            ValueError: If the name is empty or exceeds 200 characters.
        """
        name = v.strip()
        if not name or len(name) > 200:
            raise ValueError("Resource name must be 1-200 characters")
        return name


class ResourceResponse(BaseModel):
    """Schema for resource information in API responses.

    Provides both static availability (manual setting) and real-time
    availability that accounts for current reservations.

    Attributes:
        id: The unique identifier of the resource.
        name: The resource name.
        available: Base availability flag (manual enable/disable).
        current_availability: Real-time availability considering active
            reservations, or None if not computed.
        status: Current status string: "available", "in_use", or
            "unavailable".
        tags: List of tags associated with the resource.
    """

    id: int
    name: str
    available: bool  # Base availability (manual enable/disable)
    current_availability: bool | None = (
        None  # Real-time availability (includes reservations)  # noqa
    )
    status: str = "available"  # Status: available, in_use, unavailable
    tags: list[str]

    model_config = ConfigDict(from_attributes=True)


class ResourceAvailabilityUpdate(BaseModel):
    """Schema for updating resource availability status.

    Allows toggling the manual availability flag for a resource.

    Attributes:
        available: The new availability status for the resource.
    """

    available: bool

    model_config = ConfigDict(from_attributes=True)


class ReservationCreate(BaseModel):
    """Schema for creating a new reservation.

    Validates time constraints including future start time, proper ordering,
    minimum duration, and maximum duration limits.

    Attributes:
        resource_id: ID of the resource to reserve.
        start_time: When the reservation begins. Must be in the future.
        end_time: When the reservation ends. Must be after start_time,
            at least 15 minutes after start, and within 7 days of start.
    """

    resource_id: int
    start_time: datetime
    end_time: datetime

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: datetime) -> datetime:
        """Validate that start time is in the future.

        Args:
            v: The start time to validate.

        Returns:
            The validated timezone-aware start time.

        Raises:
            ValueError: If start time is not in the future.
        """
        # Ensure timezone awareness
        v = ensure_timezone_aware(v)

        if v <= utcnow():
            raise ValueError("Start time must be in the future")
        return v

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        """Validate end time constraints.

        Args:
            v: The end time to validate.
            info: Validation context containing the start time.

        Returns:
            The validated timezone-aware end time.

        Raises:
            ValueError: If end time is not after start time, or if
                duration is less than 15 minutes or exceeds 7 days.
        """
        # Ensure timezone awareness
        v = ensure_timezone_aware(v)

        start = info.data.get("start_time")
        if start:
            # Ensure start time is also timezone-aware
            start = ensure_timezone_aware(start)

            if v <= start:
                raise ValueError("End time must be after start time")

            duration = v - start
            if duration > timedelta(days=7):
                raise ValueError("Reservation cannot exceed 7 days")
            if duration < timedelta(minutes=15):
                raise ValueError("Reservation must be at least 15 minutes")

        return v


class ReservationResponse(BaseModel):
    """Schema for reservation information in API responses.

    Provides complete reservation details including associated resource,
    status, cancellation information, and recurrence details.

    Attributes:
        id: The unique identifier of the reservation.
        user_id: ID of the user who made the reservation.
        resource_id: ID of the reserved resource.
        resource: Full resource details for the reservation.
        start_time: When the reservation begins.
        end_time: When the reservation ends.
        status: Current status (e.g., "active", "cancelled", "completed").
        created_at: When the reservation was created.
        cancelled_at: When the reservation was cancelled, or None.
        cancellation_reason: Reason for cancellation, or None.
        recurrence_rule_id: ID of associated recurrence rule, or None
            for non-recurring reservations.
        parent_reservation_id: ID of parent reservation for recurring
            instances, or None.
        is_recurring_instance: Whether this is an instance of a recurring
            reservation.
    """

    id: int
    user_id: int
    resource_id: int
    resource: ResourceResponse
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    recurrence_rule_id: int | None = None
    parent_reservation_id: int | None = None
    is_recurring_instance: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class ReservationCancel(BaseModel):
    """Schema for cancelling a reservation.

    Optionally provides a reason for the cancellation.

    Attributes:
        reason: Optional explanation for the cancellation.
    """

    reason: str | None = None


class ResourceStatusUpdate(BaseModel):
    """Schema for updating resource status reset configuration.

    Configures automatic status reset behavior for resources.

    Attributes:
        auto_reset_hours: Number of hours after which resource status
            should automatically reset. Must be between 1 and 168 hours
            (1 week).
    """

    auto_reset_hours: int = 8

    @field_validator("auto_reset_hours")
    @classmethod
    def validate_auto_reset_hours(cls, v: int) -> int:
        """Validate auto reset hours is within acceptable range.

        Args:
            v: The number of hours to validate.

        Returns:
            The validated hours value.

        Raises:
            ValueError: If hours is not between 1 and 168.
        """
        if v < 1 or v > 168:  # 1 hour to 1 week
            raise ValueError("Auto reset hours must be between 1 and 168 (1 week)")
        return v


class NotificationType(str, Enum):
    """Enumeration of notification types.

    Defines the various types of notifications that can be sent to users.

    Attributes:
        RESERVATION_CONFIRMED: Notification for confirmed reservations.
        RESERVATION_CANCELLED: Notification for cancelled reservations.
        RESERVATION_REMINDER: Reminder before a reservation starts.
        RESOURCE_AVAILABLE: Alert when a watched resource becomes available.
        SYSTEM_ANNOUNCEMENT: System-wide announcements.
    """

    RESERVATION_CONFIRMED = "reservation_confirmed"
    RESERVATION_CANCELLED = "reservation_cancelled"
    RESERVATION_REMINDER = "reservation_reminder"
    RESOURCE_AVAILABLE = "resource_available"
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class NotificationBase(BaseModel):
    """Base schema for notification data.

    Provides common notification fields used by both create and response
    schemas.

    Attributes:
        type: The type of notification from NotificationType enum.
        title: Short title for the notification.
        message: Full notification message content.
        link: Optional URL for navigation when notification is clicked.
    """

    type: NotificationType
    title: str
    message: str
    link: str | None = None


class NotificationCreate(NotificationBase):
    """Schema for creating a new notification.

    Extends the base notification schema with the target user.

    Attributes:
        user_id: ID of the user to receive the notification.
    """

    user_id: int


class NotificationResponse(NotificationBase):
    """Schema for notification information in API responses.

    Extends the base notification schema with server-generated fields.

    Attributes:
        id: The unique identifier of the notification.
        read: Whether the notification has been read by the user.
        created_at: When the notification was created.
    """

    id: int
    read: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecurrenceFrequency(str, Enum):
    """Enumeration of recurrence frequency options.

    Defines how often a recurring reservation repeats.

    Attributes:
        daily: Repeats every day (or every N days with interval).
        weekly: Repeats every week (or every N weeks with interval).
        monthly: Repeats every month (or every N months with interval).
    """

    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class RecurrenceEndType(str, Enum):
    """Enumeration of recurrence ending strategies.

    Defines when a recurring reservation series should stop.

    Attributes:
        never: Recurrence continues indefinitely.
        on_date: Recurrence ends on a specific date.
        after_count: Recurrence ends after a specific number of occurrences.
    """

    never = "never"
    on_date = "on_date"
    after_count = "after_count"


class RecurrenceRuleBase(BaseModel):
    """Base schema for recurrence rule configuration.

    Defines the pattern for recurring reservations including frequency,
    interval, and ending conditions.

    Attributes:
        frequency: How often the reservation repeats (daily, weekly, monthly).
        interval: Number of frequency units between occurrences.
            Defaults to 1 (every occurrence).
        days_of_week: For weekly recurrence, list of days (0=Monday to
            6=Sunday) when the reservation occurs.
        end_type: How the recurrence series ends.
        end_date: Date when recurrence ends (required if end_type is on_date).
        occurrence_count: Number of occurrences before ending (used with
            after_count end_type). Must be 1-100, defaults to 5.
    """

    frequency: RecurrenceFrequency
    interval: int = 1
    days_of_week: list[int] | None = None
    end_type: RecurrenceEndType = RecurrenceEndType.after_count
    end_date: datetime | None = None
    occurrence_count: int | None = Field(default=5, ge=1, le=100)

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        """Validate that interval is positive.

        Args:
            v: The interval value to validate.

        Returns:
            The validated interval.

        Raises:
            ValueError: If interval is less than 1.
        """
        if v < 1:
            raise ValueError("Interval must be at least 1")
        return v

    @field_validator("days_of_week")
    @classmethod
    def validate_days(
        cls, v: list[int] | None, info: ValidationInfo
    ) -> list[int] | None:
        """Validate days of week for weekly recurrence.

        Args:
            v: List of day numbers (0-6) or None.
            info: Validation context with frequency information.

        Returns:
            The validated days list or None.

        Raises:
            ValueError: If any day is not between 0 and 6.
        """
        frequency = info.data.get("frequency")
        if frequency == RecurrenceFrequency.weekly and v:
            for day in v:
                if day < 0 or day > 6:
                    raise ValueError("days_of_week must be between 0 (Mon) and 6 (Sun)")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_end_date(
        cls, v: datetime | None, info: ValidationInfo
    ) -> datetime | None:
        """Validate end date is provided when required.

        Args:
            v: The end date or None.
            info: Validation context with end_type information.

        Returns:
            The validated end date or None.

        Raises:
            ValueError: If end_type is on_date but end_date is not provided.
        """
        end_type = info.data.get("end_type")
        if end_type == RecurrenceEndType.on_date and v is None:
            raise ValueError("end_date is required when end_type is on_date")
        return v


class RecurrenceRuleCreate(RecurrenceRuleBase):
    """Schema for creating a recurrence rule.

    Inherits all fields and validation from RecurrenceRuleBase.
    Used when creating new recurring reservation patterns.
    """

    pass


class RecurrenceRuleResponse(RecurrenceRuleBase):
    """Schema for recurrence rule information in API responses.

    Extends RecurrenceRuleBase with server-generated identifier.

    Attributes:
        id: The unique identifier of the recurrence rule.
    """

    id: int

    model_config = ConfigDict(from_attributes=True)


class RecurringReservationCreate(BaseModel):
    """Schema for creating a recurring reservation series.

    Combines basic reservation timing with recurrence configuration.

    Attributes:
        resource_id: ID of the resource to reserve.
        start_time: Start time for the first occurrence.
        end_time: End time for the first occurrence (defines duration
            for all occurrences).
        recurrence: The recurrence pattern configuration.
    """

    resource_id: int
    start_time: datetime
    end_time: datetime
    recurrence: RecurrenceRuleCreate

    @field_validator("start_time", "end_time")
    @classmethod
    def ensure_tz(cls, v: datetime) -> datetime:
        """Ensure datetime values are timezone-aware.

        Args:
            v: The datetime to process.

        Returns:
            A timezone-aware datetime in UTC.
        """
        return ensure_timezone_aware(v)


# ============================================================================
# Waitlist Schemas
# ============================================================================


class WaitlistStatus(str, Enum):
    """Enumeration of waitlist entry statuses.

    Tracks the lifecycle of a waitlist entry from creation to resolution.

    Attributes:
        WAITING: User is waiting for the resource to become available.
        OFFERED: An opening was found and offered to the user.
        EXPIRED: The offer expired without user action.
        FULFILLED: User accepted the offer and got a reservation.
        CANCELLED: User cancelled their waitlist entry.
    """

    WAITING = "waiting"
    OFFERED = "offered"
    EXPIRED = "expired"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class WaitlistCreate(BaseModel):
    """Schema for joining a resource waitlist.

    Allows users to express interest in a resource for a specific time
    period, optionally with flexibility in timing.

    Attributes:
        resource_id: ID of the desired resource.
        desired_start: Preferred start time for the reservation.
            Must be in the future.
        desired_end: Preferred end time for the reservation.
            Must be after desired_start.
        flexible_time: Whether the user accepts alternative time slots.
    """

    resource_id: int
    desired_start: datetime
    desired_end: datetime
    flexible_time: bool = False

    @field_validator("desired_start")
    @classmethod
    def validate_desired_start(cls, v: datetime) -> datetime:
        """Validate that desired start is in the future.

        Args:
            v: The desired start time.

        Returns:
            The validated timezone-aware start time.

        Raises:
            ValueError: If the time is not in the future.
        """
        v = ensure_timezone_aware(v)
        if v <= utcnow():
            raise ValueError("Desired start time must be in the future")
        return v

    @field_validator("desired_end")
    @classmethod
    def validate_desired_end(cls, v: datetime, info) -> datetime:
        """Validate that desired end is after start.

        Args:
            v: The desired end time.
            info: Validation context with start time.

        Returns:
            The validated timezone-aware end time.

        Raises:
            ValueError: If end time is not after start time.
        """
        v = ensure_timezone_aware(v)
        start = info.data.get("desired_start")
        if start:
            start = ensure_timezone_aware(start)
            if v <= start:
                raise ValueError("End time must be after start time")
        return v


class WaitlistResponse(BaseModel):
    """Schema for waitlist entry information in API responses.

    Provides complete waitlist entry details including position and
    offer status.

    Attributes:
        id: The unique identifier of the waitlist entry.
        resource_id: ID of the waitlisted resource.
        user_id: ID of the user on the waitlist.
        desired_start: User's preferred start time.
        desired_end: User's preferred end time.
        flexible_time: Whether user accepts alternative times.
        status: Current status of the waitlist entry.
        position: User's position in the waitlist queue.
        created_at: When the waitlist entry was created.
        offered_at: When an offer was made, or None.
        offer_expires_at: When the current offer expires, or None.
    """

    id: int
    resource_id: int
    user_id: int
    desired_start: datetime
    desired_end: datetime
    flexible_time: bool
    status: str
    position: int
    created_at: datetime
    offered_at: datetime | None = None
    offer_expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WaitlistWithResourceResponse(WaitlistResponse):
    """Waitlist response with embedded resource details.

    Extends WaitlistResponse with full resource information.

    Attributes:
        resource: Complete resource details for the waitlisted resource.
    """

    resource: ResourceResponse


class WaitlistAcceptOffer(BaseModel):
    """Schema for accepting a waitlist offer.

    Empty schema used to accept an offer. The waitlist entry ID is
    provided in the URL path.
    """

    pass  # No additional fields needed, ID comes from path


# ============================================================================
# Business Hours Schemas
# ============================================================================


class BusinessHoursCreate(BaseModel):
    """Schema for creating or updating business hours.

    Defines operating hours for a specific day of the week.

    Attributes:
        day_of_week: Day number where 0=Monday and 6=Sunday.
        open_time: Opening time in HH:MM format (24-hour).
        close_time: Closing time in HH:MM format (24-hour).
            Must be after open_time unless is_closed is True.
        is_closed: Whether the resource is closed on this day.
    """

    day_of_week: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")
    open_time: str = Field(
        pattern=r"^\d{2}:\d{2}(:\d{2})?$", description="HH:MM or HH:MM:SS format"
    )
    close_time: str = Field(
        pattern=r"^\d{2}:\d{2}(:\d{2})?$", description="HH:MM or HH:MM:SS format"
    )
    is_closed: bool = False

    @field_validator("open_time", "close_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time string format and values.

        Args:
            v: Time string in HH:MM format.

        Returns:
            The validated time string.

        Raises:
            ValueError: If format is invalid or time values are out of range.
        """
        try:
            parts = v.split(":")
            if len(parts) == 2:
                hours, minutes = map(int, parts)
                seconds = 0
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
            else:
                raise ValueError("Invalid time")
            if not (0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59):
                raise ValueError("Invalid time")
            return v
        except (ValueError, AttributeError) as e:
            raise ValueError("Time must be in HH:MM or HH:MM:SS format") from e

    @field_validator("close_time")
    @classmethod
    def validate_close_after_open(cls, v: str, info: ValidationInfo) -> str:
        """Validate that close time is after open time.

        Args:
            v: The close time string.
            info: Validation context with open time and is_closed flag.

        Returns:
            The validated close time.

        Raises:
            ValueError: If close time is not after open time (when not closed).
        """
        open_time = info.data.get("open_time")
        if not open_time:
            return v
        open_parsed = time.fromisoformat(open_time)
        close_parsed = time.fromisoformat(v)
        if close_parsed <= open_parsed:
            is_closed = info.data.get("is_closed", False)
            if not is_closed:
                raise ValueError("Close time must be after open time")
        return v


class BusinessHoursResponse(BaseModel):
    """Schema for business hours information in API responses.

    Represents configured operating hours for a resource or system default.

    Attributes:
        id: The unique identifier of the business hours record.
        resource_id: ID of the associated resource, or None for
            system defaults.
        day_of_week: Day number (0=Monday, 6=Sunday).
        open_time: Opening time.
        close_time: Closing time.
        is_closed: Whether closed on this day.
    """

    id: int
    resource_id: int | None = None
    day_of_week: int
    open_time: time
    close_time: time
    is_closed: bool

    model_config = ConfigDict(from_attributes=True)


class BusinessHoursBulkUpdate(BaseModel):
    """Schema for bulk updating business hours for a resource.

    Allows setting hours for multiple days in a single request.

    Attributes:
        hours: List of business hours configurations for different days.
            Each day can only appear once.
    """

    hours: list[BusinessHoursCreate]

    @field_validator("hours")
    @classmethod
    def validate_unique_days(
        cls, v: list[BusinessHoursCreate]
    ) -> list[BusinessHoursCreate]:
        """Validate that each day appears only once.

        Args:
            v: List of business hours configurations.

        Returns:
            The validated list.

        Raises:
            ValueError: If any day of week appears more than once.
        """
        days = [h.day_of_week for h in v]
        if len(days) != len(set(days)):
            raise ValueError("Duplicate days of week not allowed")
        return v


class BlackoutDateCreate(BaseModel):
    """Schema for creating a blackout date.

    Blackout dates are days when a resource is unavailable for booking.

    Attributes:
        date: The date to block. Must be today or in the future.
        reason: Optional explanation for the blackout (max 255 characters).
    """

    date: date
    reason: str | None = Field(None, max_length=255)

    @field_validator("date")
    @classmethod
    def validate_future_date(cls, v: date) -> date:
        """Validate that blackout date is not in the past.

        Args:
            v: The date to validate.

        Returns:
            The validated date.

        Raises:
            ValueError: If the date is in the past.
        """
        if v < date.today():
            raise ValueError("Blackout date must be today or in the future")
        return v


class BlackoutDateResponse(BaseModel):
    """Schema for blackout date information in API responses.

    Represents a configured blackout date for a resource or system default.

    Attributes:
        id: The unique identifier of the blackout date record.
        resource_id: ID of the associated resource, or None for
            system-wide blackout.
        date: The blackout date.
        reason: Explanation for the blackout, or None.
        created_at: When the blackout was created.
    """

    id: int
    resource_id: int | None = None
    date: date
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimeSlot(BaseModel):
    """Represents a time slot with availability status.

    Used to communicate available and unavailable time periods.

    Attributes:
        start: Start time of the slot.
        end: End time of the slot.
        available: Whether the slot is available for booking.
    """

    start: datetime
    end: datetime
    available: bool


class AvailableSlotsResponse(BaseModel):
    """Response with available time slots for a specific date.

    Provides detailed availability information including business hours
    and blackout status.

    Attributes:
        date: The date for which slots are reported.
        slots: List of time slots with availability status.
        business_hours: Business hours configuration for this date,
            or None if using defaults.
        is_blackout: Whether this date is a blackout date.
        blackout_reason: Explanation for blackout, or None.
    """

    date: date
    slots: list[TimeSlot]
    business_hours: BusinessHoursResponse | None = None
    is_blackout: bool = False
    blackout_reason: str | None = None


# ============================================================================
# Approval Workflow Schemas
# ============================================================================


class ApprovalStatus(str, Enum):
    """Enumeration of approval request statuses.

    Tracks the state of reservation approval requests.

    Attributes:
        PENDING: Awaiting approver decision.
        APPROVED: Request was approved.
        REJECTED: Request was rejected.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ResourceApprovalUpdate(BaseModel):
    """Schema for updating resource approval settings.

    Configures whether a resource requires approval for reservations.

    Attributes:
        requires_approval: Whether reservations need approval.
        default_approver_id: ID of the default approver user, or None
            to require manual approver selection.
    """

    requires_approval: bool
    default_approver_id: int | None = None


class ReservationWithApprovalCreate(BaseModel):
    """Schema for creating a reservation that may require approval.

    Similar to ReservationCreate but includes an optional message
    for the approver.

    Attributes:
        resource_id: ID of the resource to reserve.
        start_time: When the reservation begins. Must be in the future.
        end_time: When the reservation ends. Must be after start_time.
        request_message: Optional message to the approver explaining
            the reservation need (max 500 characters).
    """

    resource_id: int
    start_time: datetime
    end_time: datetime
    request_message: str | None = Field(None, max_length=500)

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: datetime) -> datetime:
        """Validate that start time is in the future.

        Args:
            v: The start time to validate.

        Returns:
            The validated timezone-aware start time.

        Raises:
            ValueError: If start time is not in the future.
        """
        v = ensure_timezone_aware(v)
        if v <= utcnow():
            raise ValueError("Start time must be in the future")
        return v

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        """Validate that end time is after start time.

        Args:
            v: The end time to validate.
            info: Validation context with start time.

        Returns:
            The validated timezone-aware end time.

        Raises:
            ValueError: If end time is not after start time.
        """
        v = ensure_timezone_aware(v)
        start = info.data.get("start_time")
        if start:
            start = ensure_timezone_aware(start)
            if v <= start:
                raise ValueError("End time must be after start time")
        return v


class ApprovalRequestCreate(BaseModel):
    """Schema for creating an approval request.

    Associates a reservation with an approver and optional message.

    Attributes:
        reservation_id: ID of the reservation requiring approval.
        approver_id: ID of the user who can approve the request.
        request_message: Optional message explaining the request
            (max 500 characters).
    """

    reservation_id: int
    approver_id: int
    request_message: str | None = Field(None, max_length=500)


class ApprovalAction(BaseModel):
    """Schema for approving or rejecting a reservation.

    Used by approvers to respond to approval requests.

    Attributes:
        action: The action to take, must be "approve" or "reject".
        response_message: Optional message explaining the decision
            (max 500 characters).
    """

    action: str = Field(pattern="^(approve|reject)$")
    response_message: str | None = Field(None, max_length=500)


class ApprovalRequestResponse(BaseModel):
    """Schema for approval request information in API responses.

    Provides the current state of an approval request.

    Attributes:
        id: The unique identifier of the approval request.
        reservation_id: ID of the associated reservation.
        approver_id: ID of the designated approver.
        status: Current status (pending, approved, rejected).
        request_message: Message from the requester, or None.
        response_message: Message from the approver, or None.
        created_at: When the request was created.
        responded_at: When the approver responded, or None.
    """

    id: int
    reservation_id: int
    approver_id: int
    status: str
    request_message: str | None = None
    response_message: str | None = None
    created_at: datetime
    responded_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalRequestWithDetails(ApprovalRequestResponse):
    """Approval request with reservation and user details.

    Extends ApprovalRequestResponse with embedded related objects.

    Attributes:
        reservation: Full reservation details.
        requester_username: Username of the person requesting, or None.
        approver_username: Username of the approver, or None.
    """

    reservation: "ReservationResponse"
    requester_username: str | None = None
    approver_username: str | None = None


# ============================================================================
# Search Schemas
# ============================================================================


class ResourceSearchParams(BaseModel):
    """Parameters for searching and filtering resources.

    Provides comprehensive filtering options for resource discovery.

    Attributes:
        query: Text search query matching resource names.
        tags: List of tags to filter by (resources must have all tags).
        status: Filter by status (available, in_use, unavailable).
        available_only: If True, only return currently available resources.
        available_from: Filter resources available from this time.
        available_until: Filter resources available until this time.
        requires_approval: Filter by approval requirement setting.
        limit: Maximum results to return (1-100, default 50).
        offset: Number of results to skip for pagination (default 0).
    """

    query: str | None = Field(None, description="Text search query")
    tags: list[str] | None = Field(None, description="Filter by tags")
    status: str | None = Field(
        None, description="Filter by status (available, in_use, unavailable)"
    )
    available_only: bool = Field(False, description="Only show available resources")
    available_from: datetime | None = Field(
        None, description="Filter by availability start time"
    )
    available_until: datetime | None = Field(
        None, description="Filter by availability end time"
    )
    requires_approval: bool | None = Field(
        None, description="Filter by approval requirement"
    )
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class ReservationSearchParams(BaseModel):
    """Parameters for searching and filtering reservations.

    Provides comprehensive filtering options for reservation queries.

    Attributes:
        user_id: Filter by specific user ID.
        resource_id: Filter by specific resource ID.
        status: Filter by status (string or list of statuses).
        start_from: Filter reservations starting from this time.
        start_until: Filter reservations starting until this time.
        created_from: Filter by creation date (from).
        created_until: Filter by creation date (until).
        include_cancelled: If True, include cancelled reservations.
        limit: Maximum results to return (1-100, default 50).
        offset: Number of results to skip for pagination (default 0).
    """

    user_id: int | None = Field(None, description="Filter by user ID")
    resource_id: int | None = Field(None, description="Filter by resource ID")
    status: str | list[str] | None = Field(None, description="Filter by status")
    start_from: datetime | None = Field(
        None, description="Filter by reservation start time (from)"
    )
    start_until: datetime | None = Field(
        None, description="Filter by reservation start time (until)"
    )
    created_from: datetime | None = Field(
        None, description="Filter by creation date (from)"
    )
    created_until: datetime | None = Field(
        None, description="Filter by creation date (until)"
    )
    include_cancelled: bool = Field(False, description="Include cancelled reservations")
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class SavedSearchCreate(BaseModel):
    """Schema for creating a saved search.

    Allows users to save search configurations for reuse.

    Attributes:
        name: Display name for the saved search (1-100 characters).
        search_type: Type of search, either "resources" or "reservations".
        filters: Dictionary of filter parameters for the search.
    """

    name: str = Field(..., min_length=1, max_length=100)
    search_type: str = Field(..., pattern="^(resources|reservations)$")
    filters: dict


class SavedSearchResponse(BaseModel):
    """Schema for saved search information in API responses.

    Represents a user's saved search configuration.

    Attributes:
        id: The unique identifier of the saved search.
        name: Display name of the saved search.
        search_type: Type of search (resources or reservations).
        filters: Dictionary of saved filter parameters.
        created_at: When the saved search was created.
        updated_at: When the saved search was last modified.
    """

    id: int
    name: str
    search_type: str
    filters: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SearchSuggestionsResponse(BaseModel):
    """Schema for search autocomplete suggestions.

    Provides suggestions for resource names and tags based on
    partial input.

    Attributes:
        resources: List of matching resource name suggestions.
        tags: List of matching tag suggestions.
    """

    resources: list[str]
    tags: list[str]


class PopularTagResponse(BaseModel):
    """Schema for popular tag statistics.

    Represents a tag and its usage count for discovery features.

    Attributes:
        tag: The tag name.
        count: Number of resources using this tag.
    """

    tag: str
    count: int


# ============================================================================
# Label Schemas
# ============================================================================


class LabelCreate(BaseModel):
    """Schema for creating a new label.

    Validates label category and value constraints for creating normalized
    labels in the system.

    Attributes:
        category: Label category for grouping (e.g., 'environment', 'team').
            Must be 1-100 characters.
        value: Label value within the category (e.g., 'production', 'qa').
            Must be 1-200 characters.
        color: Hex color code for UI display (e.g., '#6366f1').
            Must be a valid 7-character hex color. Defaults to indigo.
        description: Optional description of the label's purpose.
    """

    category: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=200)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9A-Fa-f]{6}$")
    description: str | None = None

    @field_validator("category", "value")
    @classmethod
    def normalize_label_parts(cls, v: str) -> str:
        """Normalize category and value by trimming whitespace.

        Args:
            v: The string to normalize.

        Returns:
            The trimmed string.

        Raises:
            ValueError: If the trimmed string is empty.
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("Value cannot be empty or whitespace only")
        return stripped


class LabelUpdate(BaseModel):
    """Schema for updating an existing label.

    All fields are optional; only provided fields will be updated.

    Attributes:
        category: New category for the label, or None to keep unchanged.
        value: New value for the label, or None to keep unchanged.
        color: New hex color code, or None to keep unchanged.
        description: New description, or None to keep unchanged.
    """

    category: str | None = Field(None, min_length=1, max_length=100)
    value: str | None = Field(None, min_length=1, max_length=200)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    description: str | None = None

    @field_validator("category", "value")
    @classmethod
    def normalize_label_parts(cls, v: str | None) -> str | None:
        """Normalize category and value by trimming whitespace.

        Args:
            v: The string to normalize, or None.

        Returns:
            The trimmed string, or None.

        Raises:
            ValueError: If the trimmed string is empty.
        """
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("Value cannot be empty or whitespace only")
        return stripped


class LabelResponse(BaseModel):
    """Schema for label information in API responses.

    Provides complete label details including timestamps and computed fields.

    Attributes:
        id: The unique identifier of the label.
        category: Label category for grouping.
        value: Label value within the category.
        color: Hex color code for UI display.
        description: Description of the label's purpose, or None.
        full_name: Computed field in 'category:value' format.
        created_at: When the label was created.
        updated_at: When the label was last modified.
        resource_count: Number of resources with this label assigned.
    """

    id: int
    category: str
    value: str
    color: str
    description: str | None = None
    full_name: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    resource_count: int = 0

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, label, resource_count: int = 0) -> "LabelResponse":
        """Create a LabelResponse from a Label model instance.

        Args:
            label: The Label model instance.
            resource_count: Number of resources with this label.

        Returns:
            A LabelResponse instance.
        """
        return cls(
            id=label.id,
            category=label.category,
            value=label.value,
            color=label.color,
            description=label.description,
            full_name=label.full_name,
            created_at=label.created_at,
            updated_at=label.updated_at,
            resource_count=resource_count,
        )


class LabelMerge(BaseModel):
    """Schema for merging multiple labels into one.

    Allows administrators to consolidate duplicate or similar labels
    by merging their resource assignments into a target label.

    Attributes:
        source_label_ids: List of label IDs to merge from.
            These labels will be deleted after merging.
        target_label_id: The label ID to merge into.
            This label will receive all resource assignments.
    """

    source_label_ids: list[int] = Field(..., min_length=1)
    target_label_id: int

    @field_validator("source_label_ids")
    @classmethod
    def validate_source_labels(cls, v: list[int]) -> list[int]:
        """Validate source label IDs.

        Args:
            v: List of source label IDs.

        Returns:
            The validated list.

        Raises:
            ValueError: If the list is empty or contains duplicates.
        """
        if not v:
            raise ValueError("At least one source label is required")
        if len(v) != len(set(v)):
            raise ValueError("Duplicate source label IDs are not allowed")
        return v


class ResourceLabelsUpdate(BaseModel):
    """Schema for updating labels assigned to a resource.

    Allows administrators to set the complete list of labels for a resource,
    replacing any existing label assignments.

    Attributes:
        label_ids: List of label IDs to assign to the resource.
            Pass an empty list to remove all labels.
    """

    label_ids: list[int] = Field(default_factory=list)

    @field_validator("label_ids")
    @classmethod
    def validate_label_ids(cls, v: list[int]) -> list[int]:
        """Validate label IDs for uniqueness.

        Args:
            v: List of label IDs.

        Returns:
            The validated list with duplicates removed.
        """
        return list(set(v))


class LabelCategoryResponse(BaseModel):
    """Schema for label category information.

    Provides category details for filtering and grouping in the UI.

    Attributes:
        category: The category name.
        label_count: Number of labels in this category.
    """

    category: str
    label_count: int
