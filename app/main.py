# app/main.py
"""FastAPI application with clean endpoint organization."""

import csv
import os
from io import StringIO
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db, engine
from app.services import UserService, ResourceService, ReservationService
from app.auth import authenticate_user, create_access_token, get_current_user

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Resource Reservation System",
    description="A clean, scalable resource booking system",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# Authentication endpoints
@app.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
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
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Authenticate user and return access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
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
    q: Optional[str] = Query(None, description="Search query for resource names"),
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
    """Upload resources from CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a CSV"
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

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        response = {"created_count": created_count}
        if errors:
            response["errors"] = errors[:10]  # Limit to first 10 errors

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process CSV file: {str(e)}",
        )


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
        return reservation_service.create_reservation(reservation_data, current_user.id)
    except ValueError as e:
        if "conflicts" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
    return reservation_service.get_user_reservations(current_user.id, include_cancelled)


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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "only cancel your own" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )

    if reservation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    reservation_service = ReservationService(db)
    return reservation_service.get_reservation_history(reservation_id)


# Backward compatibility endpoints
@app.post(
    "/reserve", response_model=schemas.ReservationResponse, include_in_schema=False
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
