"""SQLAlchemy database models for the Resource Reserver application.

This module defines all database models used by the Resource Reserver system,
including users, resources, reservations, authentication, and supporting entities.
The models use SQLAlchemy ORM with proper relationships, constraints, and indexes.

Features:
    - User management with MFA and email verification support
    - Resource management with hierarchical grouping and availability tracking
    - Reservation system with recurrence, approval workflows, and waitlists
    - Role-based access control (RBAC) with granular permissions
    - OAuth2 authentication with PKCE support
    - Audit logging and API quota management
    - Webhook integrations for external notifications
    - Business hours and blackout date management

Example:
    Creating a new user and resource::

        from app.models import User, Resource
        from app.database import SessionLocal

        db = SessionLocal()
        user = User(username="john_doe", hashed_password="...")
        resource = Resource(name="Conference Room A")
        db.add_all([user, resource])
        db.commit()

    Creating a reservation::

        from app.models import Reservation

        reservation = Reservation(
            user_id=user.id,
            resource_id=resource.id,
            start_time=datetime(2024, 1, 15, 9, 0),
            end_time=datetime(2024, 1, 15, 10, 0)
        )
        db.add(reservation)
        db.commit()

Author:
    Resource Reserver Development Team
"""

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
    """Get current UTC datetime that is timezone-aware.

    Returns:
        datetime: The current UTC datetime with timezone information attached.
    """
    return datetime.now(UTC)


