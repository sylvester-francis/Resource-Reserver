"""Unit tests for user service behavior."""

import pytest
from sqlalchemy.exc import IntegrityError

from app import schemas
from app.auth import verify_password
from app.services import UserService


class TestUserService:
    """Test UserService business logic"""

    def test_create_user_success(self, test_db):
        """Test successful user creation"""
        db = test_db()
        service = UserService(db)

        user_data = schemas.UserCreate(username="testuser", password="SecurePass123!")

        try:
            user = service.create_user(user_data)

            assert user.id is not None
            assert user.username == "testuser"
            assert user.hashed_password != "SecurePass123!"  # Should be hashed
            assert verify_password("SecurePass123!", user.hashed_password)
        finally:
            db.close()

    def test_create_user_duplicate_username(self, test_db):
        """Test creating user with duplicate username"""
        db = test_db()
        service = UserService(db)

        user_data = schemas.UserCreate(username="duplicate", password="Password123!")

        try:
            # Create first user
            service.create_user(user_data)

            # Try to create duplicate
            with pytest.raises(IntegrityError):
                service.create_user(user_data)
        finally:
            db.close()

    def test_get_user_by_username(self, test_db, test_user):
        """Test retrieving user by username"""
        db = test_db()
        service = UserService(db)

        try:
            found_user = service.get_user_by_username("testuser")
            assert found_user is not None
            assert found_user.username == "testuser"

            # Test case insensitive search
            found_user_upper = service.get_user_by_username("TESTUSER")
            assert found_user_upper is not None
            assert found_user_upper.id == found_user.id

            # Test non-existent user
            not_found = service.get_user_by_username("nonexistent")
            assert not_found is None
        finally:
            db.close()
