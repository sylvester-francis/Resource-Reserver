"""Integration tests for auth API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.database import get_db
from app.main import app
from app.models import Base, User
from app.rbac import create_default_roles

# Test database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Setup test database before each test."""
    Base.metadata.create_all(bind=engine)

    # Create default roles
    db = TestingSessionLocal()
    create_default_roles(db)
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers():
    """Create a test user and return auth headers."""
    from app.rbac import assign_role

    # Create user
    db = TestingSessionLocal()
    user = User(
        username="testuser",
        hashed_password=hash_password("testpass123"),
        email="test@example.com",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign user role
    assign_role(user.id, "user", db)
    db.close()

    # Login to get token
    response = client.post(
        "/token", data={"username": "testuser", "password": "testpass123"}
    )
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers():
    """Create an admin test user and return auth headers."""
    from app.rbac import assign_role

    # Create admin user
    db = TestingSessionLocal()
    user = User(
        username="adminuser",
        hashed_password=hash_password("adminpass123"),
        email="admin@example.com",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign admin role
    assign_role(user.id, "admin", db)
    db.close()

    # Login to get token
    response = client.post(
        "/token", data={"username": "adminuser", "password": "adminpass123"}
    )
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# MFA Endpoint Tests
# ============================================================================


def test_mfa_setup(auth_headers):
    """Test MFA setup endpoint."""
    response = client.post("/auth/mfa/setup", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    assert "qr_code" in data
    assert "backup_codes" in data


def test_mfa_verify_and_enable(auth_headers):
    """Test MFA verification and enablement."""
    import pyotp

    # Setup MFA
    setup_response = client.post("/auth/mfa/setup", headers=auth_headers)
    secret = setup_response.json()["secret"]

    # Generate valid code
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    # Verify and enable
    response = client.post(
        "/auth/mfa/verify", headers=auth_headers, json={"code": valid_code}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "MFA enabled successfully"


def test_mfa_disable(auth_headers):
    """Test MFA disablement."""
    import pyotp

    # Setup and enable MFA
    setup_response = client.post("/auth/mfa/setup", headers=auth_headers)
    secret = setup_response.json()["secret"]
    totp = pyotp.TOTP(secret)

    client.post("/auth/mfa/verify", headers=auth_headers, json={"code": totp.now()})

    # Disable MFA
    response = client.post(
        "/auth/mfa/disable", headers=auth_headers, json={"password": "testpass123"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "MFA disabled successfully"


# ============================================================================
# Role Endpoint Tests
# ============================================================================


def test_list_roles(admin_auth_headers):
    """Test listing all roles (requires admin)."""
    response = client.get("/roles/", headers=admin_auth_headers)

    assert response.status_code == 200
    roles = response.json()
    assert len(roles) >= 3  # At least admin, user, guest
    role_names = [r["name"] for r in roles]
    assert "admin" in role_names
    assert "user" in role_names
    assert "guest" in role_names


def test_get_my_roles(auth_headers):
    """Test getting current user's roles."""
    response = client.get("/roles/my-roles", headers=auth_headers)

    assert response.status_code == 200
    # New users might not have roles assigned yet
    roles = response.json()
    assert isinstance(roles, list)


# ============================================================================
# OAuth2 Client Tests
# ============================================================================


def test_create_oauth_client(auth_headers):
    """Test creating an OAuth2 client."""
    response = client.post(
        "/oauth/clients",
        headers=auth_headers,
        json={
            "client_name": "Test App",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": "authorization_code",
            "scope": "read write",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "client_id" in data
    assert "client_secret" in data
    assert data["client_name"] == "Test App"


def test_list_oauth_clients(auth_headers):
    """Test listing OAuth2 clients."""
    # Create a client first
    client.post(
        "/oauth/clients",
        headers=auth_headers,
        json={
            "client_name": "Test App",
            "redirect_uris": ["http://localhost:3000/callback"],
        },
    )

    # List clients
    response = client.get("/oauth/clients", headers=auth_headers)

    assert response.status_code == 200
    clients = response.json()
    assert len(clients) >= 1
    assert clients[0]["client_name"] == "Test App"


def test_delete_oauth_client(auth_headers):
    """Test deleting an OAuth2 client."""
    # Create a client
    create_response = client.post(
        "/oauth/clients",
        headers=auth_headers,
        json={
            "client_name": "Test App",
            "redirect_uris": ["http://localhost:3000/callback"],
        },
    )
    client_id = create_response.json()["client_id"]

    # Delete client
    response = client.delete(f"/oauth/clients/{client_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["message"] == "OAuth2 client deleted successfully"


# ============================================================================
# OAuth2 Authorization Flow Tests
# ============================================================================


def test_oauth_authorization_flow(auth_headers):
    """Test complete OAuth2 authorization code flow."""
    # Create OAuth client
    create_response = client.post(
        "/oauth/clients",
        headers=auth_headers,
        json={
            "client_name": "Test App",
            "redirect_uris": ["http://localhost:3000/callback"],
        },
    )
    client_id = create_response.json()["client_id"]
    client_secret = create_response.json()["client_secret"]

    # Step 1: Get authorization code
    auth_response = client.get(
        f"/oauth/authorize?client_id={client_id}&redirect_uri=http://localhost:3000/callback&scope=read",
        headers=auth_headers,
    )

    assert auth_response.status_code == 200
    code = auth_response.json()["code"]

    # Step 2: Exchange code for token
    token_response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )

    assert token_response.status_code == 200
    token_data = token_response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "Bearer"


def test_oauth_token_introspection(auth_headers):
    """Test OAuth2 token introspection."""
    # Create client and get token
    create_response = client.post(
        "/oauth/clients",
        headers=auth_headers,
        json={
            "client_name": "Test App",
            "redirect_uris": ["http://localhost:3000/callback"],
        },
    )
    client_id = create_response.json()["client_id"]
    client_secret = create_response.json()["client_secret"]

    # Get authorization code and token
    auth_response = client.get(
        f"/oauth/authorize?client_id={client_id}&redirect_uri=http://localhost:3000/callback&scope=read",
        headers=auth_headers,
    )
    code = auth_response.json()["code"]

    token_response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    access_token = token_response.json()["access_token"]

    # Introspect token
    introspect_response = client.post(
        "/oauth/introspect",
        data={
            "token": access_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )

    assert introspect_response.status_code == 200
    data = introspect_response.json()
    assert data["active"] is True
    assert data["scope"] == "read"


def test_oauth_protected_endpoint(auth_headers):
    """Test accessing protected endpoint with OAuth2 token."""
    # Create client and get token
    create_response = client.post(
        "/oauth/clients",
        headers=auth_headers,
        json={
            "client_name": "Test App",
            "redirect_uris": ["http://localhost:3000/callback"],
        },
    )
    client_id = create_response.json()["client_id"]
    client_secret = create_response.json()["client_secret"]

    # Get token
    auth_response = client.get(
        f"/oauth/authorize?client_id={client_id}&redirect_uri=http://localhost:3000/callback&scope=read",
        headers=auth_headers,
    )
    code = auth_response.json()["code"]

    token_response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    access_token = token_response.json()["access_token"]

    # Access protected endpoint
    protected_response = client.get(
        "/oauth/protected", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert protected_response.status_code == 200
    assert protected_response.json()["message"] == "Access granted via OAuth2"


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_mfa_setup_when_already_enabled(auth_headers):
    """Test MFA setup fails when already enabled."""
    import pyotp

    # Setup and enable MFA
    setup_response = client.post("/auth/mfa/setup", headers=auth_headers)
    secret = setup_response.json()["secret"]
    totp = pyotp.TOTP(secret)

    client.post("/auth/mfa/verify", headers=auth_headers, json={"code": totp.now()})

    # Try to setup again
    response = client.post("/auth/mfa/setup", headers=auth_headers)

    assert response.status_code == 400
    assert "already enabled" in response.json()["detail"]


def test_oauth_invalid_client_credentials():
    """Test OAuth2 with invalid client credentials."""
    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "invalid_id",
            "client_secret": "invalid_secret",
        },
    )

    assert response.status_code == 401
    assert "Invalid client credentials" in response.json()["detail"]


def test_oauth_invalid_authorization_code(auth_headers):
    """Test OAuth2 with invalid authorization code."""
    # Create a client first
    create_response = client.post(
        "/oauth/clients",
        headers=auth_headers,
        json={
            "client_name": "Test App",
            "redirect_uris": ["http://localhost:3000/callback"],
        },
    )
    client_id = create_response.json()["client_id"]
    client_secret = create_response.json()["client_secret"]

    # Try to exchange invalid code
    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "invalid_code",
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )

    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]
