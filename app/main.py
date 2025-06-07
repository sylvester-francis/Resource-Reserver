import csv
from io import StringIO
from typing import List, Optional
from datetime import datetime, timezone
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, status  # noqa : E501
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db, engine
from app.services import UserService, ResourceService, ReservationService
from app.auth import authenticate_user, create_access_token, get_current_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to control the cleanup task
cleanup_task = None


async def cleanup_expired_reservations():
    """Background task to clean up expired reservations and update availability."""  # noqa : E501
    from app.database import SessionLocal

    logger.info("Starting cleanup task for expired reservations")

    while True:
        try:
            db = SessionLocal()
            now = datetime.now(timezone.utc)

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
                    f"Cleaning up {len(expired_reservations)} expired reservations"  # noqa : E501
                )

                for reservation in expired_reservations:
                    # Log the cleanup action
                    history = models.ReservationHistory(
                        reservation_id=reservation.id,
                        action="expired",
                        user_id=reservation.user_id,
                        details=f"Reservation automatically expired at {now.isoformat()}",  # noqa : E501
                    )
                    db.add(history)

                    # Update status to expired
                    reservation.status = "expired"

                    logger.info(
                        f"Expired reservation {reservation.id} for resource {reservation.resource_id}"  # noqa : E501
                    )

                db.commit()
                logger.info("Expired reservations cleanup completed")
            else:
                logger.debug("No expired reservations found")

            db.close()

        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            try:
                db.close()
            except Exception:
                pass

        # Run every 5 minutes (300 seconds)
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    global cleanup_task

    # Startup
    logger.info("Starting FastAPI application...")

    # Create database tables
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

    # Start the background cleanup task
    cleanup_task = asyncio.create_task(cleanup_expired_reservations())
    logger.info("Background cleanup task started")

    yield  # Application is running

    # Shutdown
    logger.info("Shutting down FastAPI application...")

    # Cancel the background task
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
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Enhanced health check endpoint
@app.get("/health")
def health_check():
    """Enhanced health check endpoint for monitoring."""
    global cleanup_task

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

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "background_tasks": {"cleanup_task": task_status},
    }


# Authentication endpoints
@app.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):  # noqa : E501
    """Register a new user."""
    user_service = UserService(db)

    # Check if user already exists
    existing_user = user_service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    return user_service.create_user(user_data)


@app.post("/token")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate user and return access token."""
    # Normalize username from form data
    normalized_username = form_data.username.lower()

    user = authenticate_user(db, normalized_username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# Resource endpoints
@app.post(
    "/resources",
    response_model=schemas.ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resource(
    resource_data: schemas.ResourceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new resource."""
    resource_service = ResourceService(db)
    return resource_service.create_resource(resource_data)


@app.get("/resources", response_model=List[schemas.ResourceResponse])
def list_resources(db: Session = Depends(get_db)):
    """List all resources."""
    resource_service = ResourceService(db)
    return resource_service.get_all_resources()


@app.get("/resources/search", response_model=List[schemas.ResourceResponse])
def search_resources(
    q: Optional[str] = Query(None, description="Search query for resource names"),  # noqa : E501
    available_only: bool = Query(
        True, description="Filter to only available resources"
    ),
    available_from: Optional[datetime] = Query(
        None, description="Check availability from this time"
    ),
    available_until: Optional[datetime] = Query(
        None, description="Check availability until this time"
    ),
    db: Session = Depends(get_db),
):
    """Search resources with optional time-based availability filtering."""

    # Validate time range if provided
    if available_from and available_until:
        if available_until <= available_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time",
            )

        if available_from <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be in the future",
            )

    resource_service = ResourceService(db)
    return resource_service.search_resources(
        q, available_only, available_from, available_until
    )


@app.post("/resources/upload")
def upload_resources_csv(
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
                    tag.strip()
                    for tag in row.get("tags", "").split(",")
                    if tag.strip()  # noqa : E501
                ]
                available = row.get("available", "true").lower() in ("true", "1", "yes")  # noqa : E501

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
            "errors": errors[:10],  # Limit to first 10 errors
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process CSV file: {str(e)}",
        )


