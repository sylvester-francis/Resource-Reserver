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

    # MFA fields
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(32), nullable=True)
    mfa_backup_codes = Column(JSON, nullable=True)  # List of backup codes

    # Email fields
    email = Column(String(255), unique=True, nullable=True, index=True)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    reservations = relationship("Reservation", back_populates="user")
    roles = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    oauth_clients = relationship(
        "OAuth2Client", back_populates="owner", cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


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
    recurrence_rule_id = Column(
        Integer, ForeignKey("recurrence_rules.id"), nullable=True
    )
    parent_reservation_id = Column(
        Integer, ForeignKey("reservations.id"), nullable=True
    )
    is_recurring_instance = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="reservations")
    resource = relationship("Resource", back_populates="reservations")
    recurrence_rule = relationship("RecurrenceRule", back_populates="reservations")
    parent_reservation = relationship("Reservation", remote_side=[id])

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


class RecurrenceRule(Base):
    __tablename__ = "recurrence_rules"

    id = Column(Integer, primary_key=True)
    frequency = Column(String, nullable=False)  # daily, weekly, monthly
    interval = Column(Integer, default=1)
    days_of_week = Column(JSON, nullable=True)  # [0-6] for weekly
    end_type = Column(String, nullable=False)  # never, on_date, after_count
    end_date = Column(DateTime(timezone=True), nullable=True)
    occurrence_count = Column(Integer, nullable=True)

    reservations = relationship("Reservation", back_populates="recurrence_rule")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    link = Column(String, nullable=True)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="notifications")


# ============================================================================
# RBAC Models
# ============================================================================


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Relationships
    user_roles = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="user_roles")


# ============================================================================
# OAuth2 Models
# ============================================================================


class OAuth2Client(Base):
    __tablename__ = "oauth2_clients"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(48), unique=True, nullable=False, index=True)
    client_secret = Column(String, nullable=False)  # Hashed
    client_name = Column(String(255), nullable=False)
    redirect_uris = Column(JSON, nullable=False)  # List of URIs
    grant_types = Column(String(255), nullable=False)  # Space-separated
    scope = Column(String(255), nullable=False)  # Space-separated scopes
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    owner = relationship("User", back_populates="oauth_clients")
    tokens = relationship(
        "OAuth2Token", back_populates="client", cascade="all, delete-orphan"
    )


class OAuth2AuthorizationCode(Base):
    __tablename__ = "oauth2_authorization_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(120), unique=True, nullable=False, index=True)
    client_id = Column(
        String(48), ForeignKey("oauth2_clients.client_id"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    redirect_uri = Column(Text, nullable=False)
    scope = Column(String(255), nullable=False)
    code_challenge = Column(String(128), nullable=True)  # PKCE
    code_challenge_method = Column(String(10), nullable=True)  # PKCE
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class OAuth2Token(Base):
    __tablename__ = "oauth2_tokens"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(
        String(48), ForeignKey("oauth2_clients.client_id"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Null for client_credentials
    token_type = Column(String(20), default="Bearer", nullable=False)
    access_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)
    scope = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    client = relationship("OAuth2Client", back_populates="tokens")


# ============================================================================
# Permission Models
# ============================================================================


class ResourcePermission(Base):
    __tablename__ = "resource_permissions"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Null = applies to role
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    action = Column(String(50), nullable=False)  # 'read', 'update', 'delete', 'reserve'
    created_at = Column(DateTime(timezone=True), default=utcnow)


# ============================================================================
# Refresh Token Model
# ============================================================================


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    revoked = Column(Boolean, default=False, nullable=False)
    family_id = Column(String(36), nullable=False, index=True)  # For token rotation

    # Relationships
    user = relationship("User", backref="refresh_tokens")


# ============================================================================
# Login Attempt Model (for account lockout)
# ============================================================================


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    success = Column(Boolean, nullable=False)
    attempt_time = Column(DateTime(timezone=True), default=utcnow)
    failure_reason = Column(
        String(100), nullable=True
    )  # e.g., "invalid_password", "account_locked"
