"""Resource Reservation System API - Main Application Module.

This module serves as the entry point for the Resource Reservation System API,
providing a comprehensive RESTful interface for managing resources, reservations,
users, and related functionality. The API is built on FastAPI with rate limiting,
WebSocket support, and background task processing.

Features:
    - Resource Management: Create, search, and manage bookable resources with tags
    - Reservation System: Book resources with conflict detection and recurring support
    - User Authentication: JWT-based auth with MFA, OAuth2, and role-based access
    - Real-time Updates: WebSocket connections for live reservation notifications
    - Background Tasks: Automatic cleanup of expired reservations and email reminders
    - Rate Limiting: Configurable rate limits for API protection
    - Caching: Redis-based caching for improved performance
    - Health Monitoring: Kubernetes-compatible health, readiness, and liveness probes

Example Usage:
    To run the application with uvicorn::

        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

    To access the API documentation::

        http://localhost:8000/docs  # Swagger UI
        http://localhost:8000/redoc  # ReDoc

Author:
    Resource Reserver Development Team

Version:
    2.1.0
"""

# app/main.py - API v1 with rate limiting

import asyncio
import csv
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from io import StringIO
from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    WebSocket,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app import models, rbac, schemas, setup
from app.auth import (
    authenticate_user_with_lockout,
    create_access_token,
    create_refresh_token,
    get_current_user,
    revoke_user_tokens,
    rotate_refresh_token,
    verify_refresh_token,
)
from app.auth_routes import auth_router, mfa_router, oauth_router, roles_router
from app.config import get_settings
from app.core.cache import cache_manager
from app.core.metrics import check_liveness, check_readiness, metrics
from app.core.rate_limiter import RateLimitMiddleware
from app.core.versioning import VersioningMiddleware, get_version_info
from app.database import SessionLocal, engine, ensure_sqlite_schema, get_db
from app.rbac import is_admin
from app.routers.analytics import router as analytics_router
from app.routers.approvals import router as approvals_router
from app.routers.audit import router as audit_router
from app.routers.bulk import router as bulk_router
from app.routers.business_hours import router as business_hours_router
from app.routers.calendar import router as calendar_router
from app.routers.labels import router as labels_router
from app.routers.notifications import router as notifications_router
from app.routers.quotas import router as quotas_router
from app.routers.resource_groups import router as resource_groups_router
from app.routers.search import router as search_router
from app.routers.waitlist import router as waitlist_router
from app.routers.webhooks import router as webhooks_router
from app.services import (
    ReservationService,
    ResourceService,
    UserService,
)
from app.setup_routes import setup_router
from app.websocket import manager as ws_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Global variable to control the cleanup task
cleanup_task = None


def get_rate_limit_key(request: Request) -> str:
    """Generate a rate limit key based on user authentication or IP address.

    This function determines the appropriate rate limiting key for a request.
    Authenticated users are identified by a hash of their token, while
    anonymous users are identified by their IP address.

    Args:
        request: The incoming FastAPI request object containing headers
            and client information.

    Returns:
        A string key for rate limiting. For authenticated users, returns
        'user:{token_hash}'. For anonymous users, returns the client IP address.

    Example:
        >>> key = get_rate_limit_key(request)
        >>> # Returns 'user:12345678' for authenticated users
        >>> # Returns '192.168.1.1' for anonymous users
    """
    # Try to get user from token if present
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # Use token hash as key for authenticated users
        token = auth_header.split(" ")[1]
        return f"user:{hash(token)}"
    # Fall back to IP for anonymous users
    return get_remote_address(request)


# Initialize rate limiter
limiter = Limiter(
    key_func=get_rate_limit_key,
    enabled=settings.rate_limit_enabled,
    default_limits=[settings.rate_limit_anonymous],
)


