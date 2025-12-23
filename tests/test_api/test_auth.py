from fastapi import status

from app.utils.password import PasswordPolicy

# API v1 prefix
API_V1 = "/api/v1"


class TestAuth:
    """Test authentication endpoints"""

    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            f"{API_V1}/register",
            json={"username": "newuser", "password": "SecurePass123!"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be returned

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with existing username"""
        response = client.post(
            f"{API_V1}/register",
            json={
                "username": "testuser",  # Already exists
                "password": "AnotherPass123!",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_data(self, client):
        """Test registration with invalid data"""
        # Short username
        response = client.post(
            f"{API_V1}/register",
            json={
                "username": "ab",  # Too short
                "password": "ValidPass123!",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Short password
        response = client.post(
            f"{API_V1}/register",
            json={
                "username": "validuser",
                "password": "Aa1!",  # Too short
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_password_policy(self, client):
        """Test registration fails for weak passwords"""
        response = client.post(
            f"{API_V1}/register",
            json={
                "username": "policyuser",
                "password": "weakpass",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = response.json()["detail"]
        assert any("Password must" in error["msg"] for error in detail)

    def test_login_success(self, client, test_user):
        """Test successful login returns both access and refresh tokens"""
        response = client.post(
            f"{API_V1}/token", data={"username": "testuser", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials"""
        # Wrong password
        response = client.post(
            f"{API_V1}/token",
            data={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Wrong username
        response = client.post(
            f"{API_V1}/token",
            data={"username": "nonexistent", "password": "testpass123"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_warns_before_lockout(self, client, test_user):
        """Warn user as they approach lockout threshold"""
        response = None
        for _ in range(PasswordPolicy.MAX_LOGIN_ATTEMPTS - 2):
            response = client.post(
                f"{API_V1}/token",
                data={"username": "testuser", "password": "wrongpassword"},
            )
        assert response is not None
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "remaining" in response.json()["detail"].lower()

    def test_login_lockout_after_failed_attempts(self, client, test_user):
        """Lock account after too many failed login attempts"""
        response = None
        for _ in range(PasswordPolicy.MAX_LOGIN_ATTEMPTS):
            response = client.post(
                f"{API_V1}/token",
                data={"username": "testuser", "password": "wrongpassword"},
            )

        assert response is not None
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "locked" in response.json()["detail"].lower()

        # Subsequent attempts should report the account is locked
        locked_response = client.post(
            f"{API_V1}/token",
            data={"username": "testuser", "password": "wrongpassword"},
        )
        assert locked_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "account is locked" in locked_response.json()["detail"].lower()

    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication"""
        response = client.get(f"{API_V1}/reservations/my")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get(f"{API_V1}/reservations/my", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRefreshTokens:
    """Test refresh token functionality"""

    def test_refresh_token_success(self, client, test_user):
        """Test refreshing an access token with a valid refresh token"""
        # First login to get tokens
        login_response = client.post(
            f"{API_V1}/token", data={"username": "testuser", "password": "testpass123"}
        )
        assert login_response.status_code == status.HTTP_200_OK
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new tokens
        refresh_response = client.post(
            f"{API_V1}/token/refresh", params={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == status.HTTP_200_OK

        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        # New refresh token should be different (token rotation)
        assert data["refresh_token"] != refresh_token

    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token fails"""
        response = client.post(
            f"{API_V1}/token/refresh", params={"refresh_token": "invalid_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_token_reuse_fails(self, client, test_user):
        """Test that reusing an old refresh token fails (token rotation)"""
        # Login to get initial tokens
        login_response = client.post(
            f"{API_V1}/token", data={"username": "testuser", "password": "testpass123"}
        )
        old_refresh_token = login_response.json()["refresh_token"]

        # Use the refresh token once (this rotates it)
        first_refresh = client.post(
            f"{API_V1}/token/refresh", params={"refresh_token": old_refresh_token}
        )
        assert first_refresh.status_code == status.HTTP_200_OK

        # Try to use the old refresh token again - should fail
        second_refresh = client.post(
            f"{API_V1}/token/refresh", params={"refresh_token": old_refresh_token}
        )
        assert second_refresh.status_code == status.HTTP_401_UNAUTHORIZED
        assert "revoked" in second_refresh.json()["detail"].lower()

    def test_new_access_token_works(self, client, test_user):
        """Test that the new access token from refresh works for API calls"""
        # Login
        login_response = client.post(
            f"{API_V1}/token", data={"username": "testuser", "password": "testpass123"}
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh to get new access token
        refresh_response = client.post(
            f"{API_V1}/token/refresh", params={"refresh_token": refresh_token}
        )
        new_access_token = refresh_response.json()["access_token"]

        # Use new access token to access protected endpoint
        headers = {"Authorization": f"Bearer {new_access_token}"}
        user_response = client.get(f"{API_V1}/users/me", headers=headers)
        assert user_response.status_code == status.HTTP_200_OK
        assert user_response.json()["username"] == "testuser"

    def test_logout_revokes_tokens(self, client, test_user):
        """Test that logout revokes all refresh tokens"""
        # Login to get tokens
        login_response = client.post(
            f"{API_V1}/token", data={"username": "testuser", "password": "testpass123"}
        )
        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # Logout
        headers = {"Authorization": f"Bearer {access_token}"}
        logout_response = client.post(f"{API_V1}/logout", headers=headers)
        assert logout_response.status_code == status.HTTP_200_OK
        assert "revoked_tokens" in logout_response.json()

        # Try to use the refresh token - should fail
        refresh_response = client.post(
            f"{API_V1}/token/refresh", params={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
