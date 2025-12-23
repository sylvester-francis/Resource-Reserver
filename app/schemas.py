"""Pydantic schemas for request/response validation."""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.utils.password import PasswordPolicy


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


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_more: bool
    total_count: int | None = None


class PaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=20, le=100, ge=1)
    sort_by: str | None = "created_at"
    sort_order: str | None = "desc"


class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
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
        username = ""
        if info.data:
            username = info.data.get("username") or ""
        is_valid, errors = PasswordPolicy.validate(v, username=username)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class SetupInitializeRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    existing_username: str | None = None

    @field_validator("username")
    @classmethod
    def validate_setup_username(cls, v: str | None) -> str | None:
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
    name: str
    tags: list[str] | None = []
    available: bool | None = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        name = v.strip()
        if not name or len(name) > 200:
            raise ValueError("Resource name must be 1-200 characters")
        return name


class ResourceResponse(BaseModel):
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
    available: bool

    model_config = ConfigDict(from_attributes=True)


class ReservationCreate(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: datetime) -> datetime:
        # Ensure timezone awareness
        v = ensure_timezone_aware(v)

        if v <= utcnow():
            raise ValueError("Start time must be in the future")
        return v

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
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

    model_config = ConfigDict(from_attributes=True)


class ReservationCancel(BaseModel):
    reason: str | None = None


class ResourceStatusUpdate(BaseModel):
    auto_reset_hours: int = 8

    @field_validator("auto_reset_hours")
    @classmethod
    def validate_auto_reset_hours(cls, v: int) -> int:
        if v < 1 or v > 168:  # 1 hour to 1 week
            raise ValueError("Auto reset hours must be between 1 and 168 (1 week)")
        return v


class NotificationType(str, Enum):
    RESERVATION_CONFIRMED = "reservation_confirmed"
    RESERVATION_CANCELLED = "reservation_cancelled"
    RESERVATION_REMINDER = "reservation_reminder"
    RESOURCE_AVAILABLE = "resource_available"
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class NotificationBase(BaseModel):
    type: NotificationType
    title: str
    message: str
    link: str | None = None


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationResponse(NotificationBase):
    id: int
    read: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
