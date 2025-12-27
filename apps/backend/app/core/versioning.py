"""API versioning utilities for the Resource Reserver backend.

This module provides comprehensive API versioning support including version parsing,
comparison, deprecation header middleware, and version routing helpers. It enables
graceful API evolution by supporting multiple versions simultaneously while providing
clear deprecation notices to API consumers.

Features:
    - APIVersion enum for type-safe version handling
    - Version parsing from URL paths and string representations
    - Configurable deprecation settings per version and per endpoint
    - Middleware for automatic deprecation header injection
    - Decorators for marking endpoints as deprecated
    - Version requirement dependencies for FastAPI routes

Example Usage:
    Basic version checking::

        from app.core.versioning import APIVersion, get_api_version_from_path

        version = get_api_version_from_path("/api/v1/resources")
        if version == APIVersion.V1:
            # Handle v1 logic
            pass

    Using the deprecated decorator::

        from app.core.versioning import deprecated

        @deprecated(
            since="1.0.0",
            sunset_date="2025-06-01",
            alternative="/api/v2/resources",
            message="Use the v2 API for improved functionality"
        )
        async def get_resources():
            return {"resources": []}

    Requiring specific API versions::

        from fastapi import Depends
        from app.core.versioning import require_version, APIVersion

        @app.get("/api/v2/feature")
        async def new_feature(
            version: APIVersion = Depends(require_version(APIVersion.V2))
        ):
            return {"feature": "new"}

Author: Sylvester-Francis
"""

import re
from enum import Enum
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class APIVersion(str, Enum):
    """Enumeration of supported API versions.

    This enum provides type-safe representation of API versions and includes
    utility methods for parsing version strings and numeric comparisons.
    Inherits from both str and Enum to allow direct string comparison and
    serialization.

    Attributes:
        V1: API version 1, the current stable version.
        V2: API version 2, currently in preview status.

    Example:
        >>> version = APIVersion.V1
        >>> version.value
        'v1'
        >>> version.numeric
        1
        >>> APIVersion.from_string("v2") == APIVersion.V2
        True
    """

    V1 = "v1"
    V2 = "v2"

    @classmethod
    def from_string(cls, version: str) -> "APIVersion":
        """Parse a version string to an APIVersion enum member.

        Accepts version strings in various formats (e.g., "v1", "V1", "1")
        and returns the corresponding APIVersion enum member.

        Args:
            version: The version string to parse. Can be in formats like
                "v1", "V1", "1", or " v1 " (with whitespace).

        Returns:
            The corresponding APIVersion enum member.

        Raises:
            ValueError: If the version string does not correspond to a
                supported API version.

        Example:
            >>> APIVersion.from_string("v1")
            <APIVersion.V1: 'v1'>
            >>> APIVersion.from_string("2")
            <APIVersion.V2: 'v2'>
        """
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
        """Get the numeric representation of the version.

        Extracts the integer version number from the version string,
        useful for version comparison operations.

        Returns:
            The numeric version as an integer (e.g., 1 for V1, 2 for V2).

        Example:
            >>> APIVersion.V1.numeric
            1
            >>> APIVersion.V2.numeric > APIVersion.V1.numeric
            True
        """
        return int(self.value[1:])


# Version deprecation configuration
# Maps each API version to its configuration including status, deprecation flag,
# sunset date, and optional message for API consumers.
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
# Maps (HTTP method, path regex pattern) tuples to deprecation information
# for individual endpoints that are being phased out.
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
    """Extract the API version from a request URL path.

    Parses the URL path to identify the API version segment following
    the /api/ prefix. Returns None if no valid version is found.

    Args:
        path: The URL path to parse (e.g., "/api/v1/resources").

    Returns:
        The APIVersion enum member if a valid version is found in the path,
        or None if the path doesn't contain a recognized version pattern.

    Example:
        >>> get_api_version_from_path("/api/v1/resources")
        <APIVersion.V1: 'v1'>
        >>> get_api_version_from_path("/health") is None
        True
    """
    match = re.match(r"^/api/(v\d+)/", path)
    if match:
        try:
            return APIVersion.from_string(match.group(1))
        except ValueError:
            return None
    return None


