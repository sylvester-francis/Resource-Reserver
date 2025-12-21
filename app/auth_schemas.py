"""Pydantic schemas for authentication, authorization, and OAuth2."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# MFA Schemas
# ============================================================================


class MFASetupResponse(BaseModel):
    """Response for MFA setup."""

    secret: str
    qr_code: str  # Base64 QR code image
    backup_codes: list[str]
    totp_uri: str


class MFAVerifyRequest(BaseModel):
    """Request to verify MFA code."""

    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("MFA code must be 6 digits")
        return v


class MFADisableRequest(BaseModel):
    """Request to disable MFA."""

    password: str


class MFABackupCodeRequest(BaseModel):
    """Request to use backup code."""

    code: str


# ============================================================================
# Role Schemas
# ============================================================================


class RoleCreate(BaseModel):
    """Create a new role."""

    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = None


class RoleResponse(BaseModel):
    """Role response."""

    id: int
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleAssignRequest(BaseModel):
    """Assign a role to a user."""

    user_id: int
    role_name: str


# ============================================================================
# OAuth2 Schemas
# ============================================================================


class OAuth2ClientCreate(BaseModel):
    """Create a new OAuth2 client."""

    client_name: str = Field(..., min_length=1, max_length=255)
    redirect_uris: list[str] = Field(..., min_length=1)
    grant_types: str = "authorization_code client_credentials"
    scope: str = "read write"

    @field_validator("redirect_uris")
    @classmethod
    def validate_redirect_uris(cls, v: list[str]) -> list[str]:
        for uri in v:
            if not uri.startswith(("http://", "https://")):
                raise ValueError("Redirect URIs must use http:// or https://")
        return v


class OAuth2ClientResponse(BaseModel):
    """OAuth2 client response (without secret)."""

    id: int
    client_id: str
    client_name: str
    redirect_uris: list[str]
    grant_types: str
    scope: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OAuth2ClientCreatedResponse(BaseModel):
    """Response when OAuth2 client is created (includes secret)."""

    client_id: str
    client_secret: str  # Only shown once!
    client_name: str
    redirect_uris: list[str]
    grant_types: str
    scope: str
    message: str


class OAuth2AuthorizeRequest(BaseModel):
    """OAuth2 authorization request."""

    client_id: str
    redirect_uri: str
    response_type: str = "code"
    scope: str = "read"
    state: str | None = None
    code_challenge: str | None = None  # PKCE
    code_challenge_method: str | None = None  # PKCE


class OAuth2TokenRequest(BaseModel):
    """OAuth2 token request."""

    grant_type: str
    code: str | None = None  # For authorization_code grant
    redirect_uri: str | None = None
    refresh_token: str | None = None  # For refresh_token grant
    scope: str | None = None
    code_verifier: str | None = None  # PKCE


class OAuth2TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None
    scope: str


class OAuth2TokenIntrospectionResponse(BaseModel):
    """OAuth2 token introspection response."""

    active: bool
    client_id: str | None = None
    username: int | None = None
    scope: str | None = None
    exp: int | None = None
    iat: int | None = None


# ============================================================================
# Permission Schemas
# ============================================================================


class ResourcePermissionCreate(BaseModel):
    """Create a resource permission."""

    resource_id: int
    user_id: int | None = None
    role_id: int | None = None
    action: str

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid_actions = ["read", "update", "delete", "reserve"]
        if v not in valid_actions:
            raise ValueError(f"Action must be one of: {', '.join(valid_actions)}")
        return v


class ResourcePermissionResponse(BaseModel):
    """Resource permission response."""

    id: int
    resource_id: int
    user_id: int | None = None
    role_id: int | None = None
    action: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Enhanced User Schemas
# ============================================================================


class UserResponseWithMFA(BaseModel):
    """Enhanced user response including MFA status."""

    id: int
    username: str
    email: str | None = None
    email_verified: bool = False
    mfa_enabled: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserUpdateEmail(BaseModel):
    """Update user email."""

    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email address")
        return v.lower()


# ============================================================================
# Auth Response Schemas
# ============================================================================


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_session_token: str | None = None  # Temporary token if MFA required


class MFALoginRequest(BaseModel):
    """Complete login with MFA."""

    mfa_session_token: str
    mfa_code: str