class User(Base):
    """User account model for authentication and authorization.

    Represents a user in the system with support for multi-factor authentication,
    email notifications, calendar integration, and role-based access control.

    Attributes:
        id (int): Primary key identifier for the user.
        username (str): Unique username for login, max 50 characters.
        hashed_password (str): Bcrypt-hashed password string.
        mfa_enabled (bool): Whether MFA is enabled for this account.
        mfa_secret (str): TOTP secret key for MFA, max 32 characters.
        mfa_backup_codes (list): JSON list of one-time backup codes for MFA recovery.
        email (str): User's email address, max 255 characters, optional.
        email_verified (bool): Whether the email address has been verified.
        email_notifications (bool): Whether to send email notifications.
        reminder_hours (int): Hours before reservation to send reminder emails.
        calendar_token (str): Unique token for iCal feed access.
        reservations (list[Reservation]): User's reservations.
        roles (list[UserRole]): User's assigned roles.
        oauth_clients (list[OAuth2Client]): OAuth2 clients owned by this user.
        notifications (list[Notification]): User's notifications.
        waitlist_entries (list[Waitlist]): User's waitlist entries.
    """

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
    """System-wide configuration settings stored in the database.

    Provides a key-value store for application configuration that can be
    modified at runtime without restarting the application.

    Attributes:
        key (str): Primary key, the setting name, max 64 characters.
        value (str): The setting value as a string.
        updated_at (datetime): Timestamp of last modification.
    """

    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ResourceGroup(Base):
    """Resource group for organizing resources hierarchically.

    Allows resources to be organized into a tree structure with location
    information such as building, floor, and room.

    Attributes:
        id (int): Primary key identifier.
        name (str): Group name, max 200 characters.
        description (str): Optional description, max 500 characters.
        parent_id (int): Foreign key to parent group for hierarchy.
        building (str): Building name or identifier, max 200 characters.
        floor (str): Floor identifier, max 50 characters.
        room (str): Room identifier, max 100 characters.
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last modification timestamp.
        parent (ResourceGroup): Parent group in the hierarchy.
        children (list[ResourceGroup]): Child groups.
        resources (list[Resource]): Resources belonging to this group.
    """

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
    """Reservable resource in the system.

    Represents any entity that can be reserved, such as rooms, equipment,
    or vehicles. Supports hierarchical organization, tagging, availability
    status tracking, and approval workflows.

    Attributes:
        id (int): Primary key identifier.
        name (str): Unique resource name, max 200 characters.
        group_id (int): Foreign key to resource group.
        parent_id (int): Foreign key to parent resource for hierarchy.
        available (bool): Whether the resource is available for booking.
        tags (list): JSON list of tags for categorization.
        status (str): Current status: 'available', 'in_use', or 'unavailable'.
        unavailable_since (datetime): When resource became unavailable.
        auto_reset_hours (int): Hours after which unavailable status auto-resets.
        requires_approval (bool): Whether reservations require approval.
        default_approver_id (int): Foreign key to default approver user.
        reservations (list[Reservation]): Reservations for this resource.
        default_approver (User): Default approver for this resource.
        waitlist_entries (list[Waitlist]): Waitlist entries for this resource.
        business_hours (list[BusinessHours]): Operating hours configuration.
        blackout_dates (list[BlackoutDate]): Dates when resource is unavailable.
        group (ResourceGroup): Resource group this belongs to.
        parent (Resource): Parent resource in hierarchy.
        children (list[Resource]): Child resources.
    """

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
    resource_labels = relationship(
        "ResourceLabel", back_populates="resource", cascade="all, delete-orphan"
    )

    @property
    def is_available_for_reservation(self) -> bool:
        """Check if resource is available for new reservations.

        A resource is available if it is marked as available and its status
        is either 'available' or 'in_use' (but not 'unavailable').

        Returns:
            bool: True if the resource can accept new reservations.
        """
        return self.available and self.status in ["available", "in_use"]

    @property
    def is_currently_in_use(self) -> bool:
        """Check if resource is currently in use.

        Returns:
            bool: True if the resource status is 'in_use'.
        """
        return self.status == "in_use"

    @property
    def is_unavailable(self) -> bool:
        """Check if resource is unavailable for maintenance or repair.

        Returns:
            bool: True if the resource status is 'unavailable'.
        """
        return self.status == "unavailable"

    def set_unavailable(self, auto_reset_hours: int = None):
        """Set resource as unavailable with optional auto-reset.

        Marks the resource as unavailable and records the timestamp.
        Optionally configures automatic reset to available status.

        Args:
            auto_reset_hours: Hours after which to automatically reset
                to available status. If None, uses existing value.
        """
        self.status = "unavailable"
        self.unavailable_since = utcnow()
        if auto_reset_hours is not None:
            self.auto_reset_hours = auto_reset_hours

    def set_available(self):
        """Set resource as available.

        Resets the resource status to 'available' and clears the
        unavailable_since timestamp.
        """
        self.status = "available"
        self.unavailable_since = None

    def set_in_use(self):
        """Set resource as currently in use.

        Updates the resource status to 'in_use' to indicate an active
        reservation is using this resource.
        """
        self.status = "in_use"

    def should_auto_reset(self) -> bool:
        """Check if resource should be automatically reset to available.

        Determines if enough time has passed since the resource became
        unavailable to trigger an automatic reset based on auto_reset_hours.

        Returns:
            bool: True if the resource should be reset to available status.
        """
        if self.status != "unavailable" or not self.unavailable_since:
            return False

        now = utcnow()
        hours_since_unavailable = (now - self.unavailable_since).total_seconds() / 3600
        return hours_since_unavailable >= self.auto_reset_hours


class Reservation(Base):
    """Reservation of a resource for a specific time period.

    Represents a booking of a resource by a user for a defined time slot.
    Supports various statuses, recurrence patterns, and approval workflows.

    Attributes:
        id (int): Primary key identifier.
        user_id (int): Foreign key to the user making the reservation.
        resource_id (int): Foreign key to the reserved resource.
        start_time (datetime): Reservation start time with timezone.
        end_time (datetime): Reservation end time with timezone.
        status (str): Status: 'active', 'cancelled', 'expired',
            'pending_approval', or 'rejected'.
        created_at (datetime): Creation timestamp.
        cancelled_at (datetime): Cancellation timestamp if cancelled.
        cancellation_reason (str): Reason for cancellation.
        recurrence_rule_id (int): Foreign key to recurrence rule.
        parent_reservation_id (int): Foreign key to parent for recurring instances.
        is_recurring_instance (bool): Whether this is part of a recurring series.
        reminder_sent (bool): Whether a reminder email was sent.
        user (User): User who made the reservation.
        resource (Resource): Reserved resource.
        recurrence_rule (RecurrenceRule): Associated recurrence rule.
        parent_reservation (Reservation): Parent reservation for recurring instances.
        approval_request (ApprovalRequest): Associated approval request if any.
    """

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
        """Calculate the reservation duration in hours.

        Returns:
            float: Duration of the reservation in decimal hours.
        """
        return (self.end_time - self.start_time).total_seconds() / 3600

    @property
    def is_active(self) -> bool:
        """Check if reservation is currently active.

        Returns:
            bool: True if the reservation status is 'active'.
        """
        return self.status == "active"


