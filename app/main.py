# app/main.py - API v1 with rate limiting

import asyncio
import csv
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from io import StringIO

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app import models, rbac, schemas, setup
from app.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    revoke_user_tokens,
    rotate_refresh_token,
    verify_refresh_token,
)
from app.auth_routes import mfa_router, oauth_router, roles_router
from app.config import get_settings
from app.database import SessionLocal, engine, get_db
from app.services import ReservationService, ResourceService, UserService
from app.setup_routes import setup_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Global variable to control the cleanup task
cleanup_task = None


# Rate limiter key function that considers authentication
def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key based on user or IP."""
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
    """Ensure datetime is timezone-aware (convert to UTC if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def utcnow():
    """Get current UTC datetime that's timezone-aware."""
    return datetime.now(UTC)


async def cleanup_expired_reservations():
    """Background task to clean up expired reservations and auto-reset unavailable resources."""
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    global cleanup_task

    logger.info("Starting FastAPI application...")

    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

    try:
        db = SessionLocal()
        rbac.create_default_roles(db)
        setup.ensure_setup_state(db)
        db.close()
        logger.info("Default roles verified/created")
    except Exception as e:
        logger.error(f"Error creating default roles: {e}")

    cleanup_task = asyncio.create_task(cleanup_expired_reservations())
    logger.info("Background cleanup task started")

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

    logger.info("Application shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Resource Reservation System",
    description="A clean, scalable resource booking system",
    version="2.0.1",
    lifespan=lifespan,
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


# Health check at root level (no versioning needed)
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Enhanced health check endpoint for monitoring."""
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

    return {
        "status": overall_status,
        "timestamp": utcnow(),
        "version": settings.app_version,
        "database": db_status,
        "api": api_status,
        "resources_count": resources_count,
        "background_tasks": {"cleanup_task": task_status},
        "rate_limiting": {"enabled": settings.rate_limit_enabled},
    }


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
    """Register a new user."""
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
    """Authenticate user and return access and refresh tokens."""
    normalized_username = form_data.username.lower()

    user = authenticate_user(db, normalized_username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
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
    current_user: models.User = Depends(get_current_user),
):
    """Get current authenticated user's information."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "mfa_enabled": current_user.mfa_enabled,
    }


@app.post("/api/v1/token/refresh", tags=["Authentication"])
@limiter.limit(settings.rate_limit_auth)
def refresh_access_token(
    request: Request,
    refresh_token: str = Query(..., description="The refresh token"),
    db: Session = Depends(get_db),
):
    """Refresh an access token using a valid refresh token.

    This endpoint implements token rotation for security:
    - The old refresh token is revoked
    - A new refresh token is issued in the same family
    - If a revoked token is reused, the entire family is revoked (security measure)
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
    """Logout user by revoking all their refresh tokens.

    This invalidates all sessions for the user across all devices.
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
    """Create a new resource."""
    resource_service = ResourceService(db)
    return resource_service.create_resource(resource_data)


@app.get(
    "/api/v1/resources",
    response_model=list[schemas.ResourceResponse],
    tags=["Resources"],
)
@limiter.limit(settings.rate_limit_authenticated)
def list_resources(request: Request, db: Session = Depends(get_db)):
    """List all resources."""
    resource_service = ResourceService(db)
    return resource_service.get_all_resources()


@app.get(
    "/api/v1/resources/search",
    response_model=list[schemas.ResourceResponse],
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
    db: Session = Depends(get_db),
):
    """Search resources with optional time-based availability filtering."""
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
    return resource_service.search_resources(
        q, final_status_filter, available_from, available_until
    )


@app.post("/api/v1/resources/upload", tags=["Resources"])
@limiter.limit(settings.rate_limit_heavy)
def upload_resources_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Upload resources from a CSV file."""
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


@app.get("/api/v1/resources/{resource_id}/schedule", tags=["Resources"])
@limiter.limit(settings.rate_limit_authenticated)
def get_resource_schedule(
    request: Request,
    resource_id: int,
    days_ahead: int = Query(7, description="Number of days to check ahead"),
    db: Session = Depends(get_db),
):
    """Get detailed availability schedule for a specific resource."""
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
    """Get detailed availability schedule for a specific resource."""
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
    """Set resource as unavailable for maintenance/repair with auto-reset."""
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
    """Reset resource to available status."""
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
    """Get detailed status information for a resource."""
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
    """Manually update resource base availability (for maintenance, etc.)."""
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
    """Get summary of resource availability status."""
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
    """Create a new reservation."""
    reservation_service = ReservationService(db)

    try:
        return reservation_service.create_reservation(reservation_data, current_user.id)
    except ValueError as e:
        if "conflicts" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e


@app.get(
    "/api/v1/reservations/my",
    response_model=list[schemas.ReservationResponse],
    tags=["Reservations"],
)
@limiter.limit(settings.rate_limit_authenticated)
def get_my_reservations(
    request: Request,
    include_cancelled: bool = Query(
        False, description="Include cancelled reservations"
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get current user's reservations."""
    reservation_service = ReservationService(db)
    return reservation_service.get_user_reservations(current_user.id, include_cancelled)


@app.post("/api/v1/reservations/{reservation_id}/cancel", tags=["Reservations"])
@limiter.limit(settings.rate_limit_authenticated)
def cancel_reservation(
    request: Request,
    reservation_id: int,
    cancellation: schemas.ReservationCancel,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cancel a reservation."""
    reservation_service = ReservationService(db)

    try:
        cancelled_reservation = reservation_service.cancel_reservation(
            reservation_id, cancellation, current_user.id
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
    """Get history for a specific reservation."""
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
    """Manually trigger cleanup of expired reservations (admin endpoint)."""
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
v1_auth_router.include_router(mfa_router)
v1_auth_router.include_router(roles_router)
v1_auth_router.include_router(oauth_router)
v1_auth_router.include_router(setup_router)

app.include_router(v1_auth_router)


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
    """Legacy endpoint - use /api/v1/register instead."""
    return register_user(request, user_data, db)


@app.post("/token", include_in_schema=False, deprecated=True)
def login_user_legacy(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Legacy endpoint - use /api/v1/token instead."""
    return login_user(request, form_data, db)


@app.get("/users/me", include_in_schema=False, deprecated=True)
def get_current_user_info_legacy(
    request: Request,
    current_user: models.User = Depends(get_current_user),
):
    """Legacy endpoint - use /api/v1/users/me instead."""
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
    """Legacy endpoint - use /api/v1/resources instead."""
    return create_resource(request, resource_data, db, current_user)


@app.get(
    "/resources",
    response_model=list[schemas.ResourceResponse],
    include_in_schema=False,
    deprecated=True,
)
def list_resources_legacy(request: Request, db: Session = Depends(get_db)):
    """Legacy endpoint - use /api/v1/resources instead."""
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
    """Legacy endpoint - use /api/v1/resources/search instead."""
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
    """Legacy endpoint - use /api/v1/reservations instead."""
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
    """Legacy endpoint - use /api/v1/reservations/my instead."""
    return get_my_reservations(request, include_cancelled, db, current_user)


# Include legacy auth routers at root level for backward compatibility
app.include_router(mfa_router)
app.include_router(roles_router)
app.include_router(oauth_router)
app.include_router(setup_router)
