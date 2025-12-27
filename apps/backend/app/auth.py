"""Authentication and authorization utilities for the Resource Reserver application.

This module provides comprehensive authentication and authorization functionality
including password hashing, JWT token management, account lockout protection,
and refresh token handling with rotation support.

Features:
    - Secure password hashing using bcrypt via passlib
    - JWT access token creation and validation
    - Refresh token management with token rotation and family tracking
    - Account lockout protection against brute-force attacks
    - Case-insensitive username handling
    - Login attempt logging and tracking

Example:
    Basic authentication flow::

        from app.auth import authenticate_user_with_lockout, create_access_token
        from app.database import get_db

        # Authenticate user with lockout protection
        db = next(get_db())
        user, error = authenticate_user_with_lockout(
            db, "username", "password", ip_address="192.168.1.1"
        )

        if user:
            # Create access token
            access_token = create_access_token(data={"sub": user.username})

    Token refresh flow::

        from app.auth import verify_refresh_token, rotate_refresh_token

        # Verify and rotate refresh token
        old_token, user = verify_refresh_token(db, raw_refresh_token)
        new_refresh_token = rotate_refresh_token(db, old_token)

Note:
    Environment variables can be used to configure token expiration times
    and the secret key used for JWT encoding.

Attributes:
    SECRET_KEY (str): Secret key for JWT encoding. Should be changed in production.
    ALGORITHM (str): Algorithm used for JWT encoding. Defaults to "HS256".
    ACCESS_TOKEN_EXPIRE_MINUTES (int): Access token expiration time in minutes.
    REFRESH_TOKEN_EXPIRE_DAYS (int): Refresh token expiration time in days.
    pwd_context (CryptContext): Passlib context for password hashing using bcrypt.
    oauth2_scheme (OAuth2PasswordBearer): FastAPI OAuth2 scheme for token extraction.

Author:
    Resource Reserver Development Team
"""

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# Security utilities
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Uses the bcrypt algorithm via passlib for secure password hashing.
    The resulting hash includes the salt and can be verified using
    the verify_password function.

    Args:
        password: The plain text password to hash.

    Returns:
        The bcrypt hashed password string including salt and algorithm info.

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> hashed.startswith("$2b$")
        True
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against its bcrypt hash.

    Performs a constant-time comparison to prevent timing attacks.

    Args:
        plain_password: The plain text password to verify.
        hashed_password: The bcrypt hashed password to verify against.

    Returns:
        True if the password matches the hash, False otherwise.

    Example:
        >>> hashed = hash_password("correct_password")
        >>> verify_password("correct_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:  # noqa : E501
    """Create a JWT access token with the specified payload.

    Generates a signed JWT token containing the provided data and an
    expiration timestamp. The token is signed using the configured
    SECRET_KEY and ALGORITHM.

    Args:
        data: Dictionary of claims to include in the token payload.
            Typically includes "sub" (subject) with the username.
        expires_delta: Optional custom expiration time. If not provided,
            defaults to ACCESS_TOKEN_EXPIRE_MINUTES from configuration.

    Returns:
        The encoded JWT access token as a string.

    Example:
        >>> token = create_access_token(
        ...     data={"sub": "johndoe"},
        ...     expires_delta=timedelta(minutes=15)
        ... )
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # noqa : E501

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, username: str, password: str) -> models.User | None:
    """Authenticate a user with username and password.

    Performs basic credential validation without account lockout checking.
    Username comparison is case-insensitive.

    Note:
        This function does NOT check for account lockout.
        Use authenticate_user_with_lockout() for login endpoints to ensure
        brute-force protection is applied.

    Args:
        db: SQLAlchemy database session.
        username: The username to authenticate. Case-insensitive.
        password: The plain text password to verify.

    Returns:
        The User model instance if authentication succeeds, None otherwise.

    Example:
        >>> user = authenticate_user(db, "JohnDoe", "password123")
        >>> if user:
        ...     print(f"Authenticated: {user.username}")
    """
    # Normalize the username to lowercase for case-insensitive comparison
    normalized_username = username.lower()
    user = get_user_by_username(db, normalized_username)

    if not user or not verify_password(password, user.hashed_password):
        return None

    return user


# ============================================================================
# Account Lockout Functions
# ============================================================================


def get_failed_login_attempts(
    db: Session, username: str, window_minutes: int = 15
) -> int:
    """Get the count of failed login attempts within the lockout window.

    Queries the LoginAttempt table to count failed authentication attempts
    for the specified user within the configured lockout duration window.

    Args:
        db: SQLAlchemy database session.
        username: Username to check failed attempts for. Case-insensitive.
        window_minutes: Time window in minutes to check. Note: This parameter
            is overridden by PasswordPolicy.LOCKOUT_DURATION_MINUTES.

    Returns:
        The number of failed login attempts within the time window.

    Example:
        >>> failed_count = get_failed_login_attempts(db, "johndoe")
        >>> if failed_count >= 5:
        ...     print("Too many failed attempts")
    """
    from app.utils.password import PasswordPolicy

    # Use policy-defined window instead of parameter
    window_minutes = PasswordPolicy.LOCKOUT_DURATION_MINUTES
    cutoff_time = datetime.now(UTC) - timedelta(minutes=window_minutes)

    return (
        db.query(models.LoginAttempt)
        .filter(
            models.LoginAttempt.username == username.lower(),
            models.LoginAttempt.success == False,  # noqa: E712
            models.LoginAttempt.attempt_time >= cutoff_time,
        )
        .count()
    )


def is_account_locked(db: Session, username: str) -> tuple[bool, int | None]:
    """Check if an account is locked due to excessive failed login attempts.

    Determines whether the account has exceeded the maximum allowed failed
    login attempts within the lockout window. If locked, calculates the
    remaining lockout time.

    Args:
        db: SQLAlchemy database session.
        username: Username to check lockout status for. Case-insensitive.

    Returns:
        A tuple containing:
            - bool: True if the account is locked, False otherwise.
            - int | None: Minutes remaining in lockout period, or None if not locked.

    Example:
        >>> locked, remaining = is_account_locked(db, "johndoe")
        >>> if locked:
        ...     print(f"Account locked for {remaining} more minutes")
    """
    from app.utils.password import PasswordPolicy

    failed_attempts = get_failed_login_attempts(db, username)

    if failed_attempts >= PasswordPolicy.MAX_LOGIN_ATTEMPTS:
        # Find the most recent failed attempt to calculate remaining lockout time
        latest_attempt = (
            db.query(models.LoginAttempt)
            .filter(
                models.LoginAttempt.username == username.lower(),
                models.LoginAttempt.success == False,  # noqa: E712
            )
            .order_by(models.LoginAttempt.attempt_time.desc())
            .first()
        )

        if latest_attempt:
            # Handle timezone-naive datetimes from database
            attempt_time = latest_attempt.attempt_time
            if attempt_time.tzinfo is None:
                attempt_time = attempt_time.replace(tzinfo=UTC)

            lockout_end = attempt_time + timedelta(
                minutes=PasswordPolicy.LOCKOUT_DURATION_MINUTES
            )
            now = datetime.now(UTC)

            if now < lockout_end:
                remaining = int((lockout_end - now).total_seconds() / 60) + 1
                return True, remaining

    return False, None


def record_login_attempt(
    db: Session,
    username: str,
    success: bool,
    ip_address: str | None = None,
    failure_reason: str | None = None,
) -> models.LoginAttempt:
    """Record a login attempt in the database for security auditing.

    Creates a LoginAttempt record to track authentication attempts,
    both successful and failed. This data is used for account lockout
    decisions and security monitoring.

    Args:
        db: SQLAlchemy database session.
        username: Username that attempted login. Will be normalized to lowercase.
        success: Whether the login attempt was successful.
        ip_address: Optional IP address of the client making the attempt.
        failure_reason: Optional reason for failure (e.g., "invalid_credentials",
            "account_locked"). Only applicable when success is False.

    Returns:
        The created LoginAttempt model instance.

    Example:
        >>> attempt = record_login_attempt(
        ...     db, "johndoe", False,
        ...     ip_address="192.168.1.100",
        ...     failure_reason="invalid_credentials"
        ... )
    """
    attempt = models.LoginAttempt(
        username=username.lower(),
        ip_address=ip_address,
        success=success,
        failure_reason=failure_reason,
    )
    db.add(attempt)
    db.commit()
    return attempt


def clear_failed_attempts(db: Session, username: str) -> int:
    """Clear failed login attempts for a user after successful authentication.

    This function is intended to be called after a successful login to reset
    the failed attempt counter. Currently implements a no-op as the lockout
    window naturally expires.

    Args:
        db: SQLAlchemy database session.
        username: Username to clear failed attempts for.

    Returns:
        Number of attempts cleared. Currently always returns 0.

    Note:
        The current implementation relies on the time-based lockout window
        expiring naturally rather than explicitly deleting failed attempts.
    """
    # We don't actually delete, but this could be used for cleanup
    # For now, successful logins just reset the window naturally
    return 0


def authenticate_user_with_lockout(
    db: Session, username: str, password: str, ip_address: str | None = None
) -> tuple[models.User | None, str | None]:
    """Authenticate a user with comprehensive account lockout protection.

    This is the recommended authentication function for login endpoints.
    It combines credential verification with brute-force protection by:
    - Checking if the account is currently locked
    - Recording all login attempts
    - Providing informative error messages about remaining attempts

    Args:
        db: SQLAlchemy database session.
        username: Username to authenticate. Case-insensitive.
        password: Plain text password to verify.
        ip_address: Optional client IP address for audit logging.

    Returns:
        A tuple containing:
            - models.User | None: The authenticated User if successful, None otherwise.
            - str | None: Error message if authentication failed, None if successful.

    Example:
        >>> user, error = authenticate_user_with_lockout(
        ...     db, "johndoe", "password123", "192.168.1.100"
        ... )
        >>> if error:
        ...     print(f"Login failed: {error}")
        >>> elif user:
        ...     print(f"Welcome, {user.username}!")
    """
    normalized_username = username.lower()

    # Check if account is locked before attempting authentication
    locked, minutes_remaining = is_account_locked(db, normalized_username)
    if locked:
        record_login_attempt(
            db, normalized_username, False, ip_address, "account_locked"
        )
        return None, f"Account is locked. Try again in {minutes_remaining} minutes."

    # Attempt authentication
    user = authenticate_user(db, normalized_username, password)

    if user:
        # Successful login - record and return user
        record_login_attempt(db, normalized_username, True, ip_address)
        return user, None
    else:
        # Failed login - record and check remaining attempts
        record_login_attempt(
            db, normalized_username, False, ip_address, "invalid_credentials"
        )

        # Check if this attempt triggered a lockout
        from app.utils.password import PasswordPolicy

        failed_attempts = get_failed_login_attempts(db, normalized_username)
        remaining_attempts = PasswordPolicy.MAX_LOGIN_ATTEMPTS - failed_attempts

        if remaining_attempts <= 0:
            return None, (
                f"Account is now locked due to too many failed attempts. "
                f"Try again in {PasswordPolicy.LOCKOUT_DURATION_MINUTES} minutes."
            )
        elif remaining_attempts <= 2:
            # Warn user when close to lockout
            return None, (
                f"Invalid username or password. "
                f"{remaining_attempts} attempt(s) remaining before lockout."
            )
        else:
            return None, "Invalid username or password."


def get_user_by_username(db: Session, username: str) -> models.User | None:
    """Retrieve a user by username with case-insensitive matching.

    Args:
        db: SQLAlchemy database session.
        username: The username to search for. Will be normalized to lowercase.

    Returns:
        The User model instance if found, None otherwise.

    Example:
        >>> user = get_user_by_username(db, "JohnDoe")
        >>> if user:
        ...     print(f"Found user: {user.email}")
    """
    # Ensure we're always searching with lowercase
    normalized_username = username.lower()
    return (
        db.query(models.User)
        .filter(models.User.username == normalized_username)
        .first()
    )


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    """FastAPI dependency to get the current authenticated user from a JWT token.

    Extracts and validates the JWT token from the Authorization header,
    then retrieves the corresponding user from the database. This function
    is designed to be used as a FastAPI dependency.

    Args:
        token: JWT access token extracted from the Authorization header
            by the OAuth2PasswordBearer scheme.
        db: SQLAlchemy database session injected by FastAPI.

    Returns:
        The authenticated User model instance.

    Raises:
        HTTPException: 401 Unauthorized if:
            - The token is invalid or expired
            - The token payload is missing the "sub" claim
            - The user specified in the token does not exist

    Example:
        >>> @app.get("/protected")
        ... def protected_route(user: models.User = Depends(get_current_user)):
        ...     return {"message": f"Hello, {user.username}"}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception

    return user


# ============================================================================
# Refresh Token Functions
# ============================================================================


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for secure storage.

    Tokens are stored as hashes in the database rather than plain text
    to prevent exposure in case of database compromise.

    Args:
        token: The raw token string to hash.

    Returns:
        The SHA-256 hexadecimal hash of the token.

    Example:
        >>> hash_token("my_secret_token")
        'a1b2c3...'  # 64-character hex string
    """
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token(db: Session, user_id: int, family_id: str = None) -> str:
    """Create a new refresh token for a user with optional family grouping.

    Generates a cryptographically secure refresh token and stores its hash
    in the database. Tokens are grouped into families to enable secure
    token rotation and reuse detection.

    Args:
        db: SQLAlchemy database session.
        user_id: The ID of the user to create the token for.
        family_id: Optional family identifier for token rotation. If None,
            a new family is created. Tokens in the same family are rotated
            together and can detect reuse attacks.

    Returns:
        The raw refresh token string to be sent to the client.
        This value is not stored and cannot be recovered.

    Example:
        >>> raw_token = create_refresh_token(db, user_id=42)
        >>> # Send raw_token to client, store only hash in database
    """
    # Generate a secure random token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)

    # Use provided family_id or create new one
    if family_id is None:
        family_id = str(uuid4())

    # Create refresh token record
    refresh_token = models.RefreshToken(
        id=str(uuid4()),
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        family_id=family_id,
    )

    db.add(refresh_token)
    db.commit()

    return raw_token


def verify_refresh_token(
    db: Session, raw_token: str
) -> tuple[models.RefreshToken, models.User]:
    """Verify a refresh token and return the associated token record and user.

    Validates that the token exists, has not been revoked, and has not expired.
    If a revoked token is presented (indicating potential token theft/reuse),
    the entire token family is revoked for security.

    Args:
        db: SQLAlchemy database session.
        raw_token: The raw refresh token string received from the client.

    Returns:
        A tuple containing:
            - models.RefreshToken: The verified refresh token record.
            - models.User: The user associated with the token.

    Raises:
        HTTPException: 401 Unauthorized if:
            - The token does not exist in the database
            - The token has been revoked (triggers family-wide revocation)
            - The token has expired
            - The associated user does not exist

    Example:
        >>> try:
        ...     token_record, user = verify_refresh_token(db, raw_token)
        ...     print(f"Token valid for user: {user.username}")
        ... except HTTPException:
        ...     print("Invalid or expired token")
    """
    token_hash = hash_token(raw_token)

    # Find the token by its hash
    refresh_token = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_hash == token_hash)
        .first()
    )

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Check if revoked - this may indicate token theft/reuse
    if refresh_token.revoked:
        # Token reuse detected - revoke entire family for security
        revoke_token_family(db, refresh_token.family_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    # Check expiration (handle both naive and aware datetimes)
    now = datetime.now(UTC)
    expires_at = refresh_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    # Get the user
    user = db.query(models.User).filter(models.User.id == refresh_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return refresh_token, user


def rotate_refresh_token(db: Session, old_token: models.RefreshToken) -> str:
    """Rotate a refresh token by revoking the old one and creating a new one.

    Implements secure token rotation by invalidating the used token and
    issuing a new one in the same family. This limits the window of
    vulnerability if a token is compromised.

    Args:
        db: SQLAlchemy database session.
        old_token: The RefreshToken model instance to rotate.

    Returns:
        The new raw refresh token string to send to the client.

    Example:
        >>> token_record, user = verify_refresh_token(db, old_raw_token)
        >>> new_raw_token = rotate_refresh_token(db, token_record)
        >>> # Send new_raw_token to client
    """
    # Revoke the old token
    old_token.revoked = True
    db.commit()

    # Create new token in the same family
    return create_refresh_token(db, old_token.user_id, old_token.family_id)


def revoke_token_family(db: Session, family_id: str) -> int:
    """Revoke all tokens in a family for security purposes.

    Used when token reuse is detected, indicating potential token theft.
    Revoking the entire family ensures that even if an attacker has a
    valid token from the family, it becomes unusable.

    Args:
        db: SQLAlchemy database session.
        family_id: The UUID of the token family to revoke.

    Returns:
        The number of tokens that were revoked.

    Example:
        >>> revoked_count = revoke_token_family(db, "abc123-family-id")
        >>> print(f"Revoked {revoked_count} tokens")
    """
    result = (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.family_id == family_id,
            models.RefreshToken.revoked == False,  # noqa: E712
        )
        .update({"revoked": True})
    )
    db.commit()
    return result


def revoke_user_tokens(db: Session, user_id: int) -> int:
    """Revoke all refresh tokens for a specific user.

    Should be called when a user logs out, changes their password, or
    when their account security may be compromised. This invalidates
    all active sessions for the user.

    Args:
        db: SQLAlchemy database session.
        user_id: The ID of the user whose tokens should be revoked.

    Returns:
        The number of tokens that were revoked.

    Example:
        >>> # On password change, invalidate all sessions
        >>> revoked = revoke_user_tokens(db, user.id)
        >>> print(f"Logged out from {revoked} devices")
    """
    result = (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.user_id == user_id,
            models.RefreshToken.revoked == False,  # noqa: E712
        )
        .update({"revoked": True})
    )
    db.commit()
    return result


def cleanup_expired_tokens(db: Session) -> int:
    """Remove expired refresh tokens from the database.

    Performs database maintenance by deleting tokens that have passed
    their expiration date. Should be called periodically (e.g., via
    a scheduled task) to prevent table bloat.

    Args:
        db: SQLAlchemy database session.

    Returns:
        The number of expired tokens that were deleted.

    Example:
        >>> # Run as a scheduled cleanup task
        >>> deleted = cleanup_expired_tokens(db)
        >>> print(f"Cleaned up {deleted} expired tokens")
    """
    result = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.expires_at < datetime.now(UTC))
        .delete()
    )
    db.commit()
    return result