class ReservationHistory(Base):
    """Historical record of actions taken on reservations.

    Tracks all modifications and status changes made to reservations
    for audit and debugging purposes.

    Attributes:
        id (int): Primary key identifier.
        reservation_id (int): Foreign key to the associated reservation.
        action (str): Action performed, e.g., 'created', 'modified', 'cancelled'.
        user_id (int): Foreign key to the user who performed the action.
        timestamp (datetime): When the action occurred.
        details (str): Additional details about the action.
    """

    __tablename__ = "reservation_history"

    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)  # noqa : E501
    action = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow)
    details = Column(Text)


class RecurrenceRule(Base):
    """Recurrence pattern definition for recurring reservations.

    Defines how a reservation should repeat, including frequency,
    interval, specific days, and end conditions.

    Attributes:
        id (int): Primary key identifier.
        frequency (str): Recurrence frequency: 'daily', 'weekly', or 'monthly'.
        interval (int): Number of frequency units between occurrences.
        days_of_week (list): JSON list of weekday numbers (0-6, Monday-Sunday)
            for weekly recurrence.
        end_type (str): How recurrence ends: 'never', 'on_date', or 'after_count'.
        end_date (datetime): End date for 'on_date' end type.
        occurrence_count (int): Number of occurrences for 'after_count' end type.
        reservations (list[Reservation]): Reservations using this rule.
    """

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
    """In-app notification for users.

    Stores notifications that appear in the user's notification center,
    such as reservation reminders, waitlist updates, and system messages.

    Attributes:
        id (int): Primary key identifier.
        user_id (int): Foreign key to the notification recipient.
        type (str): Notification type for categorization and styling.
        title (str): Notification title/headline.
        message (str): Notification body text.
        link (str): Optional URL to navigate to when clicked.
        read (bool): Whether the notification has been read.
        created_at (datetime): When the notification was created.
        user (User): Recipient user.
    """

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
    """Role definition for role-based access control.

    Defines a role that can be assigned to users to grant permissions.
    Standard roles include 'admin', 'manager', and 'user'.

    Attributes:
        id (int): Primary key identifier.
        name (str): Unique role name, max 50 characters.
        description (str): Optional role description.
        user_roles (list[UserRole]): User-role assignments for this role.
    """

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Relationships
    user_roles = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )


