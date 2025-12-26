"""API versioning utilities.

Provides:
- Version parsing and comparison
- Deprecation header middleware
- Version routing helpers

Author: Sylvester-Francis
"""

import re
from enum import Enum
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class APIVersion(str, Enum):
    """Supported API versions."""

    V1 = "v1"
    V2 = "v2"

    @classmethod
    def from_string(cls, version: str) -> "APIVersion":
        """Parse version string to APIVersion enum."""
        version = version.lower().strip()
        if version.startswith("v"):
            version = version[1:]

        if version == "1":
            return cls.V1
        elif version == "2":
            return cls.V2
        else:
            raise ValueError(f"Unsupported API version: {version}")

    @property
    def numeric(self) -> int:
        """Get numeric version number."""
        return int(self.value[1:])


# Version deprecation configuration
VERSION_CONFIG = {
    APIVersion.V1: {
        "status": "current",
        "deprecated": False,
        "sunset_date": None,
        "message": None,
    },
    APIVersion.V2: {
        "status": "preview",
        "deprecated": False,
        "sunset_date": None,
        "message": "API v2 is in preview. Some features may change.",
    },
}

# Deprecated endpoints configuration
DEPRECATED_ENDPOINTS = {
    # Format: (method, path_pattern): {deprecation_info}
    ("GET", r"^/token$"): {
        "deprecated_since": "1.0.0",
        "sunset_date": "2025-06-01",
        "alternative": "/api/v1/token",
        "message": "Use /api/v1/token instead",
    },
    ("POST", r"^/token$"): {
        "deprecated_since": "1.0.0",
        "sunset_date": "2025-06-01",
        "alternative": "/api/v1/token",
        "message": "Use /api/v1/token instead",
    },
    ("GET", r"^/resources$"): {
        "deprecated_since": "1.0.0",
        "sunset_date": "2025-06-01",
        "alternative": "/api/v1/resources/",
        "message": "Use /api/v1/resources/ instead",
    },
    ("GET", r"^/reservations$"): {
        "deprecated_since": "1.0.0",
        "sunset_date": "2025-06-01",
        "alternative": "/api/v1/reservations/",
        "message": "Use /api/v1/reservations/ instead",
    },
}


def get_api_version_from_path(path: str) -> APIVersion | None:
    """Extract API version from request path."""
    match = re.match(r"^/api/(v\d+)/", path)
    if match:
        try:
            return APIVersion.from_string(match.group(1))
        except ValueError:
            return None
    return None


def check_endpoint_deprecation(method: str, path: str) -> dict | None:
    """Check if an endpoint is deprecated."""
    for (dep_method, pattern), info in DEPRECATED_ENDPOINTS.items():
        if method.upper() == dep_method and re.match(pattern, path):
            return info
    return None


class VersioningMiddleware(BaseHTTPMiddleware):
    """Middleware for adding versioning headers and deprecation warnings."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add versioning headers."""
        response = await call_next(request)

        # Add API version header
        api_version = get_api_version_from_path(request.url.path)
        if api_version:
            response.headers["X-API-Version"] = api_version.value
            config = VERSION_CONFIG.get(api_version, {})

            # Add deprecation headers if version is deprecated
            if config.get("deprecated"):
                response.headers["Deprecation"] = "true"
                if config.get("sunset_date"):
                    response.headers["Sunset"] = config["sunset_date"]
                if config.get("message"):
                    response.headers["X-Deprecation-Notice"] = config["message"]

        # Check for deprecated endpoints
        deprecation_info = check_endpoint_deprecation(request.method, request.url.path)
        if deprecation_info:
            response.headers["Deprecation"] = "true"
            if deprecation_info.get("sunset_date"):
                response.headers["Sunset"] = deprecation_info["sunset_date"]
            if deprecation_info.get("alternative"):
                response.headers["Link"] = (
                    f'<{deprecation_info["alternative"]}>; rel="successor-version"'
                )
            if deprecation_info.get("message"):
                response.headers["X-Deprecation-Notice"] = deprecation_info["message"]

        return response


def deprecated(
    since: str,
    sunset_date: str | None = None,
    alternative: str | None = None,
    message: str | None = None,
):
    """Decorator to mark an endpoint as deprecated.

    Args:
        since: Version when the endpoint was deprecated
        sunset_date: Date when the endpoint will be removed (YYYY-MM-DD)
        alternative: Alternative endpoint to use
        message: Custom deprecation message
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get response from original function
            response = await func(*args, **kwargs)

            # Add deprecation headers (if response object is accessible)
            # Note: This works best with dependency injection
            return response

        # Store deprecation info on the function
        wrapper._deprecated = True
        wrapper._deprecated_since = since
        wrapper._sunset_date = sunset_date
        wrapper._alternative = alternative
        wrapper._deprecation_message = message

        return wrapper

    return decorator


def require_version(min_version: APIVersion, max_version: APIVersion | None = None):
    """Dependency to require specific API version range.

    Args:
        min_version: Minimum required API version
        max_version: Maximum allowed API version (optional)
    """

    def version_checker(request: Request):
        api_version = get_api_version_from_path(request.url.path)

        if api_version is None:
            raise HTTPException(
                status_code=400,
                detail="API version not specified. Use /api/v1/ or /api/v2/",
            )

        if api_version.numeric < min_version.numeric:
            raise HTTPException(
                status_code=400,
                detail=f"This endpoint requires API version {min_version.value} or higher",
            )

        if max_version and api_version.numeric > max_version.numeric:
            raise HTTPException(
                status_code=400,
                detail=f"This endpoint is not available in API version {api_version.value}",
            )

        return api_version

    return version_checker


def get_version_info() -> dict[str, Any]:
    """Get information about all API versions."""
    return {
        "current_version": APIVersion.V1.value,
        "versions": {
            version.value: {
                "status": config["status"],
                "deprecated": config["deprecated"],
                "sunset_date": config["sunset_date"],
                "message": config["message"],
            }
            for version, config in VERSION_CONFIG.items()
        },
        "deprecated_endpoints": [
            {
                "method": method,
                "path": pattern,
                "deprecated_since": info["deprecated_since"],
                "sunset_date": info.get("sunset_date"),
                "alternative": info.get("alternative"),
            }
            for (method, pattern), info in DEPRECATED_ENDPOINTS.items()
        ],
    }
