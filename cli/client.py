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

        response = self.session.get(f"{self.base_url}/resources/search", params=params)  # noqa: E501
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
        response = self.session.get(f"{self.base_url}/resources/availability/summary")  # noqa :E501
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

    def get_reservation_history(self, reservation_id: int) -> list[dict[str, Any]]:  # noqa : E501
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

    def set_resource_unavailable(
        self, resource_id: int, auto_reset_hours: int = 8
    ) -> dict[str, Any]:
        """Set resource as unavailable for maintenance/repair with auto-reset."""
        headers = config.get_auth_headers()
        response = self.session.put(
            f"{self.base_url}/resources/{resource_id}/status/unavailable",
            params={"auto_reset_hours": auto_reset_hours},
            headers=headers,
        )
        return self._handle_response(response)

    def reset_resource_to_available(self, resource_id: int) -> dict[str, Any]:
        """Reset resource to available status."""
        headers = config.get_auth_headers()
        response = self.session.put(
            f"{self.base_url}/resources/{resource_id}/status/available",
            headers=headers,
        )
        return self._handle_response(response)

    def get_resource_status(self, resource_id: int) -> dict[str, Any]:
        """Get detailed status information for a resource."""
        response = self.session.get(f"{self.base_url}/resources/{resource_id}/status")
        return self._handle_response(response)

    # ========================================================================
    # MFA Methods
    # ========================================================================

    def mfa_setup(self) -> dict[str, Any]:
        """Setup MFA for current user."""
        headers = config.get_auth_headers()
        response = self.session.post(f"{self.base_url}/auth/mfa/setup", headers=headers)
        return self._handle_response(response)

    def mfa_verify(self, code: str) -> dict[str, Any]:
        """Verify and enable MFA."""
        headers = config.get_auth_headers()
        response = self.session.post(
            f"{self.base_url}/auth/mfa/verify", json={"code": code}, headers=headers
        )
        return self._handle_response(response)

    def mfa_disable(self, password: str) -> dict[str, Any]:
        """Disable MFA."""
        headers = config.get_auth_headers()
        response = self.session.post(
            f"{self.base_url}/auth/mfa/disable",
            json={"password": password},
            headers=headers,
        )
        return self._handle_response(response)

    def mfa_regenerate_backup_codes(self) -> dict[str, Any]:
        """Regenerate MFA backup codes."""
        headers = config.get_auth_headers()
        response = self.session.post(
            f"{self.base_url}/auth/mfa/backup-codes", headers=headers
        )
        return self._handle_response(response)

    # ========================================================================
    # Role Methods
    # ========================================================================

    def list_roles(self) -> list[dict[str, Any]]:
        """List all available roles."""
        headers = config.get_auth_headers()
        response = self.session.get(f"{self.base_url}/roles/", headers=headers)
        return self._handle_response(response)

    def create_role(self, name: str, description: str | None = None) -> dict[str, Any]:
        """Create a new role (admin only)."""
        headers = config.get_auth_headers()
        response = self.session.post(
            f"{self.base_url}/roles/",
            json={"name": name, "description": description},
            headers=headers,
        )
        return self._handle_response(response)

    def get_my_roles(self) -> list[dict[str, Any]]:
        """Get current user's roles."""
        headers = config.get_auth_headers()
        response = self.session.get(f"{self.base_url}/roles/my-roles", headers=headers)
        return self._handle_response(response)

    def assign_role(self, user_id: int, role_name: str) -> dict[str, Any]:
        """Assign role to user (admin only)."""
        headers = config.get_auth_headers()
        response = self.session.post(
            f"{self.base_url}/roles/assign",
            json={"user_id": user_id, "role_name": role_name},
            headers=headers,
        )
        return self._handle_response(response)

    def remove_role(self, user_id: int, role_name: str) -> dict[str, Any]:
        """Remove role from user (admin only)."""
        headers = config.get_auth_headers()
        response = self.session.delete(
            f"{self.base_url}/roles/assign",
            json={"user_id": user_id, "role_name": role_name},
            headers=headers,
        )
        return self._handle_response(response)

    # ========================================================================
    # Setup Methods
    # ========================================================================

    def setup_status(self) -> dict[str, Any]:
        """Get setup completion status."""
        response = self.session.get(f"{self.base_url}/setup/status")
        return self._handle_response(response)

    def setup_initialize(
        self, payload: dict[str, Any], token: str | None = None
    ) -> dict[str, Any]:
        """Initialize setup with a new admin or promote existing user."""
        headers = {"X-Setup-Token": token} if token else None
        response = self.session.post(
            f"{self.base_url}/setup/initialize", json=payload, headers=headers
        )
        return self._handle_response(response)

    def setup_unlock(self, token: str) -> dict[str, Any]:
        """Reopen setup using a secure token."""
        headers = {"X-Setup-Token": token}
        response = self.session.post(f"{self.base_url}/setup/unlock", headers=headers)
        return self._handle_response(response)

    # ========================================================================
    # OAuth2 Methods
    # ========================================================================

    def create_oauth_client(
        self,
        client_name: str,
        redirect_uris: list[str],
        grant_types: str = "authorization_code",
        scope: str = "read write",
    ) -> dict[str, Any]:
        """Create OAuth2 client."""
        headers = config.get_auth_headers()
        response = self.session.post(
            f"{self.base_url}/oauth/clients",
            json={
                "client_name": client_name,
                "redirect_uris": redirect_uris,
                "grant_types": grant_types,
                "scope": scope,
            },
            headers=headers,
        )
        return self._handle_response(response)

    def list_oauth_clients(self) -> list[dict[str, Any]]:
        """List user's OAuth2 clients."""
        headers = config.get_auth_headers()
        response = self.session.get(f"{self.base_url}/oauth/clients", headers=headers)
        return self._handle_response(response)

    def delete_oauth_client(self, client_id: str) -> dict[str, Any]:
        """Delete OAuth2 client."""
        headers = config.get_auth_headers()
        response = self.session.delete(
            f"{self.base_url}/oauth/clients/{client_id}", headers=headers
        )
        return self._handle_response(response)