class UserRole(Base):
    """Association between users and roles.

    Many-to-many relationship table connecting users to their assigned roles.

    Attributes:
        id (int): Primary key identifier.
        user_id (int): Foreign key to the user.
        role_id (int): Foreign key to the role.
        user (User): Associated user.
        role (Role): Associated role.
    """

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
    """OAuth2 client application registration.

    Stores information about registered OAuth2 client applications that
    can authenticate users and access the API on their behalf.

    Attributes:
        id (int): Primary key identifier.
        client_id (str): Unique OAuth2 client identifier, max 48 characters.
        client_secret (str): Hashed client secret for authentication.
        client_name (str): Human-readable client name, max 255 characters.
        redirect_uris (list): JSON list of allowed redirect URIs.
        grant_types (str): Space-separated list of allowed grant types.
        scope (str): Space-separated list of allowed scopes.
        owner_id (int): Foreign key to the client owner user.
        created_at (datetime): When the client was registered.
        owner (User): User who owns this client.
        tokens (list[OAuth2Token]): Tokens issued to this client.
    """

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
    """OAuth2 authorization code for the authorization code grant flow.

    Temporary code issued during OAuth2 authorization that can be exchanged
    for an access token. Supports PKCE for enhanced security.

    Attributes:
        id (int): Primary key identifier.
        code (str): Unique authorization code, max 120 characters.
        client_id (str): Foreign key to the OAuth2 client.
        user_id (int): Foreign key to the authorizing user.
        redirect_uri (str): Redirect URI for this authorization.
        scope (str): Authorized scopes, space-separated.
        code_challenge (str): PKCE code challenge, max 128 characters.
        code_challenge_method (str): PKCE method: 'plain' or 'S256'.
        expires_at (datetime): When the code expires.
        used (bool): Whether the code has been used.
        created_at (datetime): When the code was issued.
    """

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
    """OAuth2 access and refresh token pair.

    Stores issued OAuth2 tokens that grant API access. Tokens can be
    revoked and have configurable expiration times.

    Attributes:
        id (int): Primary key identifier.
        client_id (str): Foreign key to the OAuth2 client.
        user_id (int): Foreign key to the token owner (None for client credentials).
        token_type (str): Token type, typically 'Bearer'.
        access_token (str): Unique access token, max 255 characters.
        refresh_token (str): Unique refresh token, max 255 characters.
        scope (str): Granted scopes, space-separated.
        expires_at (datetime): When the access token expires.
        revoked (bool): Whether the token has been revoked.
        created_at (datetime): When the token was issued.
        client (OAuth2Client): Associated OAuth2 client.
    """

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
    """Fine-grained permission for resource access control.

    Defines specific permissions on resources for either individual users
    or roles. Allows granular control over who can perform which actions.

    Attributes:
        id (int): Primary key identifier.
        resource_id (int): Foreign key to the resource.
        user_id (int): Foreign key to user (None if role-based).
        role_id (int): Foreign key to role (None if user-based).
        action (str): Permitted action: 'read', 'update', 'delete', or 'reserve'.
        created_at (datetime): When the permission was created.
    """

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
    """JWT refresh token for session management.

    Stores refresh tokens that can be used to obtain new access tokens
    without re-authentication. Supports token rotation and family tracking
    for security.

    Attributes:
        id (str): Primary key, UUID string.
        user_id (int): Foreign key to the token owner.
        token_hash (str): SHA-256 hash of the token, max 64 characters.
        expires_at (datetime): When the token expires.
        created_at (datetime): When the token was issued.
        revoked (bool): Whether the token has been revoked.
        family_id (str): UUID for token rotation family tracking.
        user (User): Token owner.
    """

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
    """Record of login attempts for security monitoring.

    Tracks all login attempts, both successful and failed, to enable
    account lockout policies and security auditing.

    Attributes:
        id (int): Primary key identifier.
        username (str): Username attempted, max 50 characters.
        ip_address (str): Client IP address, max 45 characters (IPv6 compatible).
        success (bool): Whether the login attempt succeeded.
        attempt_time (datetime): When the attempt occurred.
        failure_reason (str): Reason for failure if applicable, e.g.,
            'invalid_password', 'account_locked'.
    """

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
    """Waitlist entry for desired resource reservations.

    Allows users to join a queue for resources that are currently booked.
    When a slot becomes available, users are offered the reservation in
    queue order.

    Attributes:
        id (int): Primary key identifier.
        resource_id (int): Foreign key to the desired resource.
        user_id (int): Foreign key to the waiting user.
        desired_start (datetime): Desired reservation start time.
        desired_end (datetime): Desired reservation end time.
        flexible_time (bool): Whether user can accept different times.
        status (str): Status: 'waiting', 'offered', 'expired', 'fulfilled',
            or 'cancelled'.
        position (int): Queue position.
        created_at (datetime): When the entry was created.
        offered_at (datetime): When a slot was offered.
        offer_expires_at (datetime): When the current offer expires.
        resource (Resource): Desired resource.
        user (User): Waiting user.
    """

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
    """Operating hours configuration for resources.

    Defines when resources are available for booking on each day of the week.
    Can be set globally (resource_id=None) or per-resource.

    Attributes:
        id (int): Primary key identifier.
        resource_id (int): Foreign key to resource (None for global default).
        day_of_week (int): Day number, 0=Monday through 6=Sunday.
        open_time (time): Opening time.
        close_time (time): Closing time.
        is_closed (bool): Whether the resource is closed on this day.
        resource (Resource): Associated resource if not global.
    """

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
    """Dates when resources are unavailable for booking.

    Defines specific dates when resources cannot be reserved, such as
    holidays, maintenance windows, or special events.

    Attributes:
        id (int): Primary key identifier.
        resource_id (int): Foreign key to resource (None applies to all).
        date (date): The blackout date.
        reason (str): Reason for the blackout, max 255 characters.
        created_at (datetime): When the blackout was created.
        resource (Resource): Associated resource if not global.
    """

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
    """Approval request for reservations requiring authorization.

    Created when a user requests a reservation on a resource that requires
    approval. An approver can then approve or reject the request.

    Attributes:
        id (int): Primary key identifier.
        reservation_id (int): Foreign key to the pending reservation.
        approver_id (int): Foreign key to the designated approver.
        status (str): Status: 'pending', 'approved', or 'rejected'.
        request_message (str): Optional message from the requester.
        response_message (str): Optional response from the approver.
        created_at (datetime): When the request was created.
        responded_at (datetime): When the approver responded.
        reservation (Reservation): Associated reservation.
        approver (User): Designated approver.
    """

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
    """User's saved search filters for quick access.

    Allows users to save commonly used search criteria for resources
    or reservations to quickly apply them later.

    Attributes:
        id (int): Primary key identifier.
        user_id (int): Foreign key to the search owner.
        name (str): User-defined name for the search, max 100 characters.
        search_type (str): Type of search: 'resources' or 'reservations'.
        filters (dict): JSON object containing search filter criteria.
        created_at (datetime): When the search was saved.
        updated_at (datetime): When the search was last modified.
        user (User): Search owner.
    """

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
    """Comprehensive audit log for tracking all system actions.

    Records detailed information about every significant action in the
    system for security auditing, debugging, and compliance purposes.

    Attributes:
        id (int): Primary key identifier.
        timestamp (datetime): When the action occurred.
        user_id (int): Foreign key to the acting user (None for anonymous).
        username (str): Denormalized username for historical reference.
        action (str): Action type, e.g., 'create', 'update', 'delete', 'login'.
        entity_type (str): Type of entity affected, e.g., 'reservation', 'resource'.
        entity_id (int): ID of the affected entity.
        entity_name (str): Name/description of the entity for context.
        ip_address (str): Client IP address, max 45 characters.
        user_agent (str): Client user agent string, max 500 characters.
        request_method (str): HTTP method: GET, POST, PUT, DELETE, etc.
        request_path (str): Request URL path, max 500 characters.
        old_values (dict): JSON of previous entity state.
        new_values (dict): JSON of new entity state.
        details (str): Human-readable description of the action.
        success (bool): Whether the action succeeded.
        error_message (str): Error message if the action failed.
        user (User): Acting user.
    """

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
    """API usage quotas and limits per user.

    Tracks and enforces rate limits and daily quotas for API access.
    Supports tier-based limits with optional per-user overrides.

    Attributes:
        id (int): Primary key identifier.
        user_id (int): Foreign key to the user (unique).
        tier (str): Access tier: 'anonymous', 'authenticated', 'premium', or 'admin'.
        custom_rate_limit (int): Custom requests per minute limit.
        custom_daily_quota (int): Custom requests per day limit.
        daily_request_count (int): Current day's request count.
        last_request_date (date): Date of last request for daily reset.
        total_requests (int): Lifetime request count.
        quota_reset_notified (bool): Whether user was notified of quota reset.
        created_at (datetime): When the quota record was created.
        updated_at (datetime): When the quota was last updated.
        user (User): Associated user.
    """

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
    """Detailed API usage log for analytics.

    Records individual API requests for usage analytics, performance
    monitoring, and troubleshooting.

    Attributes:
        id (int): Primary key identifier.
        user_id (int): Foreign key to the requesting user.
        timestamp (datetime): When the request was made.
        endpoint (str): API endpoint path, max 500 characters.
        method (str): HTTP method, max 10 characters.
        status_code (int): HTTP response status code.
        response_time_ms (int): Response time in milliseconds.
        rate_limit (int): Rate limit at time of request.
        rate_remaining (int): Remaining requests in rate limit window.
        ip_address (str): Client IP address, max 45 characters.
        user (User): Requesting user.
    """

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
    """Webhook configuration for external integrations.

    Allows users to register webhook endpoints that receive notifications
    when specific events occur in the system.

    Attributes:
        id (int): Primary key identifier.
        user_id (int): Foreign key to the webhook owner.
        url (str): Webhook endpoint URL, max 500 characters.
        secret (str): HMAC secret for signing payloads, max 64 characters.
        events (list): JSON list of subscribed event types.
        description (str): Optional description, max 255 characters.
        is_active (bool): Whether the webhook is active.
        created_at (datetime): When the webhook was created.
        updated_at (datetime): When the webhook was last modified.
        user (User): Webhook owner.
        deliveries (list[WebhookDelivery]): Delivery attempt records.
    """

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
    """Record of webhook delivery attempts.

    Tracks each attempt to deliver a webhook payload, including success/failure
    status, response information, and retry scheduling.

    Attributes:
        id (int): Primary key identifier.
        webhook_id (int): Foreign key to the webhook configuration.
        event_type (str): Type of event being delivered.
        payload (dict): JSON payload sent to the webhook.
        status (str): Delivery status: 'pending', 'delivered', or 'failed'.
        status_code (int): HTTP response status code.
        response_body (str): Truncated response body, max 1000 characters.
        error_message (str): Error message if delivery failed.
        created_at (datetime): When the delivery was created.
        delivered_at (datetime): When successful delivery occurred.
        next_retry_at (datetime): When to retry if failed.
        retry_count (int): Number of retry attempts made.
        webhook (Webhook): Associated webhook configuration.
    """

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


