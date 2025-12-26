"""Database models with proper relationships and constraints."""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
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

    # Email notification preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    reminder_hours = Column(
        Integer, default=24, nullable=False
    )  # Hours before reservation

    # Calendar integration
    calendar_token = Column(String(64), unique=True, nullable=True, index=True)

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
    waitlist_entries = relationship(
        "Waitlist", back_populates="user", cascade="all, delete-orphan"
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ResourceGroup(Base):
    """Resource group for organizing resources hierarchically."""

    __tablename__ = "resource_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)

    # Hierarchy - parent group for nesting
    parent_id = Column(Integer, ForeignKey("resource_groups.id"), nullable=True)

    # Location fields
    building = Column(String(200), nullable=True)
    floor = Column(String(50), nullable=True)
    room = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    parent = relationship(
        "ResourceGroup", remote_side="ResourceGroup.id", back_populates="children"
    )
    children = relationship("ResourceGroup", back_populates="parent")
    resources = relationship("Resource", back_populates="group")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)

    # Group/hierarchy fields
    group_id = Column(Integer, ForeignKey("resource_groups.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey("resources.id"), nullable=True)
    available = Column(Boolean, default=True, nullable=False)
    tags = Column(JSON, default=list)
    status = Column(String(20), default="available", nullable=False)
    unavailable_since = Column(DateTime(timezone=True))
    auto_reset_hours = Column(Integer, default=8)

    # Approval workflow fields
    requires_approval = Column(Boolean, default=False, nullable=False)
    default_approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    reservations = relationship("Reservation", back_populates="resource")
    default_approver = relationship("User", foreign_keys=[default_approver_id])
    waitlist_entries = relationship(
        "Waitlist", back_populates="resource", cascade="all, delete-orphan"
    )
    business_hours = relationship(
        "BusinessHours", back_populates="resource", cascade="all, delete-orphan"
    )
    blackout_dates = relationship(
        "BlackoutDate", back_populates="resource", cascade="all, delete-orphan"
    )
    group = relationship("ResourceGroup", back_populates="resources")
    parent = relationship(
        "Resource", remote_side="Resource.id", back_populates="children"
    )
    children = relationship("Resource", back_populates="parent")

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
    status = Column(
        String(20), default="active", nullable=False
    )  # active, cancelled, expired, pending_approval, rejected
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

    # Email reminder tracking
    reminder_sent = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="reservations")
    resource = relationship("Resource", back_populates="reservations")
    recurrence_rule = relationship("RecurrenceRule", back_populates="reservations")
    parent_reservation = relationship("Reservation", remote_side=[id])
    approval_request = relationship(
        "ApprovalRequest", back_populates="reservation", uselist=False
    )

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


# ============================================================================
# Waitlist Model
# ============================================================================


class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    desired_start = Column(DateTime(timezone=True), nullable=False)
    desired_end = Column(DateTime(timezone=True), nullable=False)
    flexible_time = Column(Boolean, default=False)  # Can adjust time if needed
    status = Column(
        String(20), default="waiting"
    )  # waiting, offered, expired, fulfilled, cancelled
    position = Column(Integer, nullable=False)  # Queue position
    created_at = Column(DateTime(timezone=True), default=utcnow)
    offered_at = Column(DateTime(timezone=True), nullable=True)
    offer_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    resource = relationship("Resource", back_populates="waitlist_entries")
    user = relationship("User", back_populates="waitlist_entries")


# ============================================================================
# Business Hours Models
# ============================================================================


class BusinessHours(Base):
    """Operating hours for resources."""

    __tablename__ = "business_hours"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(
        Integer, ForeignKey("resources.id"), nullable=True
    )  # null = global default
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    open_time = Column(Time, nullable=False)
    close_time = Column(Time, nullable=False)
    is_closed = Column(Boolean, default=False)  # For marking specific days as closed

    # Relationships
    resource = relationship("Resource", back_populates="business_hours")


class BlackoutDate(Base):
    """Dates when resources are unavailable (holidays, maintenance, etc.)."""

    __tablename__ = "blackout_dates"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(
        Integer, ForeignKey("resources.id"), nullable=True
    )  # null = applies to all
    date = Column(Date, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    resource = relationship("Resource", back_populates="blackout_dates")


# ============================================================================
# Approval Workflow Models
# ============================================================================


class ApprovalRequest(Base):
    """Approval request for reservations requiring approval."""

    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(
        Integer, ForeignKey("reservations.id"), nullable=False, unique=True
    )
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending, approved, rejected
    request_message = Column(Text, nullable=True)  # Message from requester
    response_message = Column(Text, nullable=True)  # Comment from approver
    created_at = Column(DateTime(timezone=True), default=utcnow)
    responded_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    reservation = relationship("Reservation", back_populates="approval_request")
    approver = relationship("User", foreign_keys=[approver_id])


# ============================================================================
# Saved Search Models
# ============================================================================


class SavedSearch(Base):
    """User's saved search filters."""

    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    search_type = Column(String(20), nullable=False)  # "resources" or "reservations"
    filters = Column(JSON, nullable=False)  # Search filters as JSON
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", backref="saved_searches")


# ============================================================================
# Audit Log Model
# ============================================================================


class AuditLog(Base):
    """Comprehensive audit log for tracking all system actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)

    # User information
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Null for anonymous
    username = Column(String(50), nullable=True)  # Denormalized for history

    # Action details
    action = Column(
        String(50), nullable=False, index=True
    )  # e.g., "create", "update", "delete", "login"
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # e.g., "reservation", "resource", "user"
    entity_id = Column(Integer, nullable=True)  # ID of affected entity
    entity_name = Column(String(255), nullable=True)  # Name/description for context

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    request_path = Column(String(500), nullable=True)

    # Change details
    old_values = Column(JSON, nullable=True)  # Previous state
    new_values = Column(JSON, nullable=True)  # New state
    details = Column(Text, nullable=True)  # Human-readable description

    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", backref="audit_logs")


# ============================================================================
# API Quota Models
# ============================================================================


class APIQuota(Base):
    """API usage quotas and limits per user."""

    __tablename__ = "api_quotas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Tier-based limits
    tier = Column(
        String(20), default="authenticated", nullable=False
    )  # anonymous, authenticated, premium, admin

    # Custom limits (override tier defaults if set)
    custom_rate_limit = Column(Integer, nullable=True)  # Requests per minute
    custom_daily_quota = Column(Integer, nullable=True)  # Requests per day

    # Usage tracking
    daily_request_count = Column(Integer, default=0, nullable=False)
    last_request_date = Column(Date, nullable=True)
    total_requests = Column(Integer, default=0, nullable=False)

    # Quota management
    quota_reset_notified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", backref="api_quota")


class APIUsageLog(Base):
    """Detailed API usage log for analytics."""

    __tablename__ = "api_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)

    # Request details
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)

    # Rate limit info at time of request
    rate_limit = Column(Integer, nullable=True)
    rate_remaining = Column(Integer, nullable=True)

    # IP and user agent for analytics
    ip_address = Column(String(45), nullable=True)

    # Relationships
    user = relationship("User", backref="api_usage_logs")


# ============================================================================
# Webhook Models
# ============================================================================


class Webhook(Base):
    """Webhook configuration for external integrations."""

    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Configuration
    url = Column(String(500), nullable=False)
    secret = Column(String(64), nullable=False)  # For HMAC signing
    events = Column(JSON, nullable=False)  # List of subscribed event types
    description = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", backref="webhooks")
    deliveries = relationship(
        "WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan"
    )


class WebhookDelivery(Base):
    """Record of webhook delivery attempts."""

    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)

    # Delivery status
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending, delivered, failed
    status_code = Column(Integer, nullable=True)  # HTTP response code
    response_body = Column(String(1000), nullable=True)  # Truncated response
    error_message = Column(String(500), nullable=True)

    # Timing
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")
