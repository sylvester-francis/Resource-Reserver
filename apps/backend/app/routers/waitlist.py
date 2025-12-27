"""Waitlist endpoints for resource availability alerts."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services import WaitlistService

router = APIRouter(prefix="/api/v1/waitlist", tags=["Waitlist"])


@router.post(
    "",
    response_model=schemas.WaitlistResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_waitlist(
    waitlist_data: schemas.WaitlistCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Join the waitlist for a resource time slot."""
    service = WaitlistService(db)
    try:
        entry = service.join_waitlist(waitlist_data, current_user.id)
        return schemas.WaitlistResponse.model_validate(entry)
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get(
    "",
    response_model=schemas.PaginatedResponse[schemas.WaitlistWithResourceResponse],
    status_code=status.HTTP_200_OK,
)
def list_my_waitlist_entries(
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(
        "created_at", description="Sort by: id, created_at, position, desired_start"
    ),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    include_completed: bool = Query(False, description="Include completed entries"),
    include_total: bool = Query(False, description="Include total count"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List waitlist entries for the current user."""
    service = WaitlistService(db)
    pagination = schemas.PaginationParams(
        cursor=cursor, limit=limit, sort_by=sort_by, sort_order=sort_order
    )

    try:
        entries, next_cursor, has_more, total_count = service.get_user_waitlist_entries(
            user_id=current_user.id,
            pagination=pagination,
            include_completed=include_completed,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return schemas.PaginatedResponse(
        data=[schemas.WaitlistWithResourceResponse.model_validate(e) for e in entries],
        next_cursor=next_cursor,
        prev_cursor=None,
        has_more=has_more,
        total_count=total_count,
    )


@router.get(
    "/{waitlist_id}",
    response_model=schemas.WaitlistWithResourceResponse,
    status_code=status.HTTP_200_OK,
)
def get_waitlist_entry(
    waitlist_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get details of a specific waitlist entry."""
    service = WaitlistService(db)
    entry = service.get_waitlist_entry(waitlist_id)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found"
        )

    if entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own waitlist entries",
        )

    return schemas.WaitlistWithResourceResponse.model_validate(entry)


@router.delete(
    "/{waitlist_id}",
    status_code=status.HTTP_200_OK,
)
def leave_waitlist(
    waitlist_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Leave the waitlist (cancel a waitlist entry)."""
    service = WaitlistService(db)
    try:
        entry = service.leave_waitlist(waitlist_id, current_user.id)
        return {
            "message": "Successfully left the waitlist",
            "waitlist_id": entry.id,
            "status": entry.status,
        }
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post(
    "/{waitlist_id}/accept",
    response_model=schemas.ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def accept_waitlist_offer(
    waitlist_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Accept a waitlist offer and create a reservation."""
    service = WaitlistService(db)
    try:
        reservation = service.accept_offer(waitlist_id, current_user.id)
        return schemas.ReservationResponse.model_validate(reservation)
    except ValueError as exc:
        error_str = str(exc).lower()
        if "not found" in error_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        if "expired" in error_str:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(exc)
            ) from exc
        if "no active offer" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get(
    "/resource/{resource_id}",
    response_model=list[schemas.WaitlistResponse],
    status_code=status.HTTP_200_OK,
)
def get_resource_waitlist(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the waitlist for a specific resource (shows positions only)."""
    service = WaitlistService(db)
    entries = service.get_waitlist_for_resource(resource_id)
    return [schemas.WaitlistResponse.model_validate(e) for e in entries]
