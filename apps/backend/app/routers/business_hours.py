"""Business hours and availability management endpoints.

This module provides RESTful API endpoints for managing business hours,
blackout dates, and available time slots for resources in the reservation
system. It supports both resource-specific and global configurations.

Features:
    - Resource-specific business hours management (CRUD operations)
    - Global default business hours that apply to all resources
    - Blackout date management for blocking reservations on specific dates
    - Available time slot calculation based on business hours and existing
      reservations
    - Next available slot finder for quick scheduling

Example Usage:
    To get business hours for a resource::

        GET /api/v1/resources/1/business-hours

    To set global business hours::

        PUT /api/v1/business-hours/global
        {
            "hours": [
                {"day_of_week": 0, "open_time": "09:00", "close_time": "17:00"},
                {"day_of_week": 1, "open_time": "09:00", "close_time": "17:00"}
            ]
        }

    To find available slots for a date::

        GET /api/v1/resources/1/available-slots?date=2024-01-15&slot_duration=30

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
    """Retrieve business hours configuration for a specific resource.

    Fetches the complete business hours schedule for a resource, including
    operating hours for each day of the week. If no resource-specific hours
    are configured, returns an empty list.

    Args:
        resource_id: The unique identifier of the resource to query.
        db: Database session dependency for querying the database.
        _: Current authenticated user (unused but required for auth).

    Returns:
        list[schemas.BusinessHoursResponse]: A list of business hours entries,
            each containing day_of_week, open_time, and close_time fields.

    Raises:
        HTTPException: 404 error if the specified resource does not exist.
    """
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
    """Set or update business hours for a specific resource.

    Replaces the existing business hours configuration for the specified
    resource with the provided schedule. This operation requires admin
    privileges.

    Args:
        resource_id: The unique identifier of the resource to update.
        hours_data: Bulk update payload containing the new business hours
            schedule with entries for each operating day.
        db: Database session dependency for database operations.
        current_user: The authenticated user making the request.

    Returns:
        list[schemas.BusinessHoursResponse]: The newly configured business
            hours entries for the resource.

    Raises:
        HTTPException: 403 error if the user lacks admin permissions.
        HTTPException: 404 error if the specified resource does not exist.
    """
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
    """Retrieve the global default business hours configuration.

    Fetches the system-wide default business hours that apply to resources
    without their own specific business hours configuration.

    Args:
        db: Database session dependency for querying the database.
        _: Current authenticated user (unused but required for auth).

    Returns:
        list[schemas.BusinessHoursResponse]: A list of global business hours
            entries, each containing day_of_week, open_time, and close_time.
    """
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
    """Set or update the global default business hours.

    Replaces the system-wide default business hours configuration with the
    provided schedule. These defaults apply to all resources that do not
    have their own specific business hours configured. This operation
    requires admin privileges.

    Args:
        hours_data: Bulk update payload containing the new global business
            hours schedule with entries for each operating day.
        db: Database session dependency for database operations.
        current_user: The authenticated user making the request.

    Returns:
        list[schemas.BusinessHoursResponse]: The newly configured global
            business hours entries.

    Raises:
        HTTPException: 403 error if the user lacks admin permissions.
    """
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
    """Get available time slots for a resource on a specific date.

    Calculates and returns all available time slots for the specified
    resource on the given date. Availability is determined based on
    business hours, existing reservations, and blackout dates.

    Args:
        resource_id: The unique identifier of the resource to query.
        target_date: The date to check for availability (YYYY-MM-DD format).
        slot_duration: Duration of each time slot in minutes. Must be
            between 15 and 480 minutes. Defaults to 30 minutes.
        db: Database session dependency for database queries.
        _: Current authenticated user (unused but required for auth).

    Returns:
        schemas.AvailableSlotsResponse: Response containing the date queried
            and a list of available time slots with start and end times.

    Raises:
        HTTPException: 404 error if the specified resource does not exist.
    """
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
    """Find the next available time slot for a resource.

    Searches for the earliest available time slot that can accommodate
    the specified duration, starting from the current time and looking
    ahead for the specified number of days.

    Args:
        resource_id: The unique identifier of the resource to query.
        slot_duration: Required duration of the time slot in minutes.
            Must be between 15 and 480 minutes. Defaults to 30 minutes.
        days_ahead: Maximum number of days to search into the future.
            Must be between 1 and 60 days. Defaults to 14 days.
        db: Database session dependency for database queries.
        _: Current authenticated user (unused but required for auth).

    Returns:
        schemas.TimeSlot | None: The next available time slot with start
            and end times, or None if no slot is available within the
            search window.

    Raises:
        HTTPException: 404 error if the specified resource does not exist.
    """
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
    """Retrieve blackout dates for a specific resource.

    Fetches all dates when the specified resource is unavailable for
    reservations. Optionally includes global blackout dates that apply
    to all resources.

    Args:
        resource_id: The unique identifier of the resource to query.
        include_global: Whether to include system-wide blackout dates
            in the response. Defaults to True.
        db: Database session dependency for database queries.
        _: Current authenticated user (unused but required for auth).

    Returns:
        list[schemas.BlackoutDateResponse]: A list of blackout date entries,
            each containing the date, reason, and whether it is global.

    Raises:
        HTTPException: 404 error if the specified resource does not exist.
    """
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
    """Add a blackout date for a specific resource.

    Creates a new blackout date entry that prevents reservations for the
    specified resource on the given date. This operation requires admin
    privileges.

    Args:
        resource_id: The unique identifier of the resource to update.
        blackout_data: Blackout date creation payload containing the date
            and optional reason for the blackout.
        db: Database session dependency for database operations.
        current_user: The authenticated user making the request.

    Returns:
        schemas.BlackoutDateResponse: The newly created blackout date entry.

    Raises:
        HTTPException: 403 error if the user lacks admin permissions.
        HTTPException: 404 error if the specified resource does not exist.
    """
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
    """Retrieve all global blackout dates.

    Fetches all system-wide blackout dates that apply to all resources.
    These dates prevent reservations across the entire system regardless
    of individual resource configurations.

    Args:
        db: Database session dependency for database queries.
        _: Current authenticated user (unused but required for auth).

    Returns:
        list[schemas.BlackoutDateResponse]: A list of global blackout date
            entries, each containing the date and reason for the blackout.
    """
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
    """Add a global blackout date.

    Creates a new system-wide blackout date that prevents reservations
    for all resources on the specified date. This operation requires
    admin privileges.

    Args:
        blackout_data: Blackout date creation payload containing the date
            and optional reason for the blackout.
        db: Database session dependency for database operations.
        current_user: The authenticated user making the request.

    Returns:
        schemas.BlackoutDateResponse: The newly created global blackout
            date entry.

    Raises:
        HTTPException: 403 error if the user lacks admin permissions.
    """
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
    """Remove a blackout date.

    Deletes an existing blackout date entry, re-enabling reservations
    for that date. This operation works for both resource-specific and
    global blackout dates. Requires admin privileges.

    Args:
        blackout_id: The unique identifier of the blackout date to remove.
        db: Database session dependency for database operations.
        current_user: The authenticated user making the request.

    Returns:
        None: Returns no content on successful deletion (HTTP 204).

    Raises:
        HTTPException: 403 error if the user lacks admin permissions.
        HTTPException: 404 error if the blackout date does not exist.
    """
    # Check admin permission
    if not check_permission(current_user, resource="resource", action="delete", db=db):
        raise HTTPException(status_code=403, detail="Admin access required")

    service = AvailabilityService(db)
    if not service.remove_blackout_date(blackout_id):
        raise HTTPException(status_code=404, detail="Blackout date not found")
