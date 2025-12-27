"""Unit tests for MFA, RBAC, and OAuth2 functionality."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import mfa, models, oauth2, rbac
from app.auth import hash_password
from app.models import Base

# Test database setup
TEST_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "db" / "test_auth.db"
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SQLALCHEMY_TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = models.User(
        username="testuser",
        hashed_password=hash_password("testpass123"),
        email="test@example.com",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ============================================================================
# MFA Tests
# ============================================================================


def test_generate_mfa_secret():
    """Test MFA secret generation."""
    secret = mfa.generate_mfa_secret()
    assert secret is not None
    assert len(secret) == 32  # Base32 encoded


def test_generate_backup_codes():
    """Test backup code generation."""
    codes = mfa.generate_backup_codes(count=10)
    assert len(codes) == 10
    assert all(len(code) == 8 for code in codes)


def test_setup_mfa(test_user, db):
    """Test MFA setup for user."""
    result = mfa.setup_mfa(test_user, db)

    assert "secret" in result
    assert "qr_code" in result
    assert "backup_codes" in result
    assert "totp_uri" in result

    # Verify user has secret stored
    db.refresh(test_user)
    assert test_user.mfa_secret is not None
    assert test_user.mfa_enabled is False  # Not enabled until verified


def test_verify_mfa(test_user, db):
    """Test MFA code verification."""
    import pyotp

    # Setup MFA
    result = mfa.setup_mfa(test_user, db)
    secret = result["secret"]

    # Generate valid TOTP code
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    # Verify code
    assert mfa.verify_mfa(test_user, valid_code) is True

    # Verify invalid code
    assert mfa.verify_mfa(test_user, "000000") is False


def test_enable_mfa(test_user, db):
    """Test enabling MFA."""
    import pyotp

    # Setup MFA
    result = mfa.setup_mfa(test_user, db)
    secret = result["secret"]

    # Generate valid code
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    # Enable MFA
    assert mfa.enable_mfa(test_user, valid_code, db) is True

    db.refresh(test_user)
    assert test_user.mfa_enabled is True


def test_disable_mfa(test_user, db):
    """Test disabling MFA."""
    import pyotp

    # Setup and enable MFA first
    result = mfa.setup_mfa(test_user, db)
    totp = pyotp.TOTP(result["secret"])
    mfa.enable_mfa(test_user, totp.now(), db)

    # Disable MFA with correct password
    assert mfa.disable_mfa(test_user, "testpass123", db) is True

    db.refresh(test_user)
    assert test_user.mfa_enabled is False
    assert test_user.mfa_secret is None


def test_backup_codes(test_user, db):
    """Test backup code usage."""
    import pyotp

    # Setup and enable MFA
    result = mfa.setup_mfa(test_user, db)
    totp = pyotp.TOTP(result["secret"])
    mfa.enable_mfa(test_user, totp.now(), db)

    backup_codes = result["backup_codes"]
    first_code = backup_codes[0]

    # Use backup code
    assert mfa.use_backup_code(test_user, first_code, db) is True

    # Try to use same code again (should fail)
    assert mfa.use_backup_code(test_user, first_code, db) is False


# ============================================================================
# RBAC Tests
# ============================================================================


def test_create_default_roles(db):
    """Test default role creation."""
    rbac.create_default_roles(db)

    # Check roles exist
    admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
    user_role = db.query(models.Role).filter(models.Role.name == "user").first()
    guest_role = db.query(models.Role).filter(models.Role.name == "guest").first()

    assert admin_role is not None
    assert user_role is not None
    assert guest_role is not None


def test_assign_role(test_user, db):
    """Test role assignment."""
    rbac.create_default_roles(db)

    # Assign user role
    assert rbac.assign_role(test_user.id, "user", db) is True

    # Verify role assigned
    roles = rbac.get_user_roles(test_user.id, db)
    assert len(roles) == 1
    assert roles[0].name == "user"


def test_has_role(test_user, db):
    """Test role checking."""
    rbac.create_default_roles(db)
    rbac.assign_role(test_user.id, "user", db)

    assert rbac.has_role(test_user, "user", db) is True
    assert rbac.has_role(test_user, "admin", db) is False


def test_check_permission(test_user, db):
    """Test permission checking."""
    rbac.create_default_roles(db)
    rbac.assign_role(test_user.id, "user", db)

    # User can read resources
    assert rbac.check_permission(test_user, "resource", "read", db) is True

    # User cannot delete resources (admin only)
    assert rbac.check_permission(test_user, "resource", "delete", db) is False


def test_admin_permissions(test_user, db):
    """Test admin role permissions."""
    rbac.create_default_roles(db)
    rbac.assign_role(test_user.id, "admin", db)

    # Admin can do everything
    assert rbac.check_permission(test_user, "resource", "create", db) is True
    assert rbac.check_permission(test_user, "resource", "read", db) is True
    assert rbac.check_permission(test_user, "resource", "update", db) is True
    assert rbac.check_permission(test_user, "resource", "delete", db) is True


def test_remove_role(test_user, db):
    """Test role removal."""
    rbac.create_default_roles(db)
    rbac.assign_role(test_user.id, "user", db)

    # Remove role
    assert rbac.remove_role(test_user.id, "user", db) is True

    # Verify role removed
    roles = rbac.get_user_roles(test_user.id, db)
    assert len(roles) == 0


# ============================================================================
# OAuth2 Tests
# ============================================================================


def test_create_oauth_client(test_user, db):
    """Test OAuth2 client creation."""
    result = oauth2.create_oauth_client(
        client_name="Test App",
        redirect_uris=["http://localhost:3000/callback"],
        owner_id=test_user.id,
        db=db,
    )

    assert "client_id" in result
    assert "client_secret" in result
    assert result["client_name"] == "Test App"


def test_verify_client_secret(test_user, db):
    """Test client secret verification."""
    result = oauth2.create_oauth_client(
        client_name="Test App",
        redirect_uris=["http://localhost:3000/callback"],
        owner_id=test_user.id,
        db=db,
    )

    client_id = result["client_id"]
    client_secret = result["client_secret"]

    # Get client
    client = oauth2.get_client_by_id(client_id, db)

    # Verify correct secret
    assert oauth2.verify_client_secret(client, client_secret) is True

    # Verify wrong secret
    assert oauth2.verify_client_secret(client, "wrong_secret") is False


def test_create_authorization_code(test_user, db):
    """Test authorization code creation."""
    # Create client first
    client_result = oauth2.create_oauth_client(
        client_name="Test App",
        redirect_uris=["http://localhost:3000/callback"],
        owner_id=test_user.id,
        db=db,
    )

    # Create authorization code
    code = oauth2.create_authorization_code(
        client_id=client_result["client_id"],
        user_id=test_user.id,
        redirect_uri="http://localhost:3000/callback",
        scope="read write",
        db=db,
    )

    assert code is not None
    assert len(code) > 20  # Should be a long random string


def test_use_authorization_code(test_user, db):
    """Test authorization code usage."""
    # Create client and code
    client_result = oauth2.create_oauth_client(
        client_name="Test App",
        redirect_uris=["http://localhost:3000/callback"],
        owner_id=test_user.id,
        db=db,
    )

    code = oauth2.create_authorization_code(
        client_id=client_result["client_id"],
        user_id=test_user.id,
        redirect_uri="http://localhost:3000/callback",
        scope="read",
        db=db,
    )

    # Get code
    auth_code = oauth2.get_authorization_code(code, db)
    assert auth_code is not None
    assert auth_code.used is False

    # Use code
    assert oauth2.use_authorization_code(code, db) is True

    # Code should now be marked as used
    db.refresh(auth_code)
    assert auth_code.used is True

    # Try to get used code (should fail)
    assert oauth2.get_authorization_code(code, db) is None


def test_create_access_token(test_user, db):
    """Test access token creation."""
    # Create client
    client_result = oauth2.create_oauth_client(
        client_name="Test App",
        redirect_uris=["http://localhost:3000/callback"],
        owner_id=test_user.id,
        db=db,
    )

    # Create token
    token_result = oauth2.create_access_token(
        client_id=client_result["client_id"],
        user_id=test_user.id,
        scope="read write",
        db=db,
    )

    assert "access_token" in token_result
    assert "refresh_token" in token_result
    assert token_result["token_type"] == "Bearer"
    assert token_result["expires_in"] == 3600


def test_token_introspection(test_user, db):
    """Test token introspection."""
    # Create client and token
    client_result = oauth2.create_oauth_client(
        client_name="Test App",
        redirect_uris=["http://localhost:3000/callback"],
        owner_id=test_user.id,
        db=db,
    )

    token_result = oauth2.create_access_token(
        client_id=client_result["client_id"], user_id=test_user.id, scope="read", db=db
    )

    # Introspect token
    introspection = oauth2.introspect_token(token_result["access_token"], db)

    assert introspection["active"] is True
    assert introspection["client_id"] == client_result["client_id"]
    assert introspection["scope"] == "read"


def test_revoke_token(test_user, db):
    """Test token revocation."""
    # Create client and token
    client_result = oauth2.create_oauth_client(
        client_name="Test App",
        redirect_uris=["http://localhost:3000/callback"],
        owner_id=test_user.id,
        db=db,
    )

    token_result = oauth2.create_access_token(
        client_id=client_result["client_id"], user_id=test_user.id, scope="read", db=db
    )

    access_token = token_result["access_token"]

    # Revoke token
    assert oauth2.revoke_token(access_token, db) is True

    # Try to get revoked token
    token = oauth2.get_token_by_access_token(access_token, db)
    assert token is None  # Should not be returned (revoked)


def test_refresh_token(test_user, db):
    """Test token refresh."""
    # Create client and token
    client_result = oauth2.create_oauth_client(
        client_name="Test App",
        redirect_uris=["http://localhost:3000/callback"],
        owner_id=test_user.id,
        db=db,
    )

    token_result = oauth2.create_access_token(
        client_id=client_result["client_id"], user_id=test_user.id, scope="read", db=db
    )

    refresh_token = token_result["refresh_token"]
    old_access_token = token_result["access_token"]

    # Refresh the token
    new_token_result = oauth2.refresh_access_token(refresh_token, db)

    assert new_token_result is not None
    assert new_token_result["access_token"] != old_access_token
    assert "refresh_token" in new_token_result


def test_validate_scopes():
    """Test scope validation."""
    assert oauth2.validate_scopes("read") is True
    assert oauth2.validate_scopes("read write") is True
    assert oauth2.validate_scopes("invalid_scope") is False
    assert oauth2.validate_scopes("read invalid") is False


# ============================================================================
# Resource Permission Tests
# ============================================================================


def test_grant_resource_permission(test_user, db):
    """Test granting resource-specific permission."""
    # Create a resource
    resource = models.Resource(name="Test Resource", available=True)
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Grant permission
    perm = rbac.grant_resource_permission(
        resource_id=resource.id, user_id=test_user.id, action="update", db=db
    )

    assert perm is not None
    assert perm.resource_id == resource.id
    assert perm.user_id == test_user.id
    assert perm.action == "update"


def test_check_resource_permission(test_user, db):
    """Test checking resource-specific permission."""
    # Create resource
    resource = models.Resource(name="Test Resource", available=True)
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Grant permission
    rbac.grant_resource_permission(
        resource_id=resource.id, user_id=test_user.id, action="update", db=db
    )

    # Check permission
    assert rbac.check_resource_permission(test_user, resource, "update", db) is True
    assert rbac.check_resource_permission(test_user, resource, "delete", db) is False


def test_revoke_resource_permission(test_user, db):
    """Test revoking resource-specific permission."""
    # Create resource
    resource = models.Resource(name="Test Resource", available=True)
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Grant and then revoke permission
    rbac.grant_resource_permission(
        resource_id=resource.id, user_id=test_user.id, action="update", db=db
    )

    assert (
        rbac.revoke_resource_permission(
            resource_id=resource.id, user_id=test_user.id, action="update", db=db
        )
        is True
    )

    # Permission should be revoked
    assert rbac.check_resource_permission(test_user, resource, "update", db) is False