def ensure_timezone_aware(dt):
    """Ensure a datetime object is timezone-aware.

    Converts naive datetime objects to UTC timezone-aware objects.
    If the datetime already has timezone info, it is returned unchanged.

    Args:
        dt: A datetime object that may or may not have timezone information,
            or None.

    Returns:
        A timezone-aware datetime object with UTC timezone if the input was
        naive, the original datetime if it was already timezone-aware, or
        None if the input was None.

    Example:
        >>> from datetime import datetime
        >>> naive_dt = datetime(2024, 1, 15, 10, 30)
        >>> aware_dt = ensure_timezone_aware(naive_dt)
        >>> aware_dt.tzinfo is not None
        True
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def utcnow():
    """Get the current UTC datetime as a timezone-aware object.

    Returns:
        A timezone-aware datetime object representing the current time in UTC.

    Example:
        >>> now = utcnow()
        >>> now.tzinfo
        datetime.timezone.utc
    """
    return datetime.now(UTC)


def get_request_timezone(request: Request) -> ZoneInfo:
    """Extract the timezone from request headers.

    Reads the X-Timezone header from the request to determine the client's
    preferred timezone. Falls back to UTC if the header is missing or contains
    an invalid timezone identifier.

    Args:
        request: The incoming FastAPI request object.

    Returns:
        A ZoneInfo object representing the requested timezone, or UTC if
        the timezone header is missing or invalid.

    Example:
        >>> # Request with header X-Timezone: America/New_York
        >>> tz = get_request_timezone(request)
        >>> str(tz)
        'America/New_York'
    """
    tz_header = request.headers.get("X-Timezone")
    if tz_header:
        try:
            return ZoneInfo(tz_header)
        except Exception:
            # Invalid timezone; fall back to UTC
            return ZoneInfo("UTC")
    return ZoneInfo("UTC")


def convert_reservation_timezone(reservation, tz: ZoneInfo):
    """Convert datetime fields on a reservation to a specified timezone.

    Transforms all datetime fields on a reservation object to the provided
    timezone. This is useful for presenting reservation times in the user's
    local timezone.

    Args:
        reservation: A reservation object with datetime attributes including
            start_time, end_time, created_at, and optionally cancelled_at.
        tz: A ZoneInfo object representing the target timezone.

    Returns:
        The same reservation object with datetime fields converted to the
        specified timezone.

    Note:
        This function modifies the reservation object in place and also
        returns it for convenience in chaining operations.

    Example:
        >>> from zoneinfo import ZoneInfo
        >>> tz = ZoneInfo("America/Los_Angeles")
        >>> reservation = convert_reservation_timezone(reservation, tz)
    """
    if hasattr(reservation, "start_time") and reservation.start_time:
        reservation.start_time = reservation.start_time.astimezone(tz)
    if hasattr(reservation, "end_time") and reservation.end_time:
        reservation.end_time = reservation.end_time.astimezone(tz)
    if hasattr(reservation, "created_at") and reservation.created_at:
        reservation.created_at = reservation.created_at.astimezone(tz)
    if hasattr(reservation, "cancelled_at") and reservation.cancelled_at:
        reservation.cancelled_at = reservation.cancelled_at.astimezone(tz)
    return reservation


# =============================================================================
# WebSocket endpoint
# =============================================================================


async def cleanup_expired_reservations():
    """Background task to clean up expired reservations and auto-reset resources.

    This coroutine runs continuously as a background task, performing two
    main cleanup operations every 5 minutes:

    1. Expired Reservations: Finds active reservations whose end_time has passed
       and marks them as 'expired', creating history entries for audit purposes.

    2. Unavailable Resources: Checks resources marked as 'unavailable' and
       automatically resets them to 'available' if their auto-reset timeout
       has elapsed.

    The task handles database errors gracefully and continues running even
    if individual cleanup operations fail.

    Raises:
        asyncio.CancelledError: When the task is cancelled during application
            shutdown. This is caught and handled by the lifespan manager.

    Note:
        This task is started automatically when the FastAPI application starts
        and is cancelled during shutdown. It uses its own database session
        to avoid conflicts with request-scoped sessions.
    """
    from app.database import SessionLocal

    logger.info("Starting cleanup task for expired reservations and resource status")

    while True:
        try:
            db = SessionLocal()
            now = utcnow()

            # Find expired reservations that are still marked as active
            expired_reservations = (
                db.query(models.Reservation)
                .filter(
                    models.Reservation.status == "active",
                    models.Reservation.end_time < now,
                )
                .all()
            )

            # Process expired reservations
            if expired_reservations:
                logger.info(
                    f"Cleaning up {len(expired_reservations)} expired reservations"
                )

                for reservation in expired_reservations:
                    history = models.ReservationHistory(
                        reservation_id=reservation.id,
                        action="expired",
                        user_id=reservation.user_id,
                        details=f"Reservation automatically expired at {now.isoformat()}",
                    )
                    db.add(history)
                    reservation.status = "expired"

                    logger.info(
                        f"Expired reservation {reservation.id} for resource "
                        f"{reservation.resource_id}"
                    )

                db.commit()
                logger.info("Expired reservations cleanup completed")
            else:
                logger.debug("No expired reservations found")

            # Auto-reset unavailable resources that have exceeded their timeout
            unavailable_resources = (
                db.query(models.Resource)
                .filter(
                    models.Resource.status == "unavailable",
                    models.Resource.unavailable_since.isnot(None),
                )
                .all()
            )

            reset_count = 0
            for resource in unavailable_resources:
                if resource.should_auto_reset():
                    logger.info(
                        f"Auto-resetting resource {resource.id} ({resource.name}) "
                        f"after {resource.auto_reset_hours} hours"
                    )
                    resource.set_available()
                    reset_count += 1

            if reset_count > 0:
                db.commit()
                logger.info(
                    f"Auto-reset {reset_count} unavailable resources to available"
                )
            else:
                logger.debug("No resources ready for auto-reset")

            db.close()

        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            try:
                db.close()
            except Exception:  # nosec B110 - intentionally ignoring close errors
                pass

        await asyncio.sleep(300)


async def send_reservation_reminders():
    """Background task to send email reminders for upcoming reservations.

    This coroutine runs continuously as a background task, checking every
    15 minutes for reservations that need reminder emails. It respects
    user preferences for notification settings and reminder timing.

    The task performs the following:
    1. Checks if email service is enabled in settings
    2. Queries for active reservations that haven't had reminders sent
    3. Filters to users who have email notifications enabled
    4. Sends reminders based on each user's reminder_hours preference
    5. Marks reservations as having reminders sent to prevent duplicates

    Raises:
        asyncio.CancelledError: When the task is cancelled during application
            shutdown.

    Note:
        This task requires the email service to be properly configured.
        If email is disabled, the task will skip processing but continue
        running to check periodically.
    """
    from app.database import SessionLocal
    from app.email_service import email_service

    logger.info("Starting email reminder task")

    while True:
        try:
            if not settings.email_enabled:
                logger.debug("Email service disabled, skipping reminders")
                await asyncio.sleep(900)  # Check every 15 minutes
                continue

            db = SessionLocal()
            now = utcnow()

            # Find reservations that need reminders
            # Get active reservations starting within the next 24 hours that haven't had reminders sent
            upcoming_reservations = (
                db.query(models.Reservation)
                .join(models.User)
                .filter(
                    models.Reservation.status == "active",
                    models.Reservation.reminder_sent == False,  # noqa: E712
                    models.Reservation.start_time > now,
                    models.User.email_notifications == True,  # noqa: E712
                    models.User.email.isnot(None),
                )
                .all()
            )

            reminders_sent = 0
            for reservation in upcoming_reservations:
                user = reservation.user
                if not user or not user.email:
                    continue

                # Calculate hours until reservation starts
                time_until = reservation.start_time - now
                hours_until = time_until.total_seconds() / 3600

                # Send reminder if within user's reminder window
                if hours_until <= user.reminder_hours:
                    try:
                        resource = reservation.resource
                        resource_name = (
                            resource.name
                            if resource
                            else f"Resource #{reservation.resource_id}"
                        )

                        success = await email_service.send_reservation_reminder(
                            to=user.email,
                            username=user.username,
                            resource_name=resource_name,
                            start_time=reservation.start_time,
                            hours_until=int(hours_until) + 1,  # Round up
                            reservation_id=reservation.id,
                        )

                        if success:
                            reservation.reminder_sent = True
                            reminders_sent += 1
                            logger.info(
                                f"Sent reminder for reservation {reservation.id} to {user.email}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Failed to send reminder for reservation {reservation.id}: {e}"
                        )

            if reminders_sent > 0:
                db.commit()
                logger.info(f"Sent {reminders_sent} reservation reminders")
            else:
                logger.debug("No reminders to send")

            db.close()

        except Exception as e:
            logger.error(f"Error in reminder task: {e}")
            try:
                db.close()
            except Exception:  # nosec B110 - intentionally ignoring close errors
                pass

        await asyncio.sleep(900)  # Check every 15 minutes


# Global variable to control the reminder task
reminder_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the FastAPI application lifecycle.

    This async context manager handles application startup and shutdown
    operations including:

    Startup:
        - Creating database tables if they don't exist
        - Initializing default RBAC roles
        - Ensuring setup state is configured
        - Connecting to Redis cache (if enabled)
        - Starting background tasks for cleanup and reminders

    Shutdown:
        - Cancelling background tasks gracefully
        - Disconnecting from Redis cache
        - Logging shutdown completion

    Args:
        app: The FastAPI application instance.

    Yields:
        Control is yielded to the application after startup completes.
        Shutdown operations run after the yield when the app is stopping.

    Example:
        This function is used as the lifespan parameter when creating
        the FastAPI app::

            app = FastAPI(lifespan=lifespan)
    """
    global cleanup_task, reminder_task

    logger.info("Starting FastAPI application...")

    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

    try:
        ensure_sqlite_schema()
        logger.info("SQLite schema verified")
    except Exception as e:
        logger.warning(f"SQLite schema check failed: {e}")

    try:
        db = SessionLocal()
        rbac.create_default_roles(db)
        setup.ensure_setup_state(db)
        db.close()
        logger.info("Default roles verified/created")
    except Exception as e:
        logger.error(f"Error creating default roles: {e}")

    # Initialize Redis cache
    try:
        cache_connected = await cache_manager.connect()
        if cache_connected:
            logger.info("Redis cache connected")
        else:
            logger.info("Redis cache disabled or unavailable - running without cache")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis cache: {e}")

    cleanup_task = asyncio.create_task(cleanup_expired_reservations())
    logger.info("Background cleanup task started")

    # Start email reminder task
    reminder_task = asyncio.create_task(send_reservation_reminders())
    logger.info("Background email reminder task started")

    yield

    logger.info("Shutting down FastAPI application...")

    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            logger.info("Background cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error during cleanup task shutdown: {e}")

    if reminder_task:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            logger.info("Background reminder task cancelled")
        except Exception as e:
            logger.error(f"Error during reminder task shutdown: {e}")

    # Disconnect Redis cache
    try:
        await cache_manager.disconnect()
        logger.info("Redis cache disconnected")
    except Exception as e:
        logger.warning(f"Error disconnecting Redis cache: {e}")

    logger.info("Application shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Resource Reservation System",
    description="""
A comprehensive resource booking system with intelligent scheduling and real-time updates.

## Features

- **Resource Management**: Create, organize, and track resources with tags and availability status
- **Reservation System**: Book resources with automatic conflict detection and recurring reservations
- **Waitlist**: Join waitlists for busy resources and receive offers when slots become available
- **Real-time Updates**: WebSocket-based notifications for reservation changes and availability alerts
- **Notifications**: In-app notification center for reservation confirmations, reminders, and system announcements
- **Security**: JWT authentication, MFA support, role-based access control, and OAuth2 authorization server

## Authentication

All protected endpoints require a Bearer token in the Authorization header.
Use the `/api/v1/token` endpoint to obtain access and refresh tokens.
""",
    version="2.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User registration, login, token management, and logout",
        },
        {
            "name": "Resources",
            "description": "Resource management, availability tracking, and status updates",
        },
        {
            "name": "Reservations",
            "description": "Create, manage, and cancel reservations including recurring bookings",
        },
        {
            "name": "Waitlist",
            "description": "Join waitlists for resources and accept slot offers",
        },
        {
            "name": "Notifications",
            "description": "View and manage user notifications",
        },
        {
            "name": "Admin",
            "description": "Administrative operations and system maintenance",
        },
    ],
)

