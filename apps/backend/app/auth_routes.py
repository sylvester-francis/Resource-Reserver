"""API routes for authentication, MFA, RBAC, and OAuth2."""

from fastapi import APIRouter, Depends, Form, Header, HTTPException
from sqlalchemy.orm import Session

from app import auth, auth_schemas, mfa, models, oauth2, rbac
from app.database import get_db

# Create routers
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
mfa_router = APIRouter(prefix="/auth/mfa", tags=["MFA"])
roles_router = APIRouter(prefix="/roles", tags=["Roles"])
oauth_router = APIRouter(prefix="/oauth", tags=["OAuth2"])


# ============================================================================
# MFA Endpoints
# ============================================================================


@mfa_router.post("/setup", response_model=auth_schemas.MFASetupResponse)
def setup_mfa_for_user(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Set up MFA for the current user."""
    if current_user.mfa_enabled:
        raise HTTPException(400, "MFA is already enabled")

    result = mfa.setup_mfa(current_user, db)
    return result


@mfa_router.post("/verify")
def verify_and_enable_mfa(
    request: auth_schemas.MFAVerifyRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Verify MFA code and enable MFA."""
    if current_user.mfa_enabled:
        raise HTTPException(400, "MFA is already enabled")

    if not mfa.enable_mfa(current_user, request.code, db):
        raise HTTPException(400, "Invalid MFA code")

    return {"message": "MFA enabled successfully"}


@mfa_router.post("/disable")
def disable_mfa_for_user(
    request: auth_schemas.MFADisableRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Disable MFA for the current user."""
    if not current_user.mfa_enabled:
        raise HTTPException(400, "MFA is not enabled")

    if not mfa.disable_mfa(current_user, request.password, db):
        raise HTTPException(400, "Invalid password")

    return {"message": "MFA disabled successfully"}


@mfa_router.post("/backup-codes")
def regenerate_mfa_backup_codes(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate backup codes."""
    if not current_user.mfa_enabled:
        raise HTTPException(400, "MFA is not enabled")

    codes = mfa.regenerate_backup_codes(current_user, db)
    return {
        "backup_codes": codes,
        "message": "Save these codes in a safe place - they won't be shown again",
    }


# ============================================================================
# Role Management Endpoints
# ============================================================================


@roles_router.get("/", response_model=list[auth_schemas.RoleResponse])
def list_roles(
    current_user: models.User = Depends(rbac.require_permission("user", "read")),
    db: Session = Depends(get_db),
):
    """List all available roles."""
    roles = db.query(models.Role).all()
    return roles


@roles_router.post("/", response_model=auth_schemas.RoleResponse)
def create_role(
    role_data: auth_schemas.RoleCreate,
    current_user: models.User = Depends(rbac.require_role("admin")),
    db: Session = Depends(get_db),
):
    """Create a new role (admin only)."""
    # Check if role already exists
    existing = db.query(models.Role).filter(models.Role.name == role_data.name).first()

    if existing:
        raise HTTPException(400, "Role already exists")

    role = models.Role(name=role_data.name, description=role_data.description)
    db.add(role)
    db.commit()
    db.refresh(role)

    return role


@roles_router.post("/assign")
def assign_role_to_user(
    request: auth_schemas.RoleAssignRequest,
    current_user: models.User = Depends(rbac.require_role("admin")),
    db: Session = Depends(get_db),
):
    """Assign a role to a user (admin only)."""
    # Resolve user_id from username if needed
    user_id = request.user_id
    if not user_id and request.username:
        user = db.query(models.User).filter(models.User.username == request.username).first()
        if not user:
            raise HTTPException(404, f"User '{request.username}' not found")
        user_id = user.id
    if not user_id:
        raise HTTPException(400, "Either user_id or username is required")
    
    if rbac.assign_role(user_id, request.role_name, db):
        return {"message": f"Role '{request.role_name}' assigned successfully"}
    else:
        raise HTTPException(404, "Role not found")


@roles_router.delete("/assign")
def remove_role_from_user(
    request: auth_schemas.RoleAssignRequest,
    current_user: models.User = Depends(rbac.require_role("admin")),
    db: Session = Depends(get_db),
):
    """Remove a role from a user (admin only)."""
    # Resolve user_id from username if needed
    user_id = request.user_id
    if not user_id and request.username:
        user = db.query(models.User).filter(models.User.username == request.username).first()
        if not user:
            raise HTTPException(404, f"User '{request.username}' not found")
        user_id = user.id
    if not user_id:
        raise HTTPException(400, "Either user_id or username is required")
    
    if rbac.remove_role(user_id, request.role_name, db):
        return {"message": f"Role '{request.role_name}' removed successfully"}
    else:
        raise HTTPException(404, "Role not found")


@roles_router.get("/my-roles", response_model=list[auth_schemas.RoleResponse])
def get_my_roles(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's roles."""
    roles = rbac.get_user_roles(current_user.id, db)
    return roles


# ============================================================================
# Admin User Management Endpoints
# ============================================================================


@auth_router.post("/admin/reset-password")
def admin_reset_user_password(
    request: auth_schemas.AdminPasswordResetRequest,
    current_user: models.User = Depends(rbac.require_role("admin")),
    db: Session = Depends(get_db),
):
    """Reset a user's password (admin only).
    
    Allows administrators to set a new password for any user account.
    The user will need to use this new password on their next login.
    """
    # Find the user by username
    user = db.query(models.User).filter(models.User.username == request.username).first()
    if not user:
        raise HTTPException(404, f"User '{request.username}' not found")
    
    # Prevent admin from accidentally resetting their own password through this endpoint
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot reset your own password through admin endpoint. Use profile settings instead.")
    
    # Hash and set the new password
    user.hashed_password = auth.hash_password(request.new_password)
    
    # Clear any failed login attempts
    user.failed_attempts = 0
    user.lockout_until = None
    
    db.commit()
    
    return {"message": f"Password for user '{request.username}' has been reset successfully"}


@auth_router.get("/admin/users")
def admin_list_users(
    current_user: models.User = Depends(rbac.require_role("admin")),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    """List all users (admin only)."""
    users = db.query(models.User).offset(skip).limit(limit).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_active": u.is_active,
            "mfa_enabled": u.mfa_enabled,
            "created_at": u.created_at,
        }
        for u in users
    ]


# ============================================================================
# OAuth2 Client Management Endpoints
# ============================================================================


@oauth_router.post("/clients", response_model=auth_schemas.OAuth2ClientCreatedResponse)
def create_oauth_client(
    client_data: auth_schemas.OAuth2ClientCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new OAuth2 client."""
    result = oauth2.create_oauth_client(
        client_name=client_data.client_name,
        redirect_uris=client_data.redirect_uris,
        owner_id=current_user.id,
        db=db,
        grant_types=client_data.grant_types,
        scope=client_data.scope,
    )
    return result


@oauth_router.get("/clients", response_model=list[auth_schemas.OAuth2ClientResponse])
def list_my_oauth_clients(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """List current user's OAuth2 clients."""
    clients = (
        db.query(models.OAuth2Client)
        .filter(models.OAuth2Client.owner_id == current_user.id)
        .all()
    )
    return clients


@oauth_router.delete("/clients/{client_id}")
def delete_oauth_client(
    client_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an OAuth2 client."""
    if oauth2.delete_oauth_client(client_id, current_user.id, db):
        return {"message": "OAuth2 client deleted successfully"}
    else:
        raise HTTPException(404, "OAuth2 client not found or unauthorized")


# ============================================================================
# OAuth2 Authorization Flow Endpoints
# ============================================================================


@oauth_router.get("/authorize")
def oauth_authorize(
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    scope: str = "read",
    state: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    OAuth2 authorization endpoint.

    User must be authenticated. Returns authorization code.
    """
    # Validate client
    client = oauth2.get_client_by_id(client_id, db)
    if not client:
        raise HTTPException(404, "Invalid client_id")

    # Validate redirect_uri
    if redirect_uri not in client.redirect_uris:
        raise HTTPException(400, "Invalid redirect_uri")

    # Validate response_type
    if response_type != "code":
        raise HTTPException(400, "Only 'code' response_type is supported")

    # Validate scope
    if not oauth2.validate_scopes(scope):
        raise HTTPException(400, "Invalid scope")

    # Create authorization code
    code = oauth2.create_authorization_code(
        client_id=client_id,
        user_id=current_user.id,
        redirect_uri=redirect_uri,
        scope=scope,
        db=db,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    # Redirect back to client with code
    redirect_url = f"{redirect_uri}?code={code}"
    if state:
        redirect_url += f"&state={state}"

    return {"redirect_uri": redirect_url, "code": code, "state": state}


@oauth_router.post("/token", response_model=auth_schemas.OAuth2TokenResponse)
def oauth_token(
    grant_type: str = Form(...),
    code: str | None = Form(None),
    redirect_uri: str | None = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    refresh_token: str | None = Form(None),
    code_verifier: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """OAuth2 token endpoint."""
    # Verify client
    client = oauth2.get_client_by_id(client_id, db)
    if not client or not oauth2.verify_client_secret(client, client_secret):
        raise HTTPException(401, "Invalid client credentials")

    if grant_type == "authorization_code":
        if not code or not redirect_uri:
            raise HTTPException(400, "code and redirect_uri required")

        # Get authorization code
        auth_code = oauth2.get_authorization_code(code, db)
        if not auth_code:
            raise HTTPException(400, "Invalid or expired authorization code")

        # Verify client and redirect_uri
        if auth_code.client_id != client_id:
            raise HTTPException(400, "Client mismatch")

        if auth_code.redirect_uri != redirect_uri:
            raise HTTPException(400, "Redirect URI mismatch")

        # Mark code as used
        oauth2.use_authorization_code(code, db)

        # Create access token
        token_response = oauth2.create_access_token(
            client_id=client_id, user_id=auth_code.user_id, scope=auth_code.scope, db=db
        )

        return token_response

    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(400, "refresh_token required")

        # Refresh the token
        token_response = oauth2.refresh_access_token(refresh_token, db)
        if not token_response:
            raise HTTPException(400, "Invalid refresh token")

        return token_response

    elif grant_type == "client_credentials":
        # Client credentials grant (no user)
        token_response = oauth2.create_access_token(
            client_id=client_id,
            user_id=None,
            scope="read",
            db=db,
            include_refresh=False,
        )

        return token_response

    else:
        raise HTTPException(400, f"Unsupported grant_type: {grant_type}")


@oauth_router.post("/revoke")
def oauth_revoke_token(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: Session = Depends(get_db),
):
    """Revoke an access token."""
    # Verify client
    client = oauth2.get_client_by_id(client_id, db)
    if not client or not oauth2.verify_client_secret(client, client_secret):
        raise HTTPException(401, "Invalid client credentials")

    oauth2.revoke_token(token, db)
    return {"message": "Token revoked"}


@oauth_router.post(
    "/introspect", response_model=auth_schemas.OAuth2TokenIntrospectionResponse
)
def oauth_introspect_token(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: Session = Depends(get_db),
):
    """Introspect an access token."""
    # Verify client
    client = oauth2.get_client_by_id(client_id, db)
    if not client or not oauth2.verify_client_secret(client, client_secret):
        raise HTTPException(401, "Invalid client credentials")

    result = oauth2.introspect_token(token, db)
    return result


# ============================================================================
# Protected API Example (Using OAuth2 Token)
# ============================================================================


@oauth_router.get("/protected")
def oauth_protected_endpoint(
    authorization: str = Header(None), db: Session = Depends(get_db)
):
    """Example protected endpoint requiring OAuth2 token."""
    token = oauth2.verify_request_token(authorization, "read", db)

    return {
        "message": "Access granted via OAuth2",
        "client_id": token.client_id,
        "scope": token.scope,
    }
