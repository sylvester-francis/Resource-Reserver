"""Authentication and authorization utilities."""

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
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:  # noqa : E501
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # noqa : E501

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, username: str, password: str) -> models.User | None:
    """Authenticate a user with username and password."""
    # Normalize the username to lowercase for case-insensitive comparison
    normalized_username = username.lower()
    user = get_user_by_username(db, normalized_username)

    if not user or not verify_password(password, user.hashed_password):
        return None

    return user


def get_user_by_username(db: Session, username: str) -> models.User | None:
    """Get user by username (case-insensitive)."""
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
    """Get the current authenticated user from JWT token."""
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
    """Hash a token using SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token(db: Session, user_id: int, family_id: str = None) -> str:
    """Create a new refresh token for a user.

    Args:
        db: Database session
        user_id: User ID to create token for
        family_id: Optional family ID for token rotation (new family if None)

    Returns:
        The raw refresh token (to be sent to client)
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
    """Verify a refresh token and return the token record and user.

    Args:
        db: Database session
        raw_token: The raw refresh token from the client

    Returns:
        Tuple of (RefreshToken, User) if valid

    Raises:
        HTTPException: If token is invalid, expired, or revoked
    """
    token_hash = hash_token(raw_token)

    # Find the token
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

    # Check if revoked
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
    """Rotate a refresh token (revoke old, create new in same family).

    Args:
        db: Database session
        old_token: The old refresh token record to rotate

    Returns:
        The new raw refresh token
    """
    # Revoke the old token
    old_token.revoked = True
    db.commit()

    # Create new token in the same family
    return create_refresh_token(db, old_token.user_id, old_token.family_id)


def revoke_token_family(db: Session, family_id: str) -> int:
    """Revoke all tokens in a family (for security on token reuse detection).

    Args:
        db: Database session
        family_id: The family ID to revoke

    Returns:
        Number of tokens revoked
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
    """Revoke all refresh tokens for a user (e.g., on logout or password change).

    Args:
        db: Database session
        user_id: The user ID to revoke tokens for

    Returns:
        Number of tokens revoked
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
    """Clean up expired refresh tokens from the database.

    Args:
        db: Database session

    Returns:
        Number of tokens deleted
    """
    result = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.expires_at < datetime.now(UTC))
        .delete()
    )
    db.commit()
    return result
