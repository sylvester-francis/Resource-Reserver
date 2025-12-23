"""Tests for waitlist functionality."""

from datetime import timedelta

from fastapi import status

from app import models
from app.auth import hash_password

# API v1 prefix
API_V1 = "/api/v1"


class TestWaitlist:
    """Test waitlist endpoints."""

    def test_join_waitlist_success(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test successfully joining a waitlist."""
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
                "flexible_time": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["resource_id"] == test_resource.id
        assert data["status"] == "waiting"
        assert data["position"] == 1
        assert data["flexible_time"] is False

    def test_join_waitlist_with_flexible_time(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test joining waitlist with flexible time option."""
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
                "flexible_time": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["flexible_time"] is True

    def test_join_waitlist_without_auth(self, client, test_resource, future_datetime):
        """Test joining waitlist without authentication."""
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_join_waitlist_invalid_resource(
        self, client, auth_headers, future_datetime
    ):
        """Test joining waitlist for non-existent resource."""
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": 99999,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_join_waitlist_past_time(self, client, auth_headers, test_resource):
        """Test joining waitlist with past time."""
        from datetime import UTC, datetime

        past_time = datetime.now(UTC) - timedelta(hours=1)
        end_time = past_time + timedelta(hours=2)

        response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": past_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_join_waitlist_duplicate(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test joining waitlist twice for same slot."""
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        # First join
        response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Second join (same slot)
        response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_waitlist_entries(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test listing user's waitlist entries."""
        # Create a waitlist entry first
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=auth_headers,
        )

        # List entries
        response = client.get(f"{API_V1}/waitlist", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 1

    def test_get_waitlist_entry(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test getting a specific waitlist entry."""
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        # Create entry
        create_response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=auth_headers,
        )
        entry_id = create_response.json()["id"]

        # Get entry
        response = client.get(f"{API_V1}/waitlist/{entry_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == entry_id
        assert data["resource_id"] == test_resource.id

    def test_leave_waitlist(self, client, auth_headers, test_resource, future_datetime):
        """Test leaving the waitlist."""
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        # Create entry
        create_response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=auth_headers,
        )
        entry_id = create_response.json()["id"]

        # Leave waitlist
        response = client.delete(f"{API_V1}/waitlist/{entry_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "cancelled"

    def test_leave_waitlist_not_found(self, client, auth_headers):
        """Test leaving non-existent waitlist entry."""
        response = client.delete(f"{API_V1}/waitlist/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_resource_waitlist(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test getting waitlist for a specific resource."""
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        # Create entry
        client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=auth_headers,
        )

        # Get resource waitlist
        response = client.get(
            f"{API_V1}/waitlist/resource/{test_resource.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_waitlist_position_ordering(
        self, client, test_db, test_resource, future_datetime
    ):
        """Test that waitlist positions are assigned correctly."""

        db = test_db()
        start_time = future_datetime + timedelta(hours=5)
        end_time = start_time + timedelta(hours=2)

        # Create two users and join waitlist
        users_and_tokens = []
        for i in range(2):
            user = models.User(
                username=f"waitlistuser{i}",
                hashed_password=hash_password("testpass123"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Get token
            response = client.post(
                "/api/v1/token",
                data={
                    "username": f"waitlistuser{i}",
                    "password": "testpass123",
                },
            )
            token = response.json()["access_token"]
            users_and_tokens.append((user, {"Authorization": f"Bearer {token}"}))

        db.close()

        # First user joins waitlist
        response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=users_and_tokens[0][1],
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["position"] == 1

        # Second user joins waitlist
        response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=users_and_tokens[1][1],
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["position"] == 2

    def test_accept_offer_no_offer(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test accepting offer when none exists."""
        start_time = future_datetime + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        # Create entry (will be in waiting status, not offered)
        create_response = client.post(
            f"{API_V1}/waitlist",
            json={
                "resource_id": test_resource.id,
                "desired_start": start_time.isoformat(),
                "desired_end": end_time.isoformat(),
            },
            headers=auth_headers,
        )
        entry_id = create_response.json()["id"]

        # Try to accept (no offer)
        response = client.post(
            f"{API_V1}/waitlist/{entry_id}/accept",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
