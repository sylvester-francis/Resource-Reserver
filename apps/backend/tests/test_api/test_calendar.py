"""API tests for calendar integration endpoints."""

from datetime import datetime, timedelta

from fastapi import status

# API v1 prefix
API_V1 = "/api/v1/calendar"


class TestCalendarSubscription:
    """Test calendar subscription URL endpoints."""

    def test_get_subscription_url(self, client, auth_headers):
        """Test getting calendar subscription URL creates token."""
        response = client.get(
            f"{API_V1}/subscription-url",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "url" in data
        assert "token" in data
        assert data["token"] in data["url"]

    def test_get_subscription_url_unauthenticated_fails(self, client):
        """Test unauthenticated request fails."""
        response = client.get(f"{API_V1}/subscription-url")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regenerate_calendar_token(self, client, auth_headers):
        """Test regenerating calendar token."""
        # Get initial token
        initial_response = client.get(
            f"{API_V1}/subscription-url",
            headers=auth_headers,
        )
        initial_token = initial_response.json()["token"]

        # Regenerate
        response = client.post(
            f"{API_V1}/regenerate-token",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "token" in data
        assert "url" in data
        assert data["token"] != initial_token

    def test_regenerate_token_unauthenticated_fails(self, client):
        """Test unauthenticated regeneration fails."""
        response = client.post(f"{API_V1}/regenerate-token")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCalendarFeed:
    """Test iCal feed endpoints."""

    def test_get_calendar_feed_with_token(self, client, auth_headers):
        """Test getting calendar feed with valid token."""
        # First get a subscription URL to obtain token
        sub_response = client.get(
            f"{API_V1}/subscription-url",
            headers=auth_headers,
        )
        token = sub_response.json()["token"]

        # Get feed with token
        response = client.get(f"{API_V1}/feed/{token}.ics")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"
        assert b"BEGIN:VCALENDAR" in response.content

    def test_get_calendar_feed_invalid_token(self, client):
        """Test getting calendar feed with invalid token fails."""
        response = client.get(f"{API_V1}/feed/invalid-token-12345.ics")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_calendar_feed_with_date_range(self, client, auth_headers):
        """Test getting calendar feed with custom date range."""
        # Get token
        sub_response = client.get(
            f"{API_V1}/subscription-url",
            headers=auth_headers,
        )
        token = sub_response.json()["token"]

        # Get feed with params
        response = client.get(
            f"{API_V1}/feed/{token}.ics",
            params={"days_back": 7, "days_ahead": 30},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_my_calendar_feed(self, client, auth_headers):
        """Test authenticated calendar feed endpoint."""
        response = client.get(
            f"{API_V1}/my-feed",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"
        assert b"BEGIN:VCALENDAR" in response.content

    def test_get_my_calendar_feed_with_params(self, client, auth_headers):
        """Test authenticated feed with custom parameters."""
        response = client.get(
            f"{API_V1}/my-feed",
            params={"days_back": 14, "days_ahead": 60},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK


class TestReservationExport:
    """Test individual reservation export."""

    def test_export_reservation_success(
        self, client, auth_headers, test_resource, test_user
    ):
        """Test exporting a reservation as iCal."""
        # Create a reservation first
        start_time = (datetime.now() + timedelta(days=1)).isoformat()
        end_time = (datetime.now() + timedelta(days=1, hours=2)).isoformat()

        create_response = client.post(
            "/api/v1/reservations",
            json={
                "resource_id": test_resource.id,
                "start_time": start_time,
                "end_time": end_time,
            },
            headers=auth_headers,
        )

        if create_response.status_code == status.HTTP_201_CREATED:
            reservation_id = create_response.json()["id"]

            # Export it
            response = client.get(
                f"{API_V1}/export/{reservation_id}.ics",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "text/calendar; charset=utf-8"
            assert b"BEGIN:VEVENT" in response.content

    def test_export_reservation_not_found(self, client, auth_headers):
        """Test exporting non-existent reservation."""
        response = client.get(
            f"{API_V1}/export/99999.ics",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_export_other_user_reservation_fails(
        self, client, auth_headers, admin_headers, test_resource
    ):
        """Test user cannot export another user's reservation."""
        # Create reservation as admin
        start_time = (datetime.now() + timedelta(days=2)).isoformat()
        end_time = (datetime.now() + timedelta(days=2, hours=1)).isoformat()

        create_response = client.post(
            "/api/v1/reservations",
            json={
                "resource_id": test_resource.id,
                "start_time": start_time,
                "end_time": end_time,
            },
            headers=admin_headers,
        )

        if create_response.status_code == status.HTTP_201_CREATED:
            reservation_id = create_response.json()["id"]

            # Try to export as regular user
            response = client.get(
                f"{API_V1}/export/{reservation_id}.ics",
                headers=auth_headers,
            )

            # Should fail with 403 or 404
            assert response.status_code in [
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ]

    def test_export_unauthenticated_fails(self, client):
        """Test unauthenticated export fails."""
        response = client.get(f"{API_V1}/export/1.ics")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
