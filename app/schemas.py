"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime, timedelta, timezone
from typing import List, Optional


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
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class ResourceCreate(BaseModel):
    name: str
    tags: Optional[List[str]] = []
    available: Optional[bool] = True

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
    available: bool
    tags: List[str]

    model_config = ConfigDict(from_attributes=True)


class ReservationCreate(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        start = info.data.get("start_time")
        if start:
            if v <= start:
                raise ValueError("End time must be after start time")

            duration = v - start
            if duration > timedelta(days=7):
                raise ValueError("Reservation cannot exceed 7 days")
            if duration < timedelta(minutes=15):
                raise ValueError("Reservation must be at least 15 minutes")

        return v

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: datetime) -> datetime:
        if v <= datetime.now(timezone.utc):
            raise ValueError("Start time must be in the future")
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
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReservationCancel(BaseModel):
    reason: Optional[str] = None
