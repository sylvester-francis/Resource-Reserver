# app/schemas.py
"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from typing import List, Optional


class UserCreate(BaseModel):
    username: str
    password: str

    @validator("username")
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3-50 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, hyphens and underscores"  # noqa : E501
            )
        return v.lower()  # Convert to lowercase

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class ResourceCreate(BaseModel):
    name: str
    tags: Optional[List[str]] = []
    available: Optional[bool] = True

    @validator("name")
    def validate_name(cls, v):
        name = v.strip()
        if not name or len(name) > 200:
            raise ValueError("Resource name must be 1-200 characters")
        return name


class ResourceResponse(BaseModel):
    id: int
    name: str
    available: bool
    tags: List[str]

    class Config:
        from_attributes = True


class ReservationCreate(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime

    @validator("end_time")
    def validate_end_time(cls, v, values):
        if "start_time" in values:
            if v <= values["start_time"]:
                raise ValueError("End time must be after start time")

            duration = v - values["start_time"]
            if duration > timedelta(days=7):
                raise ValueError("Reservation cannot exceed 7 days")
            if duration < timedelta(minutes=15):
                raise ValueError("Reservation must be at least 15 minutes")

        return v

    @validator("start_time")
    def validate_start_time(cls, v):
        if v <= datetime.utcnow():
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

    class Config:
        from_attributes = True


class ReservationCancel(BaseModel):
    reason: Optional[str] = None
