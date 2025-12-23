from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=schemas.PaginatedResponse[schemas.NotificationResponse],
    status_code=status.HTTP_200_OK,
)
def list_notifications(
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort by: id, created_at, type"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    include_total: bool = Query(False, description="Include total count"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List notifications for the current user."""
    service = NotificationService(db)
    pagination = schemas.PaginationParams(
        cursor=cursor, limit=limit, sort_by=sort_by, sort_order=sort_order
    )

    try:
        notifications, next_cursor, has_more, total_count = service.list_notifications(
            user_id=current_user.id,
            pagination=pagination,
            include_total=include_total,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return schemas.PaginatedResponse(
        data=notifications,
        next_cursor=next_cursor,
        prev_cursor=None,
        has_more=has_more,
        total_count=total_count,
    )


@router.post(
    "/{notification_id}/read",
    response_model=schemas.NotificationResponse,
    status_code=status.HTTP_200_OK,
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a single notification as read."""
    service = NotificationService(db)
    try:
        notification = service.mark_as_read(notification_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return schemas.NotificationResponse.model_validate(notification)


@router.post(
    "/mark-all-read",
    status_code=status.HTTP_200_OK,
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark all notifications for the current user as read."""
    service = NotificationService(db)
    updated = service.mark_all_as_read(current_user.id)
    return {"message": "Notifications marked as read", "updated": updated}
