# cli/client.py - Updated with new endpoints
"""API client for communicating with the reservation system."""

from datetime import datetime
from typing import Any

import requests

from cli.config import config


class APIClient:
    """Client for interacting with the reservation system API."""

    def __init__(self):
        self.base_url = config.api_url
        self.session = requests.Session()
        # Set default timeout for all requests
        self.session.timeout = 30

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Handle API response with proper error handling."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Try to extract error message from response
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", str(e))
            except Exception:
                error_msg = str(e)
            raise requests.exceptions.HTTPError(error_msg, response=response) from e

    def register(self, username: str, password: str) -> dict[str, Any]:
        """Register a new user."""
        response = self.session.post(
            f"{self.base_url}/register",
            json={"username": username, "password": password},
        )
        return self._handle_response(response)

    def login(self, username: str, password: str) -> str:
        """Login and return access token."""
        response = self.session.post(
            f"{self.base_url}/token",
            data={"username": username, "password": password},
        )
        data = self._handle_response(response)
        return data["access_token"]

    def list_resources(self) -> list[dict[str, Any]]:
        """Get all resources."""
        response = self.session.get(f"{self.base_url}/resources")
        return self._handle_response(response)

    def search_resources(
        self,
        query: str = None,
        available_from: datetime = None,
        available_until: datetime = None,
        available_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Search resources with optional time filtering."""
        params = {}
        if query:
            params["q"] = query
        if available_from:
            params["available_from"] = available_from.isoformat()
        if available_until:
            params["available_until"] = available_until.isoformat()
        if not available_only:
            params["available_only"] = "false"

        response = self.session.get(
            f"{self.base_url}/resources/search", params=params
        )  # noqa: E501
        return self._handle_response(response)

    def create_resource(
        self, name: str, tags: list[str] = None, available: bool = True
    ) -> dict[str, Any]:
        """Create a new resource."""
        headers = config.get_auth_headers()
        data = {"name": name, "tags": tags or [], "available": available}
        response = self.session.post(
            f"{self.base_url}/resources", json=data, headers=headers
        )
        return self._handle_response(response)

    def upload_resources_csv(self, file_path: str) -> dict[str, Any]:
        """Upload resources from CSV file."""
        headers = config.get_auth_headers()

        with open(file_path, "rb") as f:
            files = {"file": (file_path, f, "text/csv")}
            response = self.session.post(
                f"{self.base_url}/resources/upload",
                files=files,
                headers=headers,
            )

        return self._handle_response(response)

    def get_resource_availability(
        self, resource_id: int, days_ahead: int = 7
    ) -> dict[str, Any]:
        """Get detailed availability schedule for a resource."""
        params = {"days_ahead": days_ahead}
        response = self.session.get(
            f"{self.base_url}/resources/{resource_id}/availability",
            params=params,  # noqa : E501
        )
        return self._handle_response(response)

    def update_resource_availability(
        self, resource_id: int, available: bool
    ) -> dict[str, Any]:
        """Update resource base availability (for maintenance, etc.)."""
        headers = config.get_auth_headers()
        data = {"available": available}
        response = self.session.put(
            f"{self.base_url}/resources/{resource_id}/availability",
            json=data,
            headers=headers,
        )
        return self._handle_response(response)

    def get_availability_summary(self) -> dict[str, Any]:
        """Get system-wide availability summary."""
        response = self.session.get(
            f"{self.base_url}/resources/availability/summary"
        )  # noqa :E501
        return self._handle_response(response)

    def create_reservation(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> dict[str, Any]:
        """Create a new reservation."""
        headers = config.get_auth_headers()
        data = {
            "resource_id": resource_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
        response = self.session.post(
            f"{self.base_url}/reservations", json=data, headers=headers
        )
        return self._handle_response(response)

    def get_my_reservations(
        self, include_cancelled: bool = False
    ) -> list[dict[str, Any]]:
        """Get current user's reservations."""
        headers = config.get_auth_headers()
        params = {"include_cancelled": include_cancelled}
        response = self.session.get(
            f"{self.base_url}/reservations/my", headers=headers, params=params
        )
        return self._handle_response(response)

    def cancel_reservation(
        self, reservation_id: int, reason: str = None
    ) -> dict[str, Any]:
        """Cancel a reservation."""
        headers = config.get_auth_headers()
        data = {"reason": reason} if reason else {}
        response = self.session.post(
            f"{self.base_url}/reservations/{reservation_id}/cancel",
            json=data,
            headers=headers,
        )
        return self._handle_response(response)

    def get_reservation_history(
        self, reservation_id: int
    ) -> list[dict[str, Any]]:  # noqa : E501
        """Get reservation history."""
        headers = config.get_auth_headers()
        response = self.session.get(
            f"{self.base_url}/reservations/{reservation_id}/history",
            headers=headers,
        )
        return self._handle_response(response)

    def manual_cleanup_expired(self) -> dict[str, Any]:
        """Manually trigger cleanup of expired reservations."""
        headers = config.get_auth_headers()
        response = self.session.post(
            f"{self.base_url}/admin/cleanup-expired", headers=headers
        )
        return self._handle_response(response)

    def health_check(self) -> dict[str, Any]:
        """Check API health status."""
        response = self.session.get(f"{self.base_url}/health")
        return self._handle_response(response)
