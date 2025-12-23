import os
import tempfile
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.auth import hash_password
from app.database import get_db
from app.main import app, limiter

# Disable rate limiting for tests
limiter.enabled = False


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
    # Use v1 API endpoint
    response = client.post(
        "/api/v1/token", data={"username": "testuser", "password": "testpass123"}
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
