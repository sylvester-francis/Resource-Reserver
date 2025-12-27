"""Tests for the approval workflow endpoints.

Author: Sylvester-Francis
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


class TestApprovalEndpoints:
    """Tests for approval API endpoints."""

    def test_pending_approvals_requires_auth(self, client: TestClient):
        """Test that pending approvals endpoint requires authentication."""
        response = client.get("/api/v1/approvals/pending")
        assert response.status_code == 401

    def test_pending_approvals_empty_list(self, client: TestClient, auth_headers: dict):
        """Test getting pending approvals returns empty list when none exist."""
        response = client.get("/api/v1/approvals/pending", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "pending_approvals" in data
        assert "count" in data

    def test_my_requests_requires_auth(self, client: TestClient):
        """Test that my-requests endpoint requires authentication."""
        response = client.get("/api/v1/approvals/my-requests")
        assert response.status_code == 401

    def test_my_requests_empty_list(self, client: TestClient, auth_headers: dict):
        """Test getting my requests returns empty list when none exist."""
        response = client.get("/api/v1/approvals/my-requests", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "my_requests" in data
        assert "count" in data

    def test_get_approval_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent approval returns 404."""
        response = client.get("/api/v1/approvals/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_respond_to_approval_not_found(
        self, client: TestClient, auth_headers: dict
    ):
        """Test responding to non-existent approval returns 400."""
        response = client.post(
            "/api/v1/approvals/99999/respond",
            json={"action": "approve"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_cancel_approval_not_found(self, client: TestClient, auth_headers: dict):
        """Test cancelling non-existent approval returns 400."""
        response = client.delete("/api/v1/approvals/99999", headers=auth_headers)
        assert response.status_code == 400


class TestResourceApprovalSettings:
    """Tests for resource approval settings."""

    def test_get_settings_requires_auth(self, client: TestClient):
        """Test that getting resource settings requires authentication."""
        response = client.get("/api/v1/approvals/resources/1/settings")
        assert response.status_code == 401

    def test_get_settings_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting settings for non-existent resource returns 404."""
        response = client.get(
            "/api/v1/approvals/resources/99999/settings", headers=auth_headers
        )
        assert response.status_code == 404

    def test_update_settings_requires_auth(self, client: TestClient):
        """Test that updating resource settings requires authentication."""
        response = client.put(
            "/api/v1/approvals/resources/1/settings",
            json={"requires_approval": True},
        )
        assert response.status_code == 401

    def test_update_settings_not_found(self, client: TestClient, auth_headers: dict):
        """Test updating settings for non-existent resource returns 400."""
        response = client.put(
            "/api/v1/approvals/resources/99999/settings",
            json={"requires_approval": True},
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestReservationWithApproval:
    """Tests for creating reservations with approval workflow."""

    def test_create_reservation_requires_auth(self, client: TestClient):
        """Test that creating reservation via approval endpoint requires auth."""
        response = client.post(
            "/api/v1/approvals/reservations",
            json={
                "resource_id": 1,
                "start_time": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            },
        )
        assert response.status_code == 401

    def test_create_reservation_resource_not_found(
        self, client: TestClient, auth_headers: dict
    ):
        """Test creating reservation for non-existent resource returns 404."""
        response = client.post(
            "/api/v1/approvals/reservations",
            json={
                "resource_id": 99999,
                "start_time": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            },
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_invalid_action(self, client: TestClient, auth_headers: dict):
        """Test that invalid action in respond endpoint fails validation."""
        response = client.post(
            "/api/v1/approvals/99999/respond",
            json={"action": "invalid_action"},
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error


class TestApprovalWorkflow:
    """Integration tests for the complete approval workflow."""

    def test_full_approval_workflow(
        self, client: TestClient, auth_headers: dict, test_db
    ):
        """Test the complete approval workflow from request to approval."""
        # First create a resource
        resource_response = client.post(
            "/api/v1/resources/",
            json={"name": "approval-test-resource"},
            headers=auth_headers,
        )
        assert resource_response.status_code in [200, 201]
        resource_id = resource_response.json()["id"]

        # Get the current user ID from a token introspection or similar
        me_response = client.get("/api/v1/users/me", headers=auth_headers)
        assert me_response.status_code == 200
        user_id = me_response.json()["id"]

        # Enable approval requirement for the resource with current user as approver
        settings_response = client.put(
            f"/api/v1/approvals/resources/{resource_id}/settings",
            json={"requires_approval": True, "default_approver_id": user_id},
            headers=auth_headers,
        )
        assert settings_response.status_code == 200
        assert settings_response.json()["requires_approval"] is True

        # Verify settings were saved
        get_settings_response = client.get(
            f"/api/v1/approvals/resources/{resource_id}/settings",
            headers=auth_headers,
        )
        assert get_settings_response.status_code == 200
        assert get_settings_response.json()["requires_approval"] is True
        assert get_settings_response.json()["default_approver_id"] == user_id

        # Create a reservation (should trigger approval workflow)
        start_time = datetime.now(UTC) + timedelta(hours=2)
        end_time = datetime.now(UTC) + timedelta(hours=3)
        reservation_response = client.post(
            "/api/v1/approvals/reservations",
            json={
                "resource_id": resource_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "request_message": "Please approve my reservation",
            },
            headers=auth_headers,
        )
        assert reservation_response.status_code == 200
        data = reservation_response.json()
        assert data["requires_approval"] is True
        assert data["status"] == "pending_approval"
        assert "approval_id" in data

        approval_id = data["approval_id"]

        # Check pending approvals (as approver)
        pending_response = client.get("/api/v1/approvals/pending", headers=auth_headers)
        assert pending_response.status_code == 200
        # Note: Since we're both requester and approver, we should see it
        pending_data = pending_response.json()
        assert pending_data["count"] >= 1

        # Get the approval request details
        approval_response = client.get(
            f"/api/v1/approvals/{approval_id}", headers=auth_headers
        )
        assert approval_response.status_code == 200
        approval_data = approval_response.json()
        assert approval_data["status"] == "pending"
        assert approval_data["request_message"] == "Please approve my reservation"

        # Approve the request
        respond_response = client.post(
            f"/api/v1/approvals/{approval_id}/respond",
            json={"action": "approve", "response_message": "Approved!"},
            headers=auth_headers,
        )
        assert respond_response.status_code == 200
        assert respond_response.json()["status"] == "approved"

        # Verify the approval is no longer pending
        pending_after = client.get("/api/v1/approvals/pending", headers=auth_headers)
        # The count should be less now
        assert pending_after.status_code == 200

    def test_rejection_workflow(self, client: TestClient, auth_headers: dict, test_db):
        """Test rejecting a reservation request."""
        # Create a resource
        resource_response = client.post(
            "/api/v1/resources/",
            json={"name": "rejection-test-resource"},
            headers=auth_headers,
        )
        assert resource_response.status_code in [200, 201]
        resource_id = resource_response.json()["id"]

        # Get the current user ID
        me_response = client.get("/api/v1/users/me", headers=auth_headers)
        assert me_response.status_code == 200
        user_id = me_response.json()["id"]

        # Enable approval requirement
        client.put(
            f"/api/v1/approvals/resources/{resource_id}/settings",
            json={"requires_approval": True, "default_approver_id": user_id},
            headers=auth_headers,
        )

        # Create a reservation
        start_time = datetime.now(UTC) + timedelta(hours=4)
        end_time = datetime.now(UTC) + timedelta(hours=5)
        reservation_response = client.post(
            "/api/v1/approvals/reservations",
            json={
                "resource_id": resource_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=auth_headers,
        )
        assert reservation_response.status_code == 200
        approval_id = reservation_response.json()["approval_id"]

        # Reject the request
        respond_response = client.post(
            f"/api/v1/approvals/{approval_id}/respond",
            json={"action": "reject", "response_message": "Not available"},
            headers=auth_headers,
        )
        assert respond_response.status_code == 200
        assert respond_response.json()["status"] == "rejected"

    def test_no_approval_required(
        self, client: TestClient, auth_headers: dict, test_db
    ):
        """Test creating reservation when no approval is required."""
        # Create a resource without approval requirement
        resource_response = client.post(
            "/api/v1/resources/",
            json={"name": "no-approval-resource"},
            headers=auth_headers,
        )
        assert resource_response.status_code in [200, 201]
        resource_id = resource_response.json()["id"]

        # Create a reservation (should succeed immediately)
        start_time = datetime.now(UTC) + timedelta(hours=6)
        end_time = datetime.now(UTC) + timedelta(hours=7)
        reservation_response = client.post(
            "/api/v1/approvals/reservations",
            json={
                "resource_id": resource_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=auth_headers,
        )
        assert reservation_response.status_code == 200
        data = reservation_response.json()
        assert data["requires_approval"] is False
        assert data["status"] == "active"
