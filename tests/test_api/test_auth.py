from fastapi import status

# API v1 prefix
API_V1 = "/api/v1"


class TestAuth:
    """Test authentication endpoints"""

    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            f"{API_V1}/register",
            json={"username": "newuser", "password": "securepass123"},
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
                "password": "anotherpass",
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
                "password": "validpass123",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Short password
        response = client.post(
            f"{API_V1}/register",
            json={
                "username": "validuser",
                "password": "123",  # Too short
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            f"{API_V1}/token", data={"username": "testuser", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
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

    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication"""
        response = client.get(f"{API_V1}/reservations/my")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get(f"{API_V1}/reservations/my", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