# Add rate limiter to app state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add versioning middleware for deprecation headers
app.add_middleware(VersioningMiddleware)

# Add enhanced rate limiting middleware with quota tracking
app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics for monitoring.

    Tracks the duration and outcome of each HTTP request, recording
    metrics that can be exported to Prometheus or other monitoring systems.

    Args:
        request: The incoming HTTP request.
        call_next: The next middleware or route handler in the chain.

    Returns:
        The response from the downstream handler with metrics recorded.
    """
    import time

    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    metrics.record_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=duration,
    )

    return response


# =============================================================================
# WebSocket endpoint
# =============================================================================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """Handle WebSocket connections for real-time updates.

    Authenticates WebSocket connections using a JWT token passed as a query
    parameter, then maintains the connection for real-time event streaming.

    Args:
        websocket: The WebSocket connection instance.
        db: Database session dependency for user lookup.

    Raises:
        WebSocketDisconnect: When the client disconnects or the connection
            is closed due to authentication failure.

    Note:
        The token must be passed as a query parameter (e.g., /ws?token=xxx).
        Invalid or missing tokens result in immediate connection closure
        with policy violation code (1008).

    Example:
        Client connection URL::

            ws://localhost:8000/ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify token and extract user
    from jose import JWTError, jwt  # Local import to avoid cycles

    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise JWTError("Missing subject")
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Lookup user ID
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        await ws_manager.connect(websocket, user.id)
        while True:
            await websocket.receive_text()  # Keep alive; ignore messages for now
    except Exception as exc:  # noqa: BLE001 - broad catch to ensure clean disconnects
        logger.warning("WebSocket connection closed unexpectedly: %s", exc)
    finally:
        ws_manager.disconnect(websocket, user.id)


# API version information endpoint
@app.get("/api/versions", tags=["system"])
def get_api_versions():
    """Get information about available API versions and deprecations.

    Returns:
        dict: A dictionary containing API version information including
            current version, supported versions, and deprecation notices.
    """
    return get_version_info()


