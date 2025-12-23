# cli/client.py - Updated with API v1, pagination, recurring, waitlist
"""API client for communicating with the reservation system."""

import logging
import re
from datetime import datetime
from typing import Any

import requests

from cli.config import config

logger = logging.getLogger(__name__)


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
                # Handle validation errors (list of errors)
                if isinstance(error_msg, list):
                    # Extract messages from validation errors
                    messages = []
                    for err in error_msg:
                        if isinstance(err, dict):
                            msg = err.get("msg", str(err))
                            loc = err.get("loc", [])
                            field = loc[-1] if loc else "field"
                            messages.append(f"{field}: {msg}")
                        else:
                            messages.append(str(err))
                    error_msg = "; ".join(messages)
            except Exception:
                error_msg = str(e)
            raise requests.exceptions.HTTPError(error_msg, response=response) from e

    def _get_auth_headers_with_refresh(self) -> dict:
        """Get auth headers, refreshing token if needed."""
        if config.is_token_expired():
            refresh_token = config.load_refresh_token()
            if refresh_token:
                try:
                    self.refresh_access_token(refresh_token)
                except requests.exceptions.RequestException as exc:
                    # If refresh fails, continue with existing token and let the next
                    # request return an auth error rather than silently swallowing it.
                    logger.warning(
                        "Access token refresh failed; continuing with existing token: %s",
                        exc,
                    )
        return config.get_auth_headers()

    # ========================================================================
    # Authentication Methods
    # ========================================================================

    def register(self, username: str, password: str) -> dict[str, Any]:
        """Register a new user."""
        response = self.session.post(
            f"{self.base_url}/register",
            json={"username": username, "password": password},
        )
        return self._handle_response(response)

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Login and return access token and refresh token."""
        response = self.session.post(
            f"{self.base_url}/token",
            data={"username": username, "password": password},
        )
        data = self._handle_response(response)
        return data

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh the access token using a refresh token.

        Args:
            refresh_token: The refresh token to use

        Returns:
            Dict containing new access_token and refresh_token
        """
        response = self.session.post(
            f"{self.base_url}/token/refresh",
            params={"refresh_token": refresh_token},
        )
        data = self._handle_response(response)

        # Save the new tokens
        config.save_token(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
        )

        return data

    def logout(self) -> dict[str, Any]:
        """Logout and revoke all refresh tokens."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.post(f"{self.base_url}/logout", headers=headers)
        result = self._handle_response(response)
        config.clear_token()
        return result

    def get_current_user(self) -> dict[str, Any]:
        """Get current user information."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.get(f"{self.base_url}/users/me", headers=headers)
        return self._handle_response(response)

    # ========================================================================
    # Resource Methods
    # ========================================================================

    def list_resources(
        self,
        cursor: str | None = None,
        limit: int = 20,
        sort_by: str = "name",
        sort_order: str = "asc",
        include_total: bool = False,
    ) -> dict[str, Any]:
        """Get all resources with pagination."""
        params = {
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "include_total": include_total,
        }
        if cursor:
            params["cursor"] = cursor

        response = self.session.get(f"{self.base_url}/resources", params=params)
        return self._handle_response(response)

    def search_resources(
        self,
        query: str = None,
        available_from: datetime = None,
        available_until: datetime = None,
        available_only: bool = True,
        status_filter: str | None = None,
        tags: list[str] | None = None,
        cursor: str | None = None,
        limit: int = 20,
        sort_by: str = "name",
        sort_order: str = "asc",
        include_total: bool = False,
    ) -> dict[str, Any]:
        """Search resources with optional time filtering and pagination."""
        params = {
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "include_total": include_total,
        }
        if query:
            params["q"] = query
        if available_from:
            params["available_from"] = available_from.isoformat()
        if available_until:
            params["available_until"] = available_until.isoformat()
        if status_filter:
            params["status"] = status_filter
        elif not available_only:
            params["available_only"] = "false"
        if tags:
            params["tags"] = tags
        if cursor:
            params["cursor"] = cursor

        response = self.session.get(f"{self.base_url}/resources/search", params=params)
        return self._handle_response(response)

    def create_resource(
        self, name: str, tags: list[str] = None, available: bool = True
    ) -> dict[str, Any]:
        """Create a new resource."""
        headers = self._get_auth_headers_with_refresh()
        data = {"name": name, "tags": tags or [], "available": available}
        response = self.session.post(
            f"{self.base_url}/resources", json=data, headers=headers
        )
        return self._handle_response(response)

    def upload_resources_csv(self, file_path: str) -> dict[str, Any]:
        """Upload resources from CSV file."""
        headers = self._get_auth_headers_with_refresh()

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
            params=params,
        )
        return self._handle_response(response)

    def update_resource_availability(
        self, resource_id: int, available: bool
    ) -> dict[str, Any]:
        """Update resource base availability (for maintenance, etc.)."""
        headers = self._get_auth_headers_with_refresh()
        data = {"available": available}
        response = self.session.put(
            f"{self.base_url}/resources/{resource_id}/availability",
            json=data,
            headers=headers,
        )
        return self._handle_response(response)

    def get_availability_summary(self) -> dict[str, Any]:
        """Get system-wide availability summary."""
        response = self.session.get(f"{self.base_url}/resources/availability/summary")
        return self._handle_response(response)

    def set_resource_unavailable(
        self, resource_id: int, auto_reset_hours: int = 8
    ) -> dict[str, Any]:
        """Set resource as unavailable for maintenance/repair with auto-reset."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.put(
            f"{self.base_url}/resources/{resource_id}/status/unavailable",
            params={"auto_reset_hours": auto_reset_hours},
            headers=headers,
        )
        return self._handle_response(response)

    def reset_resource_to_available(self, resource_id: int) -> dict[str, Any]:
        """Reset resource to available status."""
        headers = self._get_auth_headers_with_refresh()
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
    # Reservation Methods
    # ========================================================================

    def create_reservation(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> dict[str, Any]:
        """Create a new reservation."""
        headers = self._get_auth_headers_with_refresh()
        data = {
            "resource_id": resource_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
        response = self.session.post(
            f"{self.base_url}/reservations", json=data, headers=headers
        )
        return self._handle_response(response)

    def create_recurring_reservation(
        self,
        resource_id: int,
        start_time: datetime,
        end_time: datetime,
        frequency: str,
        interval: int = 1,
        days_of_week: list[int] | None = None,
        end_type: str = "after_count",
        end_date: datetime | None = None,
        occurrence_count: int = 5,
    ) -> list[dict[str, Any]]:
        """Create recurring reservations.

        Args:
            resource_id: ID of the resource to reserve
            start_time: Start time of the first reservation
            end_time: End time of the first reservation
            frequency: Recurrence frequency (daily, weekly, monthly)
            interval: Interval between occurrences (default: 1)
            days_of_week: List of days (0=Mon to 6=Sun) for weekly frequency
            end_type: How recurrence ends (never, on_date, after_count)
            end_date: End date for on_date end type
            occurrence_count: Number of occurrences for after_count end type

        Returns:
            List of created reservations
        """
        headers = self._get_auth_headers_with_refresh()

        recurrence = {
            "frequency": frequency,
            "interval": interval,
            "end_type": end_type,
        }

        if days_of_week:
            recurrence["days_of_week"] = days_of_week

        if end_type == "on_date" and end_date:
            recurrence["end_date"] = end_date.isoformat()
        elif end_type == "after_count":
            recurrence["occurrence_count"] = occurrence_count

        data = {
            "resource_id": resource_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "recurrence": recurrence,
        }

        response = self.session.post(
            f"{self.base_url}/reservations/recurring", json=data, headers=headers
        )
        return self._handle_response(response)

    def get_my_reservations(
        self,
        include_cancelled: bool = False,
        cursor: str | None = None,
        limit: int = 20,
        sort_by: str = "start_time",
        sort_order: str = "desc",
        include_total: bool = False,
    ) -> dict[str, Any]:
        """Get current user's reservations with pagination."""
        headers = self._get_auth_headers_with_refresh()
        params = {
            "include_cancelled": include_cancelled,
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "include_total": include_total,
        }
        if cursor:
            params["cursor"] = cursor

        response = self.session.get(
            f"{self.base_url}/reservations/my", headers=headers, params=params
        )
        return self._handle_response(response)

    def cancel_reservation(
        self, reservation_id: int, reason: str = None
    ) -> dict[str, Any]:
        """Cancel a reservation."""
        headers = self._get_auth_headers_with_refresh()
        data = {"reason": reason} if reason else {}
        response = self.session.post(
            f"{self.base_url}/reservations/{reservation_id}/cancel",
            json=data,
            headers=headers,
        )
        return self._handle_response(response)

    def get_reservation_history(self, reservation_id: int) -> list[dict[str, Any]]:
        """Get reservation history."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.get(
            f"{self.base_url}/reservations/{reservation_id}/history",
            headers=headers,
        )
        return self._handle_response(response)

    # ========================================================================
    # Waitlist Methods
    # ========================================================================

    def join_waitlist(
        self,
        resource_id: int,
        desired_start: datetime,
        desired_end: datetime,
        flexible_time: bool = False,
    ) -> dict[str, Any]:
        """Join the waitlist for a resource time slot.

        Args:
            resource_id: ID of the resource
            desired_start: Desired start time
            desired_end: Desired end time
            flexible_time: Whether to accept nearby time slots

        Returns:
            Waitlist entry details
        """
        headers = self._get_auth_headers_with_refresh()
        data = {
            "resource_id": resource_id,
            "desired_start": desired_start.isoformat(),
            "desired_end": desired_end.isoformat(),
            "flexible_time": flexible_time,
        }
        response = self.session.post(
            f"{self.base_url}/waitlist", json=data, headers=headers
        )
        return self._handle_response(response)

    def list_my_waitlist_entries(
        self,
        cursor: str | None = None,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_completed: bool = False,
        include_total: bool = False,
    ) -> dict[str, Any]:
        """List user's waitlist entries with pagination."""
        headers = self._get_auth_headers_with_refresh()
        params = {
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "include_completed": include_completed,
            "include_total": include_total,
        }
        if cursor:
            params["cursor"] = cursor

        response = self.session.get(
            f"{self.base_url}/waitlist", headers=headers, params=params
        )
        return self._handle_response(response)

    def get_waitlist_entry(self, waitlist_id: int) -> dict[str, Any]:
        """Get details of a specific waitlist entry."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.get(
            f"{self.base_url}/waitlist/{waitlist_id}", headers=headers
        )
        return self._handle_response(response)

    def leave_waitlist(self, waitlist_id: int) -> dict[str, Any]:
        """Leave the waitlist (cancel a waitlist entry)."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.delete(
            f"{self.base_url}/waitlist/{waitlist_id}", headers=headers
        )
        return self._handle_response(response)

    def accept_waitlist_offer(self, waitlist_id: int) -> dict[str, Any]:
        """Accept a waitlist offer and create a reservation."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.post(
            f"{self.base_url}/waitlist/{waitlist_id}/accept", headers=headers
        )
        return self._handle_response(response)

    def get_resource_waitlist(self, resource_id: int) -> list[dict[str, Any]]:
        """Get the waitlist for a specific resource."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.get(
            f"{self.base_url}/waitlist/resource/{resource_id}", headers=headers
        )
        return self._handle_response(response)

    # ========================================================================
    # Admin/System Methods
    # ========================================================================

    def manual_cleanup_expired(self) -> dict[str, Any]:
        """Manually trigger cleanup of expired reservations."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.post(
            f"{self.base_url}/admin/cleanup-expired", headers=headers
        )
        return self._handle_response(response)

    def health_check(self) -> dict[str, Any]:
        """Check API health status."""
        # Health endpoint is at root level, not versioned
        response = self.session.get(f"{config.base_url}/health")
        return self._handle_response(response)

    # ========================================================================
    # MFA Methods
    # ========================================================================

    def mfa_setup(self) -> dict[str, Any]:
        """Setup MFA for current user."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.post(f"{self.base_url}/auth/mfa/setup", headers=headers)
        return self._handle_response(response)

    def mfa_verify(self, code: str) -> dict[str, Any]:
        """Verify and enable MFA."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.post(
            f"{self.base_url}/auth/mfa/verify", json={"code": code}, headers=headers
        )
        return self._handle_response(response)

    def mfa_disable(self, password: str) -> dict[str, Any]:
        """Disable MFA."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.post(
            f"{self.base_url}/auth/mfa/disable",
            json={"password": password},
            headers=headers,
        )
        return self._handle_response(response)

    def mfa_regenerate_backup_codes(self) -> dict[str, Any]:
        """Regenerate MFA backup codes."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.post(
            f"{self.base_url}/auth/mfa/backup-codes", headers=headers
        )
        return self._handle_response(response)

    # ========================================================================
    # Role Methods
    # ========================================================================

    def list_roles(self) -> list[dict[str, Any]]:
        """List all available roles."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.get(f"{self.base_url}/roles/", headers=headers)
        return self._handle_response(response)

    def create_role(self, name: str, description: str | None = None) -> dict[str, Any]:
        """Create a new role (admin only)."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.post(
            f"{self.base_url}/roles/",
            json={"name": name, "description": description},
            headers=headers,
        )
        return self._handle_response(response)

    def get_my_roles(self) -> list[dict[str, Any]]:
        """Get current user's roles."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.get(f"{self.base_url}/roles/my-roles", headers=headers)
        return self._handle_response(response)

    def assign_role(self, user_id: int, role_name: str) -> dict[str, Any]:
        """Assign role to user (admin only)."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.post(
            f"{self.base_url}/roles/assign",
            json={"user_id": user_id, "role_name": role_name},
            headers=headers,
        )
        return self._handle_response(response)

    def remove_role(self, user_id: int, role_name: str) -> dict[str, Any]:
        """Remove role from user (admin only)."""
        headers = self._get_auth_headers_with_refresh()
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
        headers = self._get_auth_headers_with_refresh()
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
        headers = self._get_auth_headers_with_refresh()
        response = self.session.get(f"{self.base_url}/oauth/clients", headers=headers)
        return self._handle_response(response)

    def delete_oauth_client(self, client_id: str) -> dict[str, Any]:
        """Delete OAuth2 client."""
        headers = self._get_auth_headers_with_refresh()
        response = self.session.delete(
            f"{self.base_url}/oauth/clients/{client_id}", headers=headers
        )
        return self._handle_response(response)


# Helper functions for error message parsing
def parse_lockout_time(error_message: str) -> int | None:
    """Extract remaining lockout time from error message.

    Args:
        error_message: The error message from the API

    Returns:
        Remaining seconds if found, None otherwise
    """
    # Match patterns like "try again in X minutes" or "locked for X seconds"
    patterns = [
        r"(\d+)\s*minutes?",
        r"(\d+)\s*seconds?",
        r"try again in (\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, error_message.lower())
        if match:
            value = int(match.group(1))
            if "minute" in error_message.lower():
                return value * 60
            return value

    return None


def is_lockout_error(error_message: str) -> bool:
    """Check if the error message indicates account lockout."""
    lockout_indicators = [
        "locked",
        "too many",
        "attempts",
        "try again",
        "temporarily",
    ]
    error_lower = error_message.lower()
    return any(indicator in error_lower for indicator in lockout_indicators)


def is_password_policy_error(error_message: str) -> bool:
    """Check if the error message indicates password policy violation."""
    policy_indicators = [
        "password",
        "characters",
        "uppercase",
        "lowercase",
        "digit",
        "special",
        "must contain",
        "at least",
    ]
    error_lower = error_message.lower()
    return any(indicator in error_lower for indicator in policy_indicators)