# ============================================================================
# Label Models
# ============================================================================


class Label(Base):
    """Label for categorizing and organizing resources.

    Labels provide a normalized tagging system for resources, allowing
    administrators to create consistent categorization with color-coded
    visual indicators for the UI.

    Attributes:
        id (int): Primary key identifier.
        category (str): Label category for grouping (e.g., 'environment', 'team').
        value (str): Label value within the category (e.g., 'production', 'qa').
        color (str): Hex color code for UI display (e.g., '#6366f1').
        description (str): Optional description of the label's purpose.
        created_at (datetime): When the label was created.
        updated_at (datetime): When the label was last modified.
        resources (list[Resource]): Resources with this label assigned.
    """

    __tablename__ = "labels"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    value = Column(String(200), nullable=False)
    color = Column(String(7), default="#6366f1", nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    resource_labels = relationship(
        "ResourceLabel", back_populates="label", cascade="all, delete-orphan"
    )

    # Unique constraint on category + value
    from sqlalchemy import UniqueConstraint

    __table_args__ = (
        UniqueConstraint("category", "value", name="uq_label_category_value"),
    )

    @property
    def full_name(self) -> str:
        """Get the full label name as category:value format.

        Returns:
            str: The label in 'category:value' format.
        """
        return f"{self.category}:{self.value}"


class ResourceLabel(Base):
    """Association table for many-to-many relationship between resources and labels.

    Links resources to labels, allowing each resource to have multiple labels
    and each label to be applied to multiple resources.

    Attributes:
        id (int): Primary key identifier.
        resource_id (int): Foreign key to the resource.
        label_id (int): Foreign key to the label.
        created_at (datetime): When the label was assigned to the resource.
        resource (Resource): The associated resource.
        label (Label): The associated label.
    """

    __tablename__ = "resource_labels"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    label_id = Column(
        Integer, ForeignKey("labels.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    resource = relationship("Resource", back_populates="resource_labels")
    label = relationship("Label", back_populates="resource_labels")

    # Unique constraint to prevent duplicate assignments
    from sqlalchemy import UniqueConstraint

    __table_args__ = (
        UniqueConstraint("resource_id", "label_id", name="uq_resource_label"),
    )