# Health check at root level (no versioning needed)
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Perform an enhanced health check of the application.

    Checks the status of critical system components including the database,
    API functionality, cache connection, and background tasks.

    Args:
        db: Database session dependency for connectivity check.

    Returns:
        dict: A comprehensive health status report containing:
            - status: Overall health status ('healthy' or 'unhealthy')
            - timestamp: Current UTC timestamp
            - version: Application version
            - database: Database connection status
            - api: API functionality status
            - cache: Redis cache connection status
            - resources_count: Number of resources in the system
            - background_tasks: Status of background task execution
            - rate_limiting: Rate limiting configuration status
    """
    task_status = "unknown"
    if cleanup_task:
        if cleanup_task.done():
            if cleanup_task.cancelled():
                task_status = "cancelled"
            elif cleanup_task.exception():
                task_status = "failed"
            else:
                task_status = "completed"
        else:
            task_status = "running"
    else:
        task_status = "not_started"

    try:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
        db_status = "healthy"

        from app.services import ResourceService

        service = ResourceService(db)
        resources_count = len(service.get_all_resources())
        api_status = "healthy"

    except Exception as e:
        db_status = "unhealthy"
        api_status = f"error: {str(e)[:100]}"
        resources_count = 0

    overall_status = (
        "healthy" if db_status == "healthy" and api_status == "healthy" else "unhealthy"
    )

    # Check cache status
    cache_status = "disabled"
    if settings.cache_enabled:
        cache_status = "connected" if cache_manager.is_connected() else "disconnected"

    return {
        "status": overall_status,
        "timestamp": utcnow(),
        "version": settings.app_version,
        "database": db_status,
        "api": api_status,
        "cache": cache_status,
        "resources_count": resources_count,
        "background_tasks": {"cleanup_task": task_status},
        "rate_limiting": {"enabled": settings.rate_limit_enabled},
    }


@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes readiness probe endpoint.

    Determines if the application is ready to receive traffic. This check
    verifies that all required dependencies (database, cache, etc.) are
    available and the application can process requests.

    Returns:
        dict: Readiness details if the application is ready.

    Raises:
        HTTPException: Returns 503 Service Unavailable if the application
            is not ready to receive traffic.
    """
    is_ready, details = check_readiness(db)

    if not is_ready:
        return JSONResponse(
            content=details, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return details


@app.get("/live")
def liveness_check():
    """Kubernetes liveness probe endpoint.

    A simple check to verify the application process is alive and can
    respond to requests. This is a lightweight check that doesn't verify
    dependencies.

    Returns:
        dict: Liveness status details confirming the application is running.
    """
    is_alive, details = check_liveness()
    return details


@app.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint.

    Exports application metrics in Prometheus text format for scraping
    by monitoring systems.

    Returns:
        Response: Plain text response containing metrics in Prometheus
            exposition format.
    """
    prometheus_metrics = metrics.export_prometheus()
    return Response(
        content=prometheus_metrics,
        media_type="text/plain; charset=utf-8",
    )


@app.get("/api/v1/metrics/summary")
@limiter.limit(settings.rate_limit_authenticated)
def get_metrics_summary(
    request: Request,
    current_user: models.User = Depends(get_current_user),
):
    """Get a JSON summary of application metrics.

    Provides a structured summary of all collected metrics for authenticated
    users. This endpoint is rate-limited to prevent abuse.

    Args:
        request: The incoming request (used for rate limiting).
        current_user: The authenticated user making the request.

    Returns:
        dict: A JSON object containing summarized metrics including request
            counts, latencies, error rates, and system statistics.
    """
    return metrics.get_summary()


# =============================================================================
# API v1 Endpoints
# =============================================================================


# Authentication endpoints
@app.post(
    "/api/v1/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
@limiter.limit(settings.rate_limit_auth)
def register_user(
    request: Request,
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    """Register a new user account.

    Creates a new user with the provided credentials. The username must be
    unique across the system.

    Args:
        request: The incoming request (used for rate limiting).
        user_data: User creation data including username and password.
        db: Database session dependency.

    Returns:
        UserResponse: The created user's public information.

    Raises:
        HTTPException: 400 Bad Request if the username is already taken.
    """
    user_service = UserService(db)

    existing_user = user_service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    return user_service.create_user(user_data)


@app.post("/api/v1/token", tags=["Authentication"])
@limiter.limit(settings.rate_limit_auth)
def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate a user and issue access tokens.

    Validates user credentials and returns JWT access and refresh tokens.
    Implements account lockout protection after multiple failed attempts.

    Args:
        request: The incoming request (used for rate limiting and IP logging).
        form_data: OAuth2 password grant form containing username and password.
        db: Database session dependency.

    Returns:
        dict: Token response containing:
            - access_token: JWT for API authentication
            - refresh_token: Token for obtaining new access tokens
            - token_type: Always 'bearer'

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid or
            account is locked.
    """
    # Get client IP for logging
    client_ip = request.client.host if request.client else None

    # Authenticate with lockout protection
    user, error_message = authenticate_user_with_lockout(
        db, form_data.username, form_data.password, client_ip
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message or "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(db, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.get("/api/v1/users/me", tags=["Authentication"])
@limiter.limit(settings.rate_limit_authenticated)
def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the current authenticated user's profile information.

    Args:
        request: The incoming request (used for rate limiting).
        db: Database session dependency.
        current_user: The authenticated user from the JWT token.

    Returns:
        dict: User profile information including:
            - id: User's unique identifier
            - username: User's username
            - email: User's email address (if set)
            - email_verified: Email verification status
            - mfa_enabled: Multi-factor authentication status
            - email_notifications: Email notification preference
            - reminder_hours: Hours before reservation to send reminder
            - is_admin: Whether user has admin role
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "mfa_enabled": current_user.mfa_enabled,
        "email_notifications": current_user.email_notifications,
        "reminder_hours": current_user.reminder_hours,
        "is_admin": rbac.is_admin(current_user, db),
    }


@app.patch(
    "/api/v1/users/me/preferences",
    response_model=schemas.UserDetailResponse,
    tags=["Authentication"],
)
@limiter.limit(settings.rate_limit_authenticated)
def update_user_preferences(
    request: Request,
    preferences: schemas.UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update the current user's notification preferences.

    Allows users to configure their email notification settings and
    reminder timing preferences.

    Args:
        request: The incoming request (used for rate limiting).
        preferences: The preference updates to apply.
        db: Database session dependency.
        current_user: The authenticated user making the request.

    Returns:
        UserDetailResponse: The updated user profile with new preferences.
    """
    if preferences.email_notifications is not None:
        current_user.email_notifications = preferences.email_notifications

    if preferences.reminder_hours is not None:
        current_user.reminder_hours = preferences.reminder_hours

    db.commit()
    db.refresh(current_user)

    return current_user


@app.post("/api/v1/token/refresh", tags=["Authentication"])
@limiter.limit(settings.rate_limit_auth)
def refresh_access_token(
    request: Request,
    refresh_token: str = Query(..., description="The refresh token"),
    db: Session = Depends(get_db),
):
    """Refresh an access token using a valid refresh token.

    Implements secure token rotation: the old refresh token is revoked
    and a new one is issued. If a revoked token is reused, the entire
    token family is invalidated as a security measure.

    Args:
        request: The incoming request (used for rate limiting).
        refresh_token: The refresh token to exchange for new tokens.
        db: Database session dependency.

    Returns:
        dict: New token pair containing:
            - access_token: New JWT for API authentication
            - refresh_token: New refresh token (old one is revoked)
            - token_type: Always 'bearer'

    Raises:
        HTTPException: 401 Unauthorized if the refresh token is invalid,
            expired, or has been revoked.
    """
    # Verify the refresh token
    token_record, user = verify_refresh_token(db, refresh_token)

    # Rotate the refresh token (revoke old, create new)
    new_refresh_token = rotate_refresh_token(db, token_record)

    # Create new access token
    new_access_token = create_access_token(data={"sub": user.username})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@app.post("/api/v1/logout", tags=["Authentication"])
@limiter.limit(settings.rate_limit_authenticated)
def logout_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Log out the current user by revoking all refresh tokens.

    Invalidates all active sessions for the user across all devices.
    Access tokens will remain valid until they expire, but no new
    access tokens can be obtained.

    Args:
        request: The incoming request (used for rate limiting).
        db: Database session dependency.
        current_user: The authenticated user to log out.

    Returns:
        dict: Logout confirmation containing:
            - message: Success message
            - revoked_tokens: Number of refresh tokens that were revoked
    """
    revoked_count = revoke_user_tokens(db, current_user.id)

    return {
        "message": "Successfully logged out",
        "revoked_tokens": revoked_count,
    }


# Resource endpoints
@app.post(
    "/api/v1/resources",
    response_model=schemas.ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Resources"],
)
@limiter.limit(settings.rate_limit_authenticated)
def create_resource(
    request: Request,
    resource_data: schemas.ResourceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new bookable resource (admin only).

    Args:
        request: The incoming request (used for rate limiting).
        resource_data: Resource creation data including name and optional tags.
        db: Database session dependency.
        current_user: The authenticated user creating the resource.

    Returns:
        ResourceResponse: The created resource details.

    Raises:
        HTTPException: 403 if user is not an admin.
    """
    if not rbac.is_admin(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create resources",
        )

    resource_service = ResourceService(db)
    return resource_service.create_resource(resource_data)


@app.get(
    "/api/v1/resources",
    response_model=schemas.PaginatedResponse[schemas.ResourceResponse],
    tags=["Resources"],
)
@limiter.limit(settings.rate_limit_authenticated)
def list_resources(
    request: Request,
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Sort by: id, name, status"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    include_total: bool = Query(False, description="Include total count"),
    db: Session = Depends(get_db),
):
    """List all resources with pagination support.

    Args:
        request: The incoming request (used for rate limiting).
        cursor: Opaque cursor for pagination (from previous response).
        limit: Maximum number of resources to return (1-100).
        sort_by: Field to sort results by.
        sort_order: Sort direction ('asc' or 'desc').
        include_total: Whether to include total count in response.
        db: Database session dependency.

    Returns:
        PaginatedResponse: Paginated list of resources with navigation cursors.

    Raises:
        HTTPException: 400 Bad Request if pagination parameters are invalid.
    """
    resource_service = ResourceService(db)
    pagination = schemas.PaginationParams(
        cursor=cursor, limit=limit, sort_by=sort_by, sort_order=sort_order
    )

    try:
        resources, next_cursor, has_more, total_count = (
            resource_service.get_resources_paginated(
                pagination=pagination, include_total=include_total
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return schemas.PaginatedResponse(
        data=resources,
        next_cursor=next_cursor,
        prev_cursor=None,
        has_more=has_more,
        total_count=total_count,
    )


@app.get(
    "/api/v1/resources/tags",
    response_model=list[str],
    tags=["Resources"],
)
@limiter.limit(settings.rate_limit_authenticated)
def get_all_tags(
    request: Request,
    db: Session = Depends(get_db),
):
    """Get all unique tags from all resources.

    Returns a sorted list of all unique tags used across resources.

    Args:
        request: The incoming request (used for rate limiting).
        db: Database session dependency.

    Returns:
        list[str]: Sorted list of unique tags.
    """
    resources = db.query(models.Resource).all()
    tags_set = set()
    for resource in resources:
        if resource.tags:
            for tag in resource.tags:
                tags_set.add(tag)
    return sorted(tags_set)


@app.get(
    "/api/v1/resources/tags/details",
    response_model=list[schemas.TagInfo],
    tags=["Resources"],
)
@limiter.limit(settings.rate_limit_authenticated)
def get_all_tags_with_details(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all unique tags with usage counts (admin only).

    Returns a list of all tags with the number of resources using each tag.

    Args:
        request: The incoming request (used for rate limiting).
        db: Database session dependency.
        current_user: The authenticated user.

    Returns:
        list[TagInfo]: List of tags with resource counts.
    """
    if not rbac.is_admin(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view tag details",
        )

    resource_service = ResourceService(db)
    return resource_service.get_all_tags_with_counts()


@app.put(
    "/api/v1/resources/tags/rename",
    tags=["Resources"],
)
@limiter.limit(settings.rate_limit_authenticated)
def rename_tag_globally(
    request: Request,
    rename_data: schemas.TagRename,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Rename a tag across all resources (admin only).

    Updates all resources that have the specified tag to use the new name.

    Args:
        request: The incoming request (used for rate limiting).
        rename_data: The old and new tag names.
        db: Database session dependency.
        current_user: The authenticated user.

    Returns:
        dict: Success message with count of updated resources.

    Raises:
        HTTPException: 403 if user is not admin, 400 if tag doesn't exist
            or new name already exists.
    """
    if not rbac.is_admin(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can rename tags",
        )

    resource_service = ResourceService(db)
    try:
        updated_count = resource_service.rename_tag_globally(
            rename_data.old_name, rename_data.new_name
        )
        return {
            "message": "Tag renamed successfully",
            "old_name": rename_data.old_name,
            "new_name": rename_data.new_name,
            "updated_resources": updated_count,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@app.delete(
    "/api/v1/resources/tags/{tag_name}",
    tags=["Resources"],
)
@limiter.limit(settings.rate_limit_authenticated)
def delete_tag_globally(
    request: Request,
    tag_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a tag from all resources (admin only).

    Removes the specified tag from all resources that have it.

    Args:
        request: The incoming request (used for rate limiting).
        tag_name: The tag name to delete.
        db: Database session dependency.
        current_user: The authenticated user.

    Returns:
        dict: Success message with count of updated resources.

    Raises:
        HTTPException: 403 if user is not admin, 400 if tag doesn't exist.
    """
    if not rbac.is_admin(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete tags",
        )

    resource_service = ResourceService(db)
    try:
        updated_count = resource_service.delete_tag_globally(tag_name)
        return {
            "message": "Tag deleted successfully",
            "deleted_tag": tag_name,
            "updated_resources": updated_count,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@app.get(
    "/api/v1/resources/search",
    response_model=schemas.PaginatedResponse[schemas.ResourceResponse],
    tags=["Resources"],
)
@limiter.limit(settings.rate_limit_authenticated)
def search_resources(
    request: Request,
    q: str | None = Query(None, description="Search query for resource names"),
    status_filter: str | None = Query(
        None,
        description="Filter by resource status: 'available', 'in_use', 'unavailable', or 'all'",
        alias="status",
    ),
    available_only: bool = Query(
        None, description="Legacy parameter - use 'status' instead"
    ),
    available_from: datetime | None = Query(
        None, description="Check availability from this time"
    ),
    available_until: datetime | None = Query(
        None, description="Check availability until this time"
    ),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Sort by: id, name, status"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    include_total: bool = Query(False, description="Include total count"),
    db: Session = Depends(get_db),
):
    """Search resources with filtering and time-based availability checking.

    Allows searching resources by name, filtering by status and tags,
    and checking availability within a specific time window.

    Args:
        request: The incoming request (used for rate limiting).
        q: Search query to match against resource names.
        status_filter: Filter by status ('available', 'in_use', 'unavailable', 'all').
        available_only: Deprecated - use status_filter instead.
        available_from: Start of availability check window.
        available_until: End of availability check window.
        tags: List of tags to filter by (resources must have all specified tags).
        cursor: Pagination cursor from previous response.
        limit: Maximum results per page (1-100).
        sort_by: Field to sort by.
        sort_order: Sort direction.
        include_total: Include total count in response.
        db: Database session dependency.

    Returns:
        PaginatedResponse: Paginated search results with matching resources.

    Raises:
        HTTPException: 400 Bad Request if parameters are invalid (e.g., end
            time before start time, start time in the past).
    """
    if available_from:
        available_from = ensure_timezone_aware(available_from)
    if available_until:
        available_until = ensure_timezone_aware(available_until)

    if available_from and available_until:
        if available_until <= available_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time",
            )

        if available_from <= utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be in the future",
            )

    final_status_filter = None
    if status_filter is not None:
        valid_statuses = ["available", "in_use", "unavailable", "all"]
        if status_filter not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            )
        final_status_filter = status_filter
    elif available_only is not None:
        final_status_filter = "available" if available_only else "all"
    else:
        final_status_filter = "available"

    resource_service = ResourceService(db)
    pagination = schemas.PaginationParams(
        cursor=cursor, limit=limit, sort_by=sort_by, sort_order=sort_order
    )
    try:
        resources, next_cursor, has_more, total_count = (
            resource_service.get_resources_paginated(
                pagination=pagination,
                query=q,
                status_filter=final_status_filter,
                available_from=available_from,
                available_until=available_until,
                tags=tags,
                include_total=include_total,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return schemas.PaginatedResponse(
        data=resources,
        next_cursor=next_cursor,
        prev_cursor=None,
        has_more=has_more,
        total_count=total_count,
    )


@app.post("/api/v1/resources/upload", tags=["Resources"])
@limiter.limit(settings.rate_limit_heavy)
def upload_resources_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Bulk upload resources from a CSV file (admin only).

    Accepts a CSV file with columns: name (required), tags (comma-separated),
    and available (true/false). Creates resources for each valid row.

    Args:
        request: The incoming request (used for rate limiting).
        file: The uploaded CSV file.
        db: Database session dependency.
        current_user: The authenticated user performing the upload.

    Returns:
        dict: Upload results containing:
            - created_count: Number of resources successfully created
            - errors: List of error messages (limited to first 10)

    Raises:
        HTTPException: 403 if user is not an admin.
        HTTPException: 400 Bad Request if the file is not a CSV or cannot
            be processed.
    """
    if not rbac.is_admin(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can upload resources",
        )

    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV",
        )

    try:
        content = file.file.read().decode("utf-8")
        reader = csv.DictReader(StringIO(content))

        resource_service = ResourceService(db)
        created_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                name = row.get("name", "").strip()
                if not name:
                    errors.append(f"Row {row_num}: Missing resource name")
                    continue

                tags = [
                    tag.strip() for tag in row.get("tags", "").split(",") if tag.strip()
                ]
                available = row.get("available", "true").lower() in ("true", "1", "yes")

                resource_data = schemas.ResourceCreate(
                    name=name, tags=tags, available=available
                )

                resource_service.create_resource(resource_data)
                created_count += 1

            except ValueError as ve:
                errors.append(f"Row {row_num}: {ve}")
            except Exception as e:
                errors.append(f"Row {row_num}: Unexpected error: {e}")

        return {
            "created_count": created_count,
            "errors": errors[:10],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process CSV file: {str(e)}",
        ) from e


@app.put(
    "/api/v1/resources/{resource_id}",
    response_model=schemas.ResourceResponse,
    tags=["Resources"],
)
@limiter.limit(settings.rate_limit_authenticated)
def update_resource(
    request: Request,
    resource_id: int,
    update_data: schemas.ResourceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a resource's details (admin only).

    Allows administrators to update resource name, description, and tags.
    The resource must not be currently in use.

    Args:
        request: The incoming request (used for rate limiting).
        resource_id: The unique identifier of the resource to update.
        update_data: The update data with optional name, description, tags.
        db: Database session dependency.
        current_user: The authenticated user making the request.

    Returns:
        ResourceResponse: The updated resource details.

    Raises:
        HTTPException: 403 if user is not an admin, 404 if resource not found,
            400 if resource is in use or name conflicts with existing resource.
    """
    if not is_admin(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can edit resources",
        )

    resource_service = ResourceService(db)
    try:
        return resource_service.update_resource(resource_id, update_data)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        ) from e


@app.get("/api/v1/resources/{resource_id}/schedule", tags=["Resources"])
@limiter.limit(settings.rate_limit_authenticated)
def get_resource_schedule(
    request: Request,
    resource_id: int,
    days_ahead: int = Query(7, description="Number of days to check ahead"),
    db: Session = Depends(get_db),
):
    """Get the detailed availability schedule for a specific resource.

    Returns a day-by-day breakdown of the resource's availability,
    including existing reservations and available time slots.

    Args:
        request: The incoming request (used for rate limiting).
        resource_id: The unique identifier of the resource.
        days_ahead: Number of days to include in the schedule (default: 7).
        db: Database session dependency.

    Returns:
        dict: Schedule information including daily availability and bookings.

    Raises:
        HTTPException: 404 Not Found if the resource doesn't exist.
    """
    resource_service = ResourceService(db)

    try:
        schedule = resource_service.get_resource_schedule(resource_id, days_ahead)
        return schedule
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@app.get("/api/v1/resources/{resource_id}/availability", tags=["Resources"])
@limiter.limit(settings.rate_limit_authenticated)
def get_resource_availability(
    request: Request,
    resource_id: int,
    days_ahead: int = Query(7, description="Number of days to check ahead"),
    db: Session = Depends(get_db),
):
    """Get detailed availability information for a specific resource.

    Alias for the schedule endpoint, providing the same availability
    information in a compatible format.

    Args:
        request: The incoming request (used for rate limiting).
        resource_id: The unique identifier of the resource.
        days_ahead: Number of days to check (default: 7).
        db: Database session dependency.

    Returns:
        dict: Availability information for the requested time period.

    Raises:
        HTTPException: 404 Not Found if the resource doesn't exist.
    """
    resource_service = ResourceService(db)

    try:
        availability = resource_service.get_resource_schedule(resource_id, days_ahead)
        return availability
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@app.put("/api/v1/resources/{resource_id}/status/unavailable", tags=["Resources"])
@limiter.limit(settings.rate_limit_authenticated)
def set_resource_unavailable(
    request: Request,
    resource_id: int,
    auto_reset_hours: int = 8,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a resource as unavailable for maintenance or repair (admin only).

    Sets the resource status to 'unavailable' with an optional auto-reset
    timer. After the specified hours, the background task will automatically
    reset the resource to 'available'.

    Args:
        request: The incoming request (used for rate limiting).
        resource_id: The unique identifier of the resource.
        auto_reset_hours: Hours until automatic reset to available (default: 8).
        db: Database session dependency.
        current_user: The authenticated user making the change.

    Returns:
        dict: Confirmation message and updated resource details including
            the auto-reset configuration.

    Raises:
        HTTPException: 403 if user is not an admin.
        HTTPException: 404 Not Found if the resource doesn't exist.
    """
    if not rbac.is_admin(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can set resources unavailable",
        )

    resource_service = ResourceService(db)

    try:
        resource = resource_service.set_resource_unavailable(
            resource_id, auto_reset_hours
        )
        return {
            "message": f"Resource set to unavailable for maintenance "
            f"(auto-reset in {auto_reset_hours} hours)",
            "resource": {
                "id": resource.id,
                "name": resource.name,
                "status": resource.status,
                "auto_reset_hours": resource.auto_reset_hours,
                "unavailable_since": (
                    resource.unavailable_since.isoformat()
                    if resource.unavailable_since
                    else None
                ),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@app.put("/api/v1/resources/{resource_id}/status/available", tags=["Resources"])
@limiter.limit(settings.rate_limit_authenticated)
def reset_resource_to_available(
    request: Request,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Reset a resource to available status (admin only).

    Manually resets a resource that was marked as unavailable back to
    the available state, clearing any auto-reset timer.

    Args:
        request: The incoming request (used for rate limiting).
        resource_id: The unique identifier of the resource.
        db: Database session dependency.
        current_user: The authenticated user making the change.

    Returns:
        dict: Confirmation message and updated resource details.

    Raises:
        HTTPException: 403 if user is not an admin.
        HTTPException: 404 Not Found if the resource doesn't exist.
    """
    if not rbac.is_admin(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can reset resource availability",
        )

    resource_service = ResourceService(db)

    try:
        resource = resource_service.reset_resource_to_available(resource_id)
        return {
            "message": "Resource reset to available",
            "resource": {
                "id": resource.id,
                "name": resource.name,
                "status": resource.status,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@app.get("/api/v1/resources/{resource_id}/status", tags=["Resources"])
@limiter.limit(settings.rate_limit_authenticated)
def get_resource_status(
    request: Request,
    resource_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed status information for a specific resource.

    Returns comprehensive status information including current availability,
    active reservations, and maintenance status.

    Args:
        request: The incoming request (used for rate limiting).
        resource_id: The unique identifier of the resource.
        db: Database session dependency.

    Returns:
        dict: Detailed status information for the resource.

    Raises:
        HTTPException: 404 Not Found if the resource doesn't exist.
    """
    resource_service = ResourceService(db)

    try:
        status_info = resource_service.get_resource_status(resource_id)
        return status_info
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@app.put("/api/v1/resources/{resource_id}/availability", tags=["Resources"])
@limiter.limit(settings.rate_limit_authenticated)
def update_resource_availability(
    request: Request,
    resource_id: int,
    availability_update: schemas.ResourceAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Manually update resource base availability (admin only).

    Sets the resource's base availability flag, typically used for
    maintenance windows or decommissioning resources.

    Args:
        request: The incoming request (used for rate limiting).
        resource_id: The unique identifier of the resource.
        availability_update: The new availability state to set.
        db: Database session dependency.
        current_user: The authenticated user making the change.

    Returns:
        dict: Confirmation message and updated resource details.

    Raises:
        HTTPException: 403 if user is not an admin.
        HTTPException: 404 Not Found if the resource doesn't exist.
    """
    if not rbac.is_admin(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update resource availability",
        )

    resource_service = ResourceService(db)

    try:
        resource = resource_service.update_resource_availability(
            resource_id, availability_update.available
        )
        return {
            "message": f"Resource availability updated to "
            f"{'available' if availability_update.available else 'unavailable'}",
            "resource": resource,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@app.get("/api/v1/resources/availability/summary", tags=["Resources"])
@limiter.limit(settings.rate_limit_authenticated)
def get_availability_summary(request: Request, db: Session = Depends(get_db)):
    """Get a summary of resource availability across the system.

    Provides aggregate statistics about resource availability including
    total counts, currently available, unavailable, and in-use resources.

    Args:
        request: The incoming request (used for rate limiting).
        db: Database session dependency.

    Returns:
        dict: Availability summary containing:
            - total_resources: Total number of resources
            - available_now: Resources currently available
            - unavailable_now: Resources marked unavailable
            - currently_in_use: Resources with active reservations
            - timestamp: Time of the summary
    """
    resource_service = ResourceService(db)

    resources = resource_service.get_all_resources()

    total_resources = len(resources)
    available_now = sum(1 for r in resources if r.available)
    unavailable_now = total_resources - available_now

    now = utcnow()
    in_use = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.status == "active",
            models.Reservation.start_time <= now,
            models.Reservation.end_time > now,
        )
        .count()
    )

    return {
        "total_resources": total_resources,
        "available_now": available_now,
        "unavailable_now": unavailable_now,
        "currently_in_use": in_use,
        "timestamp": now,
    }


# Reservation endpoints
@app.post(
    "/api/v1/reservations",
    response_model=schemas.ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Reservations"],
)
@limiter.limit(settings.rate_limit_authenticated)
def create_reservation(
    request: Request,
    reservation_data: schemas.ReservationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new reservation for a resource.

    Books a resource for the specified time period. The system automatically
    checks for conflicts with existing reservations.

    Args:
        request: The incoming request (used for rate limiting and timezone).
        reservation_data: Reservation details including resource, start, and end time.
        db: Database session dependency.
        current_user: The authenticated user making the reservation.

    Returns:
        ReservationResponse: The created reservation with times converted to
            the client's requested timezone.

    Raises:
        HTTPException: 409 Conflict if the time slot conflicts with existing
            reservations. 400 Bad Request for invalid time ranges.
    """
    reservation_service = ReservationService(db)
    tz = get_request_timezone(request)

    try:
        reservation = reservation_service.create_reservation(
            reservation_data, current_user.id
        )
        return convert_reservation_timezone(reservation, tz)
    except ValueError as e:
        if "conflicts" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e


@app.post(
    "/api/v1/reservations/recurring",
    response_model=list[schemas.ReservationResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["Reservations"],
)
@limiter.limit(settings.rate_limit_authenticated)
def create_recurring_reservations(
    request: Request,
    reservation_data: schemas.RecurringReservationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a series of recurring reservations.

    Creates multiple reservations based on a recurrence pattern (daily,
    weekly, etc.). All occurrences are checked for conflicts before
    any reservations are created.

    Args:
        request: The incoming request (used for rate limiting and timezone).
        reservation_data: Recurring reservation details including pattern.
        db: Database session dependency.
        current_user: The authenticated user making the reservations.

    Returns:
        list[ReservationResponse]: List of all created reservations with
            times converted to the client's requested timezone.

    Raises:
        HTTPException: 409 Conflict if any occurrence conflicts with
            existing reservations.
    """
    reservation_service = ReservationService(db)
    tz = get_request_timezone(request)
    try:
        reservations = reservation_service.create_recurring_reservations(
            reservation_data, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    return [convert_reservation_timezone(res, tz) for res in reservations]


@app.get(
    "/api/v1/reservations/my",
    response_model=schemas.PaginatedResponse[schemas.ReservationResponse],
    tags=["Reservations"],
)
@limiter.limit(settings.rate_limit_authenticated)
def get_my_reservations(
    request: Request,
    include_cancelled: bool = Query(
        False, description="Include cancelled reservations"
    ),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(
        "start_time", description="Sort by: id, start_time, end_time, created_at"
    ),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    include_total: bool = Query(False, description="Include total count"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the current user's reservations.

    Retrieves all reservations made by the authenticated user with
    pagination support and optional filtering.

    Args:
        request: The incoming request (used for rate limiting and timezone).
        include_cancelled: Whether to include cancelled reservations.
        cursor: Pagination cursor from previous response.
        limit: Maximum reservations per page (1-100).
        sort_by: Field to sort by.
        sort_order: Sort direction ('asc' or 'desc').
        include_total: Include total count in response.
        db: Database session dependency.
        current_user: The authenticated user.

    Returns:
        PaginatedResponse: Paginated list of the user's reservations.

    Raises:
        HTTPException: 400 Bad Request for invalid pagination parameters.
    """
    reservation_service = ReservationService(db)
    tz = get_request_timezone(request)
    pagination = schemas.PaginationParams(
        cursor=cursor, limit=limit, sort_by=sort_by, sort_order=sort_order
    )
    try:
        reservations, next_cursor, has_more, total_count = (
            reservation_service.get_user_reservations_paginated(
                current_user.id,
                include_cancelled=include_cancelled,
                pagination=pagination,
                include_total=include_total,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    reservations_local = [convert_reservation_timezone(res, tz) for res in reservations]

    return schemas.PaginatedResponse(
        data=reservations_local,
        next_cursor=next_cursor,
        prev_cursor=None,
        has_more=has_more,
        total_count=total_count,
    )


@app.post("/api/v1/reservations/{reservation_id}/cancel", tags=["Reservations"])
@limiter.limit(settings.rate_limit_authenticated)
def cancel_reservation(
    request: Request,
    reservation_id: int,
    cancellation: schemas.ReservationCancel,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cancel an existing reservation.

    Marks a reservation as cancelled. Users can only cancel their own
    reservations unless they have admin privileges.

    Args:
        request: The incoming request (used for rate limiting).
        reservation_id: The unique identifier of the reservation to cancel.
        cancellation: Cancellation details including optional reason.
        db: Database session dependency.
        current_user: The authenticated user requesting cancellation.

    Returns:
        dict: Cancellation confirmation containing:
            - message: Success message
            - reservation_id: The cancelled reservation ID
            - cancelled_at: Timestamp of cancellation

    Raises:
        HTTPException: 404 Not Found if reservation doesn't exist.
            403 Forbidden if user doesn't own the reservation and is not admin.
            400 Bad Request for already cancelled reservations.
    """
    reservation_service = ReservationService(db)
    user_is_admin = rbac.is_admin(current_user, db)

    try:
        cancelled_reservation = reservation_service.cancel_reservation(
            reservation_id, cancellation, current_user.id, is_admin=user_is_admin
        )
        return {
            "message": "Reservation cancelled successfully",
            "reservation_id": reservation_id,
            "cancelled_at": cancelled_reservation.cancelled_at,
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        elif "only cancel your own" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e


@app.get("/api/v1/reservations/{reservation_id}/history", tags=["Reservations"])
@limiter.limit(settings.rate_limit_authenticated)
def get_reservation_history(
    request: Request,
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the history of changes for a specific reservation.

    Returns an audit trail of all actions taken on a reservation,
    including creation, modifications, and cancellation.

    Args:
        request: The incoming request (used for rate limiting).
        reservation_id: The unique identifier of the reservation.
        db: Database session dependency.
        current_user: The authenticated user requesting history.

    Returns:
        list: List of history entries for the reservation, each containing
            action type, timestamp, and details.

    Raises:
        HTTPException: 404 Not Found if reservation doesn't exist.
            403 Forbidden if user doesn't own the reservation.
    """
    reservation = (
        db.query(models.Reservation)
        .filter(models.Reservation.id == reservation_id)
        .first()
    )

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )

    if reservation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    reservation_service = ReservationService(db)
    return reservation_service.get_reservation_history(reservation_id)


# Admin endpoints
@app.post("/api/v1/admin/cleanup-expired", tags=["Admin"])
@limiter.limit(settings.rate_limit_authenticated)
def manual_cleanup_expired_reservations(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Manually trigger cleanup of expired reservations.

    Forces immediate processing of all expired reservations that haven't
    been cleaned up by the background task. Useful for maintenance or
    when immediate cleanup is required.

    Args:
        request: The incoming request (used for rate limiting).
        db: Database session dependency.
        current_user: The authenticated admin user.

    Returns:
        dict: Cleanup results containing:
            - message: Summary of cleanup action
            - expired_count: Number of reservations marked as expired
            - timestamp: Time of cleanup operation

    Raises:
        HTTPException: 500 Internal Server Error if cleanup fails.
    """
    try:
        now = utcnow()

        expired_reservations = (
            db.query(models.Reservation)
            .filter(
                models.Reservation.status == "active",
                models.Reservation.end_time < now,
            )
            .all()
        )

        cleanup_count = 0
        for reservation in expired_reservations:
            history = models.ReservationHistory(
                reservation_id=reservation.id,
                action="expired",
                user_id=reservation.user_id,
                details=f"Reservation manually expired by user {current_user.id} "
                f"at {now.isoformat()}",
            )
            db.add(history)
            reservation.status = "expired"
            cleanup_count += 1

        db.commit()

        return {
            "message": f"Successfully cleaned up {cleanup_count} expired reservations",
            "expired_count": cleanup_count,
            "timestamp": now,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during cleanup: {str(e)}",
        ) from e


# =============================================================================
# Include auth sub-routers under /api/v1
# =============================================================================

# Create a v1 router for auth sub-routes
v1_auth_router = APIRouter(prefix="/api/v1")
v1_auth_router.include_router(auth_router)
v1_auth_router.include_router(mfa_router)
v1_auth_router.include_router(roles_router)
v1_auth_router.include_router(oauth_router)
v1_auth_router.include_router(setup_router)

app.include_router(v1_auth_router)
app.include_router(analytics_router)
app.include_router(approvals_router)
app.include_router(audit_router)
app.include_router(bulk_router)
app.include_router(notifications_router)
app.include_router(quotas_router)
app.include_router(search_router)
app.include_router(waitlist_router)
app.include_router(webhooks_router)
app.include_router(resource_groups_router)
app.include_router(business_hours_router)
app.include_router(calendar_router)
app.include_router(labels_router)


# =============================================================================
# Legacy endpoints (deprecated, will be removed in v2)
# These redirect/proxy to v1 endpoints for backward compatibility
# =============================================================================


@app.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    deprecated=True,
)
def register_user_legacy(
    request: Request,
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    """Legacy user registration endpoint.

    Deprecated:
        Use /api/v1/register instead. This endpoint will be removed in v2.

    Args:
        request: The incoming request.
        user_data: User creation data.
        db: Database session dependency.

    Returns:
        UserResponse: The created user.
    """
    return register_user(request, user_data, db)


@app.post("/token", include_in_schema=False, deprecated=True)
def login_user_legacy(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Legacy authentication endpoint.

    Deprecated:
        Use /api/v1/token instead. This endpoint will be removed in v2.

    Args:
        request: The incoming request.
        form_data: OAuth2 password grant form.
        db: Database session dependency.

    Returns:
        dict: Token response.
    """
    return login_user(request, form_data, db)


@app.get("/users/me", include_in_schema=False, deprecated=True)
def get_current_user_info_legacy(
    request: Request,
    current_user: models.User = Depends(get_current_user),
):
    """Legacy current user info endpoint.

    Deprecated:
        Use /api/v1/users/me instead. This endpoint will be removed in v2.

    Args:
        request: The incoming request.
        current_user: The authenticated user.

    Returns:
        dict: User information.
    """
    return get_current_user_info(request, current_user)


@app.post(
    "/resources",
    response_model=schemas.ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    deprecated=True,
)
def create_resource_legacy(
    request: Request,
    resource_data: schemas.ResourceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Legacy resource creation endpoint.

    Deprecated:
        Use /api/v1/resources instead. This endpoint will be removed in v2.

    Args:
        request: The incoming request.
        resource_data: Resource creation data.
        db: Database session dependency.
        current_user: The authenticated user.

    Returns:
        ResourceResponse: The created resource.
    """
    return create_resource(request, resource_data, db, current_user)


@app.get(
    "/resources",
    response_model=list[schemas.ResourceResponse],
    include_in_schema=False,
    deprecated=True,
)
def list_resources_legacy(request: Request, db: Session = Depends(get_db)):
    """Legacy resource listing endpoint.

    Deprecated:
        Use /api/v1/resources instead. This endpoint will be removed in v2.

    Args:
        request: The incoming request.
        db: Database session dependency.

    Returns:
        list: List of resources.
    """
    return list_resources(request, db)


@app.get(
    "/resources/search",
    response_model=list[schemas.ResourceResponse],
    include_in_schema=False,
    deprecated=True,
)
def search_resources_legacy(
    request: Request,
    q: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    available_only: bool = Query(None),
    available_from: datetime | None = Query(None),
    available_until: datetime | None = Query(None),
    db: Session = Depends(get_db),
):
    """Legacy resource search endpoint.

    Deprecated:
        Use /api/v1/resources/search instead. This endpoint will be removed in v2.

    Args:
        request: The incoming request.
        q: Search query.
        status_filter: Status filter.
        available_only: Availability filter.
        available_from: Start of availability window.
        available_until: End of availability window.
        db: Database session dependency.

    Returns:
        list: List of matching resources.
    """
    return search_resources(
        request, q, status_filter, available_only, available_from, available_until, db
    )


@app.post(
    "/reservations",
    response_model=schemas.ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    deprecated=True,
)
def create_reservation_legacy(
    request: Request,
    reservation_data: schemas.ReservationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Legacy reservation creation endpoint.

    Deprecated:
        Use /api/v1/reservations instead. This endpoint will be removed in v2.

    Args:
        request: The incoming request.
        reservation_data: Reservation creation data.
        db: Database session dependency.
        current_user: The authenticated user.

    Returns:
        ReservationResponse: The created reservation.
    """
    return create_reservation(request, reservation_data, db, current_user)


@app.get(
    "/reservations/my",
    response_model=list[schemas.ReservationResponse],
    include_in_schema=False,
    deprecated=True,
)
def get_my_reservations_legacy(
    request: Request,
    include_cancelled: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Legacy user reservations endpoint.

    Deprecated:
        Use /api/v1/reservations/my instead. This endpoint will be removed in v2.

    Args:
        request: The incoming request.
        include_cancelled: Include cancelled reservations.
        db: Database session dependency.
        current_user: The authenticated user.

    Returns:
        list: List of user's reservations.
    """
    return get_my_reservations(request, include_cancelled, db, current_user)


# Include legacy auth routers at root level for backward compatibility
app.include_router(mfa_router)
app.include_router(roles_router)
app.include_router(oauth_router)
app.include_router(setup_router)
