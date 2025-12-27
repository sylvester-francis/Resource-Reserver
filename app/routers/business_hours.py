"""Business hours and availability management endpoints.

Provides endpoints for:
- Managing business hours for resources
- Managing blackout dates
- Getting available time slots

Author: Sylvester-Francis
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.availability_service import AvailabilityService
from app.database import get_db
from app.rbac import check_permission

router = APIRouter(prefix="/api/v1", tags=["business-hours"])


# ============================================================================
# Business Hours Endpoints
# ============================================================================


@router.get(
    "/resources/{resource_id}/business-hours",
    response_model=list[schemas.BusinessHoursResponse],
)
async def get_resource_business_hours(
    resource_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Get business hours for a specific resource."""
    # Verify resource exists
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    service = AvailabilityService(db)
    hours = service.get_all_business_hours(resource_id)
    return hours


@router.put(
    "/resources/{resource_id}/business-hours",
    response_model=list[schemas.BusinessHoursResponse],
)
async def set_resource_business_hours(
    resource_id: int,
    hours_data: schemas.BusinessHoursBulkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Set business hours for a resource. Admin only."""
    # Check admin permission
    if not check_permission(current_user, resource="resource", action="update", db=db):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Verify resource exists
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    service = AvailabilityService(db)
    hours = service.set_business_hours(resource_id, hours_data)
    return hours


@router.get(
    "/business-hours/global",
    response_model=list[schemas.BusinessHoursResponse],
)
async def get_global_business_hours(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Get global default business hours."""
    service = AvailabilityService(db)
    hours = service.get_all_business_hours(None)
    return hours


@router.put(
    "/business-hours/global",
    response_model=list[schemas.BusinessHoursResponse],
)
async def set_global_business_hours(
    hours_data: schemas.BusinessHoursBulkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Set global default business hours. Admin only."""
    # Check admin permission
    if not check_permission(current_user, resource="resource", action="update", db=db):
        raise HTTPException(status_code=403, detail="Admin access required")

    service = AvailabilityService(db)
    hours = service.set_business_hours(None, hours_data)
    return hours


# ============================================================================
# Available Slots Endpoints
# ============================================================================


@router.get(
    "/resources/{resource_id}/available-slots",
    response_model=schemas.AvailableSlotsResponse,
)
async def get_available_slots(
    resource_id: int,
    target_date: date = Query(
        ..., alias="date", description="Date in YYYY-MM-DD format"
    ),
    slot_duration: int = Query(
        30, ge=15, le=480, description="Slot duration in minutes"
    ),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Get available time slots for a resource on a specific date."""
    # Verify resource exists
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    service = AvailabilityService(db)
    return service.get_available_slots(resource_id, target_date, slot_duration)


@router.get(
    "/resources/{resource_id}/next-available",
    response_model=schemas.TimeSlot | None,
)
async def get_next_available_slot(
    resource_id: int,
    slot_duration: int = Query(
        30, ge=15, le=480, description="Slot duration in minutes"
    ),
    days_ahead: int = Query(14, ge=1, le=60, description="Days to search ahead"),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Find the next available time slot for a resource."""
    # Verify resource exists
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    service = AvailabilityService(db)
    return service.get_next_available_slot(resource_id, slot_duration, days_ahead)


# ============================================================================
# Blackout Date Endpoints
# ============================================================================


@router.get(
    "/resources/{resource_id}/blackout-dates",
    response_model=list[schemas.BlackoutDateResponse],
)
async def get_resource_blackout_dates(
    resource_id: int,
    include_global: bool = Query(True, description="Include global blackout dates"),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Get blackout dates for a resource."""
    # Verify resource exists
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    service = AvailabilityService(db)
    return service.get_blackout_dates(resource_id, include_global)


@router.post(
    "/resources/{resource_id}/blackout-dates",
    response_model=schemas.BlackoutDateResponse,
    status_code=201,
)
async def add_resource_blackout_date(
    resource_id: int,
    blackout_data: schemas.BlackoutDateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a blackout date for a resource. Admin only."""
    # Check admin permission
    if not check_permission(current_user, resource="resource", action="update", db=db):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Verify resource exists
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    service = AvailabilityService(db)
    return service.add_blackout_date(resource_id, blackout_data)


@router.get(
    "/blackout-dates",
    response_model=list[schemas.BlackoutDateResponse],
)
async def get_global_blackout_dates(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Get global blackout dates."""
    service = AvailabilityService(db)
    return service.get_blackout_dates(None)


@router.post(
    "/blackout-dates",
    response_model=schemas.BlackoutDateResponse,
    status_code=201,
)
async def add_global_blackout_date(
    blackout_data: schemas.BlackoutDateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a global blackout date. Admin only."""
    # Check admin permission
    if not check_permission(current_user, resource="resource", action="update", db=db):
        raise HTTPException(status_code=403, detail="Admin access required")

    service = AvailabilityService(db)
    return service.add_blackout_date(None, blackout_data)


@router.delete("/blackout-dates/{blackout_id}", status_code=204)
async def remove_blackout_date(
    blackout_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove a blackout date. Admin only."""
    # Check admin permission
    if not check_permission(current_user, resource="resource", action="delete", db=db):
        raise HTTPException(status_code=403, detail="Admin access required")

    service = AvailabilityService(db)
    if not service.remove_blackout_date(blackout_id):
        raise HTTPException(status_code=404, detail="Blackout date not found")
