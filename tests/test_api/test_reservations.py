from fastapi import status
from datetime import datetime, timezone, timedelta


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
            "/reservations", json=reservation_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["resource_id"] == test_resource.id
        assert data["status"] == "active"
        assert "id" in data
        assert "resource" in data

    def test_create_reservation_past_time(self, client, auth_headers, test_resource):
        """Test reservation creation with past time"""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = past_time + timedelta(hours=1)

        reservation_data = {
            "resource_id": test_resource.id,
            "start_time": past_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        response = client.post(
            "/reservations", json=reservation_data, headers=auth_headers
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
            "/reservations", json=reservation_data, headers=auth_headers
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
            "/reservations", json=reservation_data, headers=auth_headers
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
            "/reservations", json=conflicting_data, headers=auth_headers
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

        client.post("/reservations", json=reservation_data, headers=auth_headers)

        # Get reservations
        response = client.get("/reservations/my", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
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
            "/reservations", json=reservation_data, headers=auth_headers
        )
        reservation_id = response.json()["id"]

        # Cancel reservation
        cancel_data = {"reason": "Test cancellation"}
        response = client.post(
            f"/reservations/{reservation_id}/cancel",
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
            "/reservations/99999/cancel", json=cancel_data, headers=auth_headers
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
            "/reservations", json=reservation_data, headers=auth_headers
        )
        reservation_id = response.json()["id"]

        # Cancel it
        cancel_data = {"reason": "Test cancellation"}
        client.post(
            f"/reservations/{reservation_id}/cancel",
            json=cancel_data,
            headers=auth_headers,
        )

        # Get history
        response = client.get(
            f"/reservations/{reservation_id}/history", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # Should have created + cancelled events

        actions = [entry["action"] for entry in data]
        assert "created" in actions
        assert "cancelled" in actions
