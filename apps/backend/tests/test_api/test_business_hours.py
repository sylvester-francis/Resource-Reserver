"""API tests for business hours and availability endpoints."""

from datetime import date, timedelta

from fastapi import status

# API v1 prefix
API_V1 = "/api/v1"


class TestResourceBusinessHours:
    """Test resource-specific business hours endpoints."""

    def test_get_resource_business_hours_empty(
        self, client, auth_headers, test_resource
    ):
        """Test getting business hours for resource with no custom hours."""
        response = client.get(
            f"{API_V1}/resources/{test_resource.id}/business-hours",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        # May return empty or default global hours
        assert isinstance(response.json(), list)

    def test_set_resource_business_hours_success(
        self, client, admin_headers, test_resource
    ):
        """Test setting business hours for a resource as admin."""
        hours_data = {
            "hours": [
                {
                    "day_of_week": 0,  # Monday
                    "open_time": "09:00",
                    "close_time": "17:00",
                },
                {
                    "day_of_week": 1,  # Tuesday
                    "open_time": "09:00",
                    "close_time": "17:00",
                },
                {
                    "day_of_week": 2,  # Wednesday
                    "open_time": "10:00",
                    "close_time": "18:00",
                },
            ]
        }

        response = client.put(
            f"{API_V1}/resources/{test_resource.id}/business-hours",
            json=hours_data,
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert any(h["day_of_week"] == 0 for h in data)

    def test_set_resource_business_hours_non_admin_fails(
        self, client, auth_headers, test_resource
    ):
        """Test non-admin cannot set resource business hours."""
        hours_data = {
            "hours": [
                {
                    "day_of_week": 0,
                    "open_time": "09:00",
                    "close_time": "17:00",
                }
            ]
        }

        response = client.put(
            f"{API_V1}/resources/{test_resource.id}/business-hours",
            json=hours_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_set_resource_business_hours_resource_not_found(
        self, client, admin_headers
    ):
        """Test setting hours for non-existent resource."""
        response = client.put(
            f"{API_V1}/resources/99999/business-hours",
            json={"hours": []},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_resource_business_hours_after_set(
        self, client, admin_headers, test_resource
    ):
        """Test getting business hours after setting them."""
        # Set hours
        hours_data = {
            "hours": [
                {
                    "day_of_week": 4,  # Friday
                    "open_time": "08:00",
                    "close_time": "16:00",
                }
            ]
        }
        client.put(
            f"{API_V1}/resources/{test_resource.id}/business-hours",
            json=hours_data,
            headers=admin_headers,
        )

        # Get hours
        response = client.get(
            f"{API_V1}/resources/{test_resource.id}/business-hours",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        friday_hours = [h for h in data if h["day_of_week"] == 4]
        assert len(friday_hours) == 1
        assert friday_hours[0]["open_time"] == "08:00:00"
        assert friday_hours[0]["close_time"] == "16:00:00"


class TestGlobalBusinessHours:
    """Test global default business hours endpoints."""

    def test_get_global_business_hours(self, client, auth_headers):
        """Test getting global business hours."""
        response = client.get(
            f"{API_V1}/business-hours/global",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_set_global_business_hours_success(self, client, admin_headers):
        """Test setting global business hours as admin."""
        hours_data = {
            "hours": [
                {
                    "day_of_week": 0,
                    "open_time": "08:00",
                    "close_time": "18:00",
                },
                {
                    "day_of_week": 1,
                    "open_time": "08:00",
                    "close_time": "18:00",
                },
            ]
        }

        response = client.put(
            f"{API_V1}/business-hours/global",
            json=hours_data,
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

    def test_set_global_business_hours_non_admin_fails(self, client, auth_headers):
        """Test non-admin cannot set global business hours."""
        response = client.put(
            f"{API_V1}/business-hours/global",
            json={"hours": []},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAvailableSlots:
    """Test available time slots endpoints."""

    def test_get_available_slots(self, client, auth_headers, test_resource):
        """Test getting available slots for a resource."""
        target_date = (date.today() + timedelta(days=1)).isoformat()

        response = client.get(
            f"{API_V1}/resources/{test_resource.id}/available-slots",
            params={"date": target_date},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "slots" in data or isinstance(data, list)

    def test_get_available_slots_with_duration(
        self, client, auth_headers, test_resource
    ):
        """Test getting available slots with specific duration."""
        target_date = (date.today() + timedelta(days=1)).isoformat()

        response = client.get(
            f"{API_V1}/resources/{test_resource.id}/available-slots",
            params={"date": target_date, "slot_duration": 60},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_available_slots_resource_not_found(self, client, auth_headers):
        """Test getting slots for non-existent resource."""
        target_date = (date.today() + timedelta(days=1)).isoformat()

        response = client.get(
            f"{API_V1}/resources/99999/available-slots",
            params={"date": target_date},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_next_available_slot(self, client, auth_headers, test_resource):
        """Test getting next available slot for a resource."""
        response = client.get(
            f"{API_V1}/resources/{test_resource.id}/next-available",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_next_available_slot_with_params(
        self, client, auth_headers, test_resource
    ):
        """Test getting next available slot with custom params."""
        response = client.get(
            f"{API_V1}/resources/{test_resource.id}/next-available",
            params={"slot_duration": 120, "days_ahead": 7},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK


class TestBlackoutDates:
    """Test blackout date endpoints."""

    def test_get_resource_blackout_dates(self, client, auth_headers, test_resource):
        """Test getting blackout dates for a resource."""
        response = client.get(
            f"{API_V1}/resources/{test_resource.id}/blackout-dates",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_resource_blackout_dates_exclude_global(
        self, client, auth_headers, test_resource
    ):
        """Test getting blackout dates excluding global."""
        response = client.get(
            f"{API_V1}/resources/{test_resource.id}/blackout-dates",
            params={"include_global": False},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_add_resource_blackout_date_success(
        self, client, admin_headers, test_resource
    ):
        """Test adding a blackout date for a resource."""
        blackout_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            f"{API_V1}/resources/{test_resource.id}/blackout-dates",
            json={"date": blackout_date, "reason": "Maintenance"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["reason"] == "Maintenance"

    def test_add_resource_blackout_date_non_admin_fails(
        self, client, auth_headers, test_resource
    ):
        """Test non-admin cannot add blackout dates."""
        blackout_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            f"{API_V1}/resources/{test_resource.id}/blackout-dates",
            json={"date": blackout_date, "reason": "Test"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_global_blackout_dates(self, client, auth_headers):
        """Test getting global blackout dates."""
        response = client.get(
            f"{API_V1}/blackout-dates",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_add_global_blackout_date_success(self, client, admin_headers):
        """Test adding a global blackout date."""
        blackout_date = (date.today() + timedelta(days=60)).isoformat()
        response = client.post(
            f"{API_V1}/blackout-dates",
            json={"date": blackout_date, "reason": "Company Holiday"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["reason"] == "Company Holiday"

    def test_add_global_blackout_date_non_admin_fails(self, client, auth_headers):
        """Test non-admin cannot add global blackout dates."""
        blackout_date = (date.today() + timedelta(days=60)).isoformat()
        response = client.post(
            f"{API_V1}/blackout-dates",
            json={"date": blackout_date, "reason": "Test"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_blackout_date_success(self, client, admin_headers, test_resource):
        """Test deleting a blackout date."""
        # First create a blackout date
        blackout_date = (date.today() + timedelta(days=45)).isoformat()
        create_response = client.post(
            f"{API_V1}/resources/{test_resource.id}/blackout-dates",
            json={"date": blackout_date, "reason": "To Delete"},
            headers=admin_headers,
        )
        blackout_id = create_response.json()["id"]

        # Delete it
        response = client.delete(
            f"{API_V1}/blackout-dates/{blackout_id}",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
