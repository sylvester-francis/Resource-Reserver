import os
import tempfile
from datetime import UTC, datetime

# Disable rate limiting before importing app
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.auth import hash_password
from app.config import get_settings
from app.core.rate_limiter import reset_rate_limiter
from app.database import get_db
from app.main import app, limiter

# Clear settings cache and reload with rate limiting disabled
get_settings.cache_clear()
_ = get_settings()  # Reload settings

# Disable slowapi rate limiting for tests
limiter.enabled = False

# Reset the custom rate limiter before tests
reset_rate_limiter()


# Test database setup
@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database for each test"""
    # Create temporary file for test database
    db_fd, db_path = tempfile.mkstemp()
    database_url = f"sqlite:///{db_path}"

    # Create engine and tables
    engine = create_engine(database_url, connect_args={"check_same_thread": False})  # noqa : E501
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # noqa : E501

    models.Base.metadata.create_all(bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    """FastAPI test client"""
    # Reset rate limiter before creating client to avoid rate limit issues
    reset_rate_limiter()
    return TestClient(app)


@pytest.fixture
def test_user(test_db):
    """Create a test user in the database"""
    db = test_db()
    try:
        user = models.User(
            username="testuser", hashed_password=hash_password("testpass123")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    # Reset rate limiter before getting token to avoid rate limit issues
    reset_rate_limiter()

    # Use v1 API endpoint
    response = client.post(
        "/api/v1/token", data={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_user(test_db):
    """Create an admin test user in the database"""
    db = test_db()
    try:
        hashed_password = hash_password("adminpass123")
        user = models.User(username="adminuser", hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create admin role if not exists
        admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
        if not admin_role:
            admin_role = models.Role(name="admin", description="Administrator role")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        # Assign admin role to user
        user_role = models.UserRole(user_id=user.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()

        return user
    finally:
        db.close()


@pytest.fixture
def admin_headers(client, admin_user):
    """Get authentication headers for admin user"""
    reset_rate_limiter()

    response = client.post(
        "/api/v1/token", data={"username": "adminuser", "password": "adminpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_resource(test_db):
    """Create a test resource"""
    db = test_db()
    try:
        resource = models.Resource(
            name="Test Conference Room",
            tags=["meeting", "conference"],
            available=True,  # noqa : E501
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource
    finally:
        db.close()


@pytest.fixture
def future_datetime():
    """Future datetime for reservations"""
    from datetime import timedelta

    return datetime.now(UTC) + timedelta(days=1)
