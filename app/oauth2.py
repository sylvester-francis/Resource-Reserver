"""OAuth2 Authorization Server using Authlib."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional

from authlib.integrations.sqla_oauth2 import (
    OAuth2AuthorizationCodeMixin,
    OAuth2ClientMixin,
    OAuth2TokenMixin,
)
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6749.grants import (
    AuthorizationCodeGrant as _AuthorizationCodeGrant,
)
from authlib.oauth2.rfc7636 import CodeChallenge
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.auth import hash_password, verify_password


# ============================================================================
# OAuth2 Client Management
# ============================================================================

def create_oauth_client(
    client_name: str,
    redirect_uris: list[str],
    owner_id: int,
    db: Session,
    grant_types: str = "authorization_code client_credentials",
    scope: str = "read write"
) -> dict:
    """
    Create a new OAuth2 client.
    
    Returns:
        Dictionary with client_id, client_secret (only shown once!)
    """
    client_id = secrets.token_urlsafe(24)
    client_secret = secrets.token_urlsafe(48)
    
    client = models.OAuth2Client(
        client_id=client_id,
        client_secret=hash_password(client_secret),  # Hash it!
        client_name=client_name,
        redirect_uris=redirect_uris,
        grant_types=grant_types,
        scope=scope,
        owner_id=owner_id
    )
    
    db.add(client)
    db.commit()
    db.refresh(client)
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,  # Only shown once!
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
        "scope": scope,
        "message": "Save the client_secret now - it won't be shown again!"
    }


def get_client_by_id(client_id: str, db: Session) -> Optional[models.OAuth2Client]:
    """Get OAuth2 client by client_id."""
    return db.query(models.OAuth2Client).filter(
        models.OAuth2Client.client_id == client_id
    ).first()


def verify_client_secret(client: models.OAuth2Client, secret: str) -> bool:
    """Verify OAuth2 client secret."""
    return verify_password(secret, client.client_secret)


def delete_oauth_client(client_id: str, user_id: int, db: Session) -> bool:
    """Delete an OAuth2 client (only by owner)."""
    client = db.query(models.OAuth2Client).filter(
        models.OAuth2Client.client_id == client_id,
        models.OAuth2Client.owner_id == user_id
    ).first()
    
    if not client:
        return False
    
    db.delete(client)
    db.commit()
    return True


# ============================================================================
# Authorization Code Management
# ============================================================================

def create_authorization_code(
    client_id: str,
    user_id: int,
    redirect_uri: str,
    scope: str,
    db: Session,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None,
    expires_in: int = 600  # 10 minutes
) -> str:
    """Create an authorization code."""
    code = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    
    auth_code = models.OAuth2AuthorizationCode(
        code=code,
        client_id=client_id,
        user_id=user_id,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=expires_at
    )
    
    db.add(auth_code)
    db.commit()
    
    return code


def get_authorization_code(code: str, db: Session) -> Optional[models.OAuth2AuthorizationCode]:
    """Get authorization code."""
    return db.query(models.OAuth2AuthorizationCode).filter(
        models.OAuth2AuthorizationCode.code == code,
        models.OAuth2AuthorizationCode.used == False,  # noqa: E712
        models.OAuth2AuthorizationCode.expires_at > datetime.now(UTC)
    ).first()


def use_authorization_code(code: str, db: Session) -> bool:
    """Mark authorization code as used."""
    auth_code = db.query(models.OAuth2AuthorizationCode).filter(
        models.OAuth2AuthorizationCode.code == code
    ).first()
    
    if not auth_code:
        return False
    
    auth_code.used = True
    db.commit()
    return True


# ============================================================================
# Token Management
# ============================================================================

def create_access_token(
    client_id: str,
    user_id: Optional[int],
    scope: str,
    db: Session,
    expires_in: int = 3600,  # 1 hour
    include_refresh: bool = True
) -> dict:
    """Create an access token (and optionally refresh token)."""
    access_token = secrets.token_urlsafe(48)
    refresh_token = secrets.token_urlsafe(48) if include_refresh else None
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    
    token = models.OAuth2Token(
        client_id=client_id,
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        scope=scope,
        expires_at=expires_at
    )
    
    db.add(token)
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "scope": scope
    }


def get_token_by_access_token(access_token: str, db: Session) -> Optional[models.OAuth2Token]:
    """Get token by access token."""
    return db.query(models.OAuth2Token).filter(
        models.OAuth2Token.access_token == access_token,
        models.OAuth2Token.revoked == False,  # noqa: E712
        models.OAuth2Token.expires_at > datetime.now(UTC)
    ).first()


def get_token_by_refresh_token(refresh_token: str, db: Session) -> Optional[models.OAuth2Token]:
    """Get token by refresh token."""
    return db.query(models.OAuth2Token).filter(
        models.OAuth2Token.refresh_token == refresh_token,
        models.OAuth2Token.revoked == False  # noqa: E712
    ).first()


def revoke_token(access_token: str, db: Session) -> bool:
    """Revoke an access token."""
    token = db.query(models.OAuth2Token).filter(
        models.OAuth2Token.access_token == access_token
    ).first()
    
    if not token:
        return False
    
    token.revoked = True
    db.commit()
    return True


def refresh_access_token(refresh_token: str, db: Session) -> Optional[dict]:
    """Refresh an access token using refresh token."""
    old_token = get_token_by_refresh_token(refresh_token, db)
    
    if not old_token:
        return None
    
    # Revoke old token
    old_token.revoked = True
    db.commit()
    
    # Create new token
    return create_access_token(
        client_id=old_token.client_id,
        user_id=old_token.user_id,
        scope=old_token.scope,
        db=db
    )


def introspect_token(access_token: str, db: Session) -> Optional[dict]:
    """
    Introspect an access token.
    
    Returns token information or None if invalid.
    """
    token = get_token_by_access_token(access_token, db)
    
    if not token:
        return {"active": False}
    
    return {
        "active": True,
        "client_id": token.client_id,
        "username": token.user_id,  # Could map to username
        "scope": token.scope,
        "exp": int(token.expires_at.timestamp()),
        "iat": int(token.created_at.timestamp()),
    }


# ============================================================================
# Token Verification for Protected Endpoints
# ============================================================================

def verify_request_token(authorization: str, required_scope: Optional[str], db: Session) -> models.OAuth2Token:
    """
    Verify OAuth2 bearer token from request.
    
    Args:
        authorization: Authorization header value
        required_scope: Required scope (optional)
        db: Database session
    
    Returns:
        OAuth2Token if valid
    
    Raises:
        HTTPException if invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    
    access_token = authorization.replace("Bearer ", "")
    
    token = get_token_by_access_token(access_token, db)
    if not token:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check scope if required
    if required_scope:
        token_scopes = token.scope.split()
        if required_scope not in token_scopes:
            raise HTTPException(403, f"Scope '{required_scope}' required")
    
    return token


# ============================================================================
# Scope Utilities
# ============================================================================

VALID_SCOPES = {
    "read": "Read access to resources and reservations",
    "write": "Create and update resources and reservations",
    "delete": "Delete resources and reservations",
    "admin": "Administrative access",
    "user:profile": "Access user profile information"
}


def validate_scopes(scopes: str) -> bool:
    """Validate that all scopes are valid."""
    scope_list = scopes.split()
    return all(scope in VALID_SCOPES for scope in scope_list)


def get_scope_description(scope: str) -> str:
    """Get human-readable description of a scope."""
    return VALID_SCOPES.get(scope, "Unknown scope")
