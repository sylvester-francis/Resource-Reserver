"""Database models with proper relationships and constraints."""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    """Get current UTC datetime that's timezone-aware."""
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)

    # Relationships
    reservations = relationship("Reservation", back_populates="user")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    available = Column(Boolean, default=True, nullable=False)
    tags = Column(JSON, default=list)
    status = Column(String(20), default="available", nullable=False)
    unavailable_since = Column(DateTime(timezone=True))
    auto_reset_hours = Column(Integer, default=8)

    # Relationships
    reservations = relationship("Reservation", back_populates="resource")

    @property
    def is_available_for_reservation(self) -> bool:
        """Check if resource is available for new reservations."""
        return self.available and self.status in ["available", "in_use"]

    @property
    def is_currently_in_use(self) -> bool:
        """Check if resource is currently in use."""
        return self.status == "in_use"

    @property
    def is_unavailable(self) -> bool:
        """Check if resource is unavailable (maintenance/repair)."""
        return self.status == "unavailable"

    def set_unavailable(self, auto_reset_hours: int = None):
        """Set resource as unavailable with optional auto-reset."""
        self.status = "unavailable"
        self.unavailable_since = utcnow()
        if auto_reset_hours is not None:
            self.auto_reset_hours = auto_reset_hours

    def set_available(self):
        """Set resource as available."""
        self.status = "available"
        self.unavailable_since = None

    def set_in_use(self):
        """Set resource as in use."""
        self.status = "in_use"

    def should_auto_reset(self) -> bool:
        """Check if resource should be automatically reset to available."""
        if self.status != "unavailable" or not self.unavailable_since:
            return False

        now = utcnow()
        hours_since_unavailable = (now - self.unavailable_since).total_seconds() / 3600
        return hours_since_unavailable >= self.auto_reset_hours


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    cancelled_at = Column(DateTime(timezone=True))
    cancellation_reason = Column(Text)

    # Relationships
    user = relationship("User", back_populates="reservations")
    resource = relationship("Resource", back_populates="reservations")

    @property
    def duration_hours(self) -> float:
        """Calculate duration in hours."""
        return (self.end_time - self.start_time).total_seconds() / 3600

    @property
    def is_active(self) -> bool:
        """Check if reservation is currently active."""
        return self.status == "active"


class ReservationHistory(Base):
    __tablename__ = "reservation_history"

    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)  # noqa : E501
    action = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow)
    details = Column(Text)
