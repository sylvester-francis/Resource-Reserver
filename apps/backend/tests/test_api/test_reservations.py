"""API tests for reservation endpoints."""

from datetime import UTC, datetime, timedelta

from fastapi import status

# API v1 prefix
API_V1 = "/api/v1"


class TestReservations:
    """Test reservation management endpoints"""

    def test_create_reservation_success(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test successful reservation creation"""
        start_time = future_datetime
        end_time = start_time + timedelta(hours=2)

        reservation_data = {
            "resource_id": test_resource.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        response = client.post(
            f"{API_V1}/reservations", json=reservation_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["resource_id"] == test_resource.id
        assert data["status"] == "active"
        assert "id" in data
        assert "resource" in data

    def test_create_reservation_past_time(self, client, auth_headers, test_resource):
        """Test reservation creation with past time"""
        past_time = datetime.now(UTC) - timedelta(hours=1)
        end_time = past_time + timedelta(hours=1)

        reservation_data = {
            "resource_id": test_resource.id,
            "start_time": past_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        response = client.post(
            f"{API_V1}/reservations", json=reservation_data, headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_reservation_invalid_time_range(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test reservation with end time before start time"""
        start_time = future_datetime
        end_time = start_time - timedelta(hours=1)  # End before start

        reservation_data = {
            "resource_id": test_resource.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        response = client.post(
            f"{API_V1}/reservations", json=reservation_data, headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_conflicting_reservation(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test creating conflicting reservations"""
        start_time = future_datetime
        end_time = start_time + timedelta(hours=2)

        reservation_data = {
            "resource_id": test_resource.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        # Create first reservation
        response = client.post(
            f"{API_V1}/reservations", json=reservation_data, headers=auth_headers
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Try to create conflicting reservation
        conflicting_start = start_time + timedelta(minutes=30)
        conflicting_end = end_time + timedelta(minutes=30)

        conflicting_data = {
            "resource_id": test_resource.id,
            "start_time": conflicting_start.isoformat(),
            "end_time": conflicting_end.isoformat(),
        }

        response = client.post(
            f"{API_V1}/reservations", json=conflicting_data, headers=auth_headers
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "conflicts" in response.json()["detail"].lower()

    def test_get_my_reservations(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test getting user's reservations"""
        # Create a reservation first
        start_time = future_datetime
        end_time = start_time + timedelta(hours=1)

        reservation_data = {
            "resource_id": test_resource.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        client.post(
            f"{API_V1}/reservations", json=reservation_data, headers=auth_headers
        )

        # Get reservations
        response = client.get(f"{API_V1}/reservations/my", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        data = payload["data"]
        assert isinstance(data, list)
        assert len(data) >= 1

        # Check reservation details
        reservation = data[0]
        assert reservation["resource_id"] == test_resource.id
        assert reservation["status"] == "active"

    def test_cancel_reservation_success(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test successful reservation cancellation"""
        # Create reservation
        start_time = future_datetime
        end_time = start_time + timedelta(hours=1)

        reservation_data = {
            "resource_id": test_resource.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        response = client.post(
            f"{API_V1}/reservations", json=reservation_data, headers=auth_headers
        )
        reservation_id = response.json()["id"]

        # Cancel reservation
        cancel_data = {"reason": "Test cancellation"}
        response = client.post(
            f"{API_V1}/reservations/{reservation_id}/cancel",
            json=cancel_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "cancelled" in data["message"].lower()

    def test_cancel_nonexistent_reservation(self, client, auth_headers):
        """Test cancelling non-existent reservation"""
        cancel_data = {"reason": "Test"}
        response = client.post(
            f"{API_V1}/reservations/99999/cancel",
            json=cancel_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_reservation_history(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test getting reservation history"""
        # Create and cancel a reservation
        start_time = future_datetime
        end_time = start_time + timedelta(hours=1)

        reservation_data = {
            "resource_id": test_resource.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        response = client.post(
            f"{API_V1}/reservations", json=reservation_data, headers=auth_headers
        )
        reservation_id = response.json()["id"]

        # Cancel it
        cancel_data = {"reason": "Test cancellation"}
        client.post(
            f"{API_V1}/reservations/{reservation_id}/cancel",
            json=cancel_data,
            headers=auth_headers,
        )

        # Get history
        response = client.get(
            f"{API_V1}/reservations/{reservation_id}/history", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # Should have created + cancelled events

        actions = [entry["action"] for entry in data]
        assert "created" in actions
        assert "cancelled" in actions

    def test_reservations_pagination(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test cursor pagination for reservations"""
        start_time = future_datetime
        for offset in range(4):
            reservation_data = {
                "resource_id": test_resource.id,
                "start_time": (start_time + timedelta(hours=offset * 2)).isoformat(),
                "end_time": (start_time + timedelta(hours=offset * 2 + 1)).isoformat(),
            }
            response = client.post(
                f"{API_V1}/reservations",
                json=reservation_data,
                headers=auth_headers,
            )
            assert response.status_code == status.HTTP_201_CREATED

        first_page = client.get(
            f"{API_V1}/reservations/my",
            headers=auth_headers,
            params={
                "limit": 2,
                "sort_by": "start_time",
                "sort_order": "asc",
            },
        )
        assert first_page.status_code == status.HTTP_200_OK
        payload = first_page.json()
        assert len(payload["data"]) == 2
        assert payload["has_more"] is True
        assert payload["next_cursor"]

        second_page = client.get(
            f"{API_V1}/reservations/my",
            headers=auth_headers,
            params={
                "limit": 2,
                "sort_by": "start_time",
                "sort_order": "asc",
                "cursor": payload["next_cursor"],
            },
        )
        assert second_page.status_code == status.HTTP_200_OK
        payload_next = second_page.json()
        ids_first = {item["id"] for item in payload["data"]}
        ids_next = {item["id"] for item in payload_next["data"]}
        assert ids_first.isdisjoint(ids_next)

    def test_create_recurring_reservations(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test creating a recurring reservation series"""
        start_time = future_datetime
        end_time = start_time + timedelta(hours=1)

        request_data = {
            "resource_id": test_resource.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "recurrence": {
                "frequency": "daily",
                "interval": 1,
                "end_type": "after_count",
                "occurrence_count": 3,
            },
        }

        response = client.post(
            f"{API_V1}/reservations/recurring", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert all(res["recurrence_rule_id"] is not None for res in data)

    def test_recurring_reservations_conflict(
        self, client, auth_headers, test_resource, future_datetime
    ):
        """Test conflict detection for recurring reservations"""
        # Create an existing reservation to force conflict
        client.post(
            f"{API_V1}/reservations",
            json={
                "resource_id": test_resource.id,
                "start_time": future_datetime.isoformat(),
                "end_time": (future_datetime + timedelta(hours=1)).isoformat(),
            },
            headers=auth_headers,
        )

        request_data = {
            "resource_id": test_resource.id,
            "start_time": future_datetime.isoformat(),
            "end_time": (future_datetime + timedelta(hours=1)).isoformat(),
            "recurrence": {
                "frequency": "daily",
                "interval": 1,
                "end_type": "after_count",
                "occurrence_count": 2,
            },
        }

        response = client.post(
            f"{API_V1}/reservations/recurring", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_409_CONFLICT