def check_endpoint_deprecation(method: str, path: str) -> dict | None:
    """Check if a specific endpoint is marked as deprecated.

    Searches the DEPRECATED_ENDPOINTS configuration to determine if
    the given HTTP method and path combination matches a deprecated
    endpoint pattern.

    Args:
        method: The HTTP method (e.g., "GET", "POST").
        path: The URL path to check (e.g., "/token").

    Returns:
        A dictionary containing deprecation information if the endpoint
        is deprecated, with keys:
            - deprecated_since: Version when deprecation started
            - sunset_date: When the endpoint will be removed
            - alternative: Suggested replacement endpoint
            - message: Human-readable deprecation message
        Returns None if the endpoint is not deprecated.

    Example:
        >>> info = check_endpoint_deprecation("GET", "/token")
        >>> info["alternative"]
        '/api/v1/token'
    """
    for (dep_method, pattern), info in DEPRECATED_ENDPOINTS.items():
        if method.upper() == dep_method and re.match(pattern, path):
            return info
    return None


class VersioningMiddleware(BaseHTTPMiddleware):
    """Middleware for adding versioning headers and deprecation warnings.

    This middleware intercepts all HTTP responses and adds appropriate
    versioning and deprecation headers based on the request path and
    configured deprecation settings. It helps API consumers understand
    which version they're using and be notified of any deprecations.

    Attributes:
        app: The ASGI application wrapped by this middleware.

    Headers Added:
        - X-API-Version: The API version being used
        - Deprecation: "true" if the version or endpoint is deprecated
        - Sunset: ISO date when deprecated functionality will be removed
        - X-Deprecation-Notice: Human-readable deprecation message
        - Link: Reference to successor/alternative endpoint

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.add_middleware(VersioningMiddleware)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and add versioning headers to the response.

        Intercepts the request, forwards it to the next handler, and then
        adds appropriate versioning and deprecation headers to the response
        based on the API version and endpoint deprecation status.

        Args:
            request: The incoming HTTP request object.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The HTTP response with added versioning headers.
        """
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

    Wraps an async endpoint function and stores deprecation metadata
    on the wrapper function. This metadata can be used by middleware
    or documentation generators to provide deprecation information.

    Args:
        since: The version when the endpoint was deprecated (e.g., "1.0.0").
        sunset_date: Optional ISO date when the endpoint will be removed
            (format: "YYYY-MM-DD").
        alternative: Optional URL path to the replacement endpoint.
        message: Optional custom deprecation message for API consumers.

    Returns:
        A decorator function that wraps the endpoint and attaches
        deprecation metadata.

    Note:
        The deprecation headers are best added via VersioningMiddleware
        or dependency injection, as this decorator stores metadata but
        doesn't directly modify responses.

    Example:
        >>> @deprecated(
        ...     since="1.0.0",
        ...     sunset_date="2025-06-01",
        ...     alternative="/api/v2/resources",
        ...     message="Please migrate to v2 API"
        ... )
        ... async def get_old_resources():
        ...     return {"resources": []}
        >>> get_old_resources._deprecated
        True
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
    """Create a FastAPI dependency that enforces API version requirements.

    Returns a dependency function that validates the API version extracted
    from the request path against the specified version constraints. Use
    this to restrict endpoints to specific API version ranges.

    Args:
        min_version: The minimum required API version. Requests with lower
            versions will receive a 400 error.
        max_version: Optional maximum allowed API version. Requests with
            higher versions will receive a 400 error. If None, no upper
            bound is enforced.

    Returns:
        A dependency function that can be used with FastAPI's Depends().
        The function validates the version and returns the APIVersion
        if valid.

    Raises:
        HTTPException: With status code 400 if:
            - No API version is specified in the request path
            - The version is below min_version
            - The version is above max_version (if specified)

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/api/v2/new-feature")
        ... async def new_feature(
        ...     version: APIVersion = Depends(require_version(APIVersion.V2))
        ... ):
        ...     return {"available": True}
        >>>
        >>> # Restrict to v1 only
        >>> @app.get("/api/v1/legacy")
        ... async def legacy_endpoint(
        ...     version: APIVersion = Depends(
        ...         require_version(APIVersion.V1, APIVersion.V1)
        ...     )
        ... ):
        ...     return {"legacy": True}
    """

    def version_checker(request: Request):
        """Validate the API version from the request path.

        Args:
            request: The FastAPI Request object.

        Returns:
            The validated APIVersion enum member.

        Raises:
            HTTPException: If version validation fails.
        """
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
    """Get comprehensive information about all API versions.

    Compiles version configuration and deprecated endpoint information
    into a single dictionary suitable for API responses or documentation.

    Returns:
        A dictionary containing:
            - current_version: The current stable API version string
            - versions: Nested dict with status info for each version
            - deprecated_endpoints: List of deprecated endpoint details

    Example:
        >>> info = get_version_info()
        >>> info["current_version"]
        'v1'
        >>> "v1" in info["versions"]
        True
        >>> info["versions"]["v1"]["status"]
        'current'
    """
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