@app.get("/resources/{resource_id}/availability")
def get_resource_availability(
    resource_id: int,
    days_ahead: int = Query(7, description="Number of days to check ahead"),
    db: Session = Depends(get_db),
):
    """Get detailed availability schedule for a specific resource."""
    resource_service = ResourceService(db)

    try:
        availability = resource_service.get_resource_availability_schedule(
            resource_id, days_ahead
        )
        return availability
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))  # noqa : E501


@app.put("/resources/{resource_id}/availability")
def update_resource_availability(
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
            "message": f"Resource availability updated to {'available' if availability_update.available else 'unavailable'}",  # noqa : E501
            "resource": resource,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))  # noqa : E501


@app.get("/resources/availability/summary")
def get_availability_summary(db: Session = Depends(get_db)):
    """Get summary of resource availability status."""
    resource_service = ResourceService(db)

    resources = resource_service.get_all_resources()

    total_resources = len(resources)
    available_now = sum(1 for r in resources if r.available)
    unavailable_now = total_resources - available_now

    # Get resources currently in use
    now = datetime.utcnow()
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
    "/reservations",
    response_model=schemas.ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reservation(
    reservation_data: schemas.ReservationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new reservation."""
    reservation_service = ReservationService(db)

    try:
        return reservation_service.create_reservation(reservation_data, current_user.id)  # noqa : E501
    except ValueError as e:
        if "conflicts" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))  # noqa : E501
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))  # noqa : E501


@app.get("/reservations/my", response_model=List[schemas.ReservationResponse])
def get_my_reservations(
    include_cancelled: bool = Query(
        False, description="Include cancelled reservations"
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get current user's reservations."""
    reservation_service = ReservationService(db)
    return reservation_service.get_user_reservations(current_user.id, include_cancelled)  # noqa : E501


@app.post("/reservations/{reservation_id}/cancel")
def cancel_reservation(
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))  # noqa : E501
        elif "only cancel your own" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))  # noqa : E501
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))  # noqa : E501


@app.get("/reservations/{reservation_id}/history")
def get_reservation_history(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get history for a specific reservation."""
    # Check if reservation exists and user has access
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
@app.post("/admin/cleanup-expired")
def manual_cleanup_expired_reservations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),  # noqa : E501
):
    """Manually trigger cleanup of expired reservations (admin endpoint)."""
    try:
        now = datetime.now(timezone.utc)

        # Find expired reservations
        expired_reservations = (
            db.query(models.Reservation)
            .filter(
                models.Reservation.status == "active",
                models.Reservation.end_time < now,  # noqa : E501
            )
            .all()
        )

        cleanup_count = 0
        for reservation in expired_reservations:
            # Log the cleanup action
            history = models.ReservationHistory(
                reservation_id=reservation.id,
                action="expired",
                user_id=reservation.user_id,
                details=f"Reservation manually expired by user {current_user.id} at {now.isoformat()}",  # noqa : E501
            )
            db.add(history)

            # Update status to expired
            reservation.status = "expired"
            cleanup_count += 1

        db.commit()

        return {
            "message": f"Successfully cleaned up {cleanup_count} expired reservations",  # noqa : E501
            "expired_count": cleanup_count,
            "timestamp": now,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during cleanup: {str(e)}",
        )


# Backward compatibility endpoints
@app.post(
    "/reserve",
    response_model=schemas.ReservationResponse,
    include_in_schema=False,
)
def reserve_resource(
    reservation_data: schemas.ReservationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Legacy endpoint for creating reservations."""
    return create_reservation(reservation_data, db, current_user)


@app.get(
    "/my_reservations",
    response_model=List[schemas.ReservationResponse],
    include_in_schema=False,
)
def get_my_reservations_legacy(
    include_cancelled: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Legacy endpoint for getting user reservations."""
    return get_my_reservations(include_cancelled, db, current_user)
