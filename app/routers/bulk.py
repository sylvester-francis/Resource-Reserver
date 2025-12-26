"""Bulk operations endpoints for reservations.

Provides endpoints for:
- Bulk create reservations
- Bulk cancel reservations
- CSV import/export
- Dry-run validation

Author: Sylvester-Francis
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.bulk_service import BulkReservationService
from app.database import get_db

router = APIRouter(prefix="/api/v1/bulk", tags=["bulk"])


def ensure_timezone_aware(dt):
    """Ensure datetime is timezone-aware (convert to UTC if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class BulkReservationItem(BaseModel):
    """Single reservation item for bulk create."""

    resource_id: int
    start_time: datetime
    end_time: datetime


class BulkCreateRequest(BaseModel):
    """Request body for bulk reservation creation."""

    reservations: list[BulkReservationItem] = Field(..., min_length=1, max_length=100)
    dry_run: bool = Field(False, description="Validate only without creating")


class BulkCancelRequest(BaseModel):
    """Request body for bulk reservation cancellation."""

    reservation_ids: list[int] = Field(..., min_length=1, max_length=100)
    reason: str | None = Field(None, max_length=500)


@router.post("/reservations")
def bulk_create_reservations(
    data: BulkCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create multiple reservations in bulk.

    - Maximum 100 reservations per request
    - Use dry_run=true to validate without creating
    - All reservations succeed or all fail (atomic)
    """
    service = BulkReservationService(db)

    # Convert to dict format
    reservations_data = [
        {
            "resource_id": r.resource_id,
            "start_time": ensure_timezone_aware(r.start_time),
            "end_time": ensure_timezone_aware(r.end_time),
        }
        for r in data.reservations
    ]

    results = service.bulk_create_reservations(
        reservations_data,
        current_user.id,
        dry_run=data.dry_run,
    )

    return results


@router.post("/reservations/cancel")
def bulk_cancel_reservations(
    data: BulkCancelRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cancel multiple reservations in bulk.

    - Maximum 100 reservations per request
    - Can only cancel own reservations (unless admin)
    """
    service = BulkReservationService(db)

    results = service.bulk_cancel_reservations(
        data.reservation_ids,
        current_user.id,
        reason=data.reason,
    )

    return results


@router.post("/reservations/import")
async def import_reservations_csv(
    request: Request,
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="Validate only without creating"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Import reservations from CSV file.

    Expected CSV columns:
    - resource_id (or resource_name)
    - start_time (ISO format or YYYY-MM-DD HH:MM)
    - end_time (ISO format or YYYY-MM-DD HH:MM)

    Example:
    ```
    resource_id,start_time,end_time
    1,2024-01-15 09:00,2024-01-15 10:00
    2,2024-01-15 10:00,2024-01-15 11:00
    ```
    """
    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file",
        )

    # Read file content
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail="File must be UTF-8 encoded",
        ) from e

    # Check file size (max 1MB)
    if len(content) > 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 1MB limit",
        )

    service = BulkReservationService(db)
    results = service.import_from_csv(csv_content, current_user.id, dry_run=dry_run)

    return results


@router.get("/reservations/export")
def export_reservations_csv(
    request: Request,
    user_id: int | None = Query(None, description="Filter by user ID"),
    resource_id: int | None = Query(None, description="Filter by resource ID"),
    start_from: datetime | None = Query(
        None, description="Filter by start time (from)"
    ),
    start_until: datetime | None = Query(
        None, description="Filter by start time (until)"
    ),
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Export reservations to CSV file.

    Supports filtering by user, resource, date range, and status.
    """
    service = BulkReservationService(db)

    csv_content = service.export_to_csv(
        user_id=user_id,
        resource_id=resource_id,
        start_from=ensure_timezone_aware(start_from),
        start_until=ensure_timezone_aware(start_until),
        status=status,
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reservations_export.csv"},
    )


@router.post("/reservations/validate")
def validate_bulk_reservations(
    data: BulkCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Validate bulk reservations without creating them.

    Equivalent to dry_run=true but more explicit.
    """
    service = BulkReservationService(db)

    reservations_data = [
        {
            "resource_id": r.resource_id,
            "start_time": ensure_timezone_aware(r.start_time),
            "end_time": ensure_timezone_aware(r.end_time),
        }
        for r in data.reservations
    ]

    results = service.bulk_create_reservations(
        reservations_data,
        current_user.id,
        dry_run=True,
    )

    return {
        "valid": results["failed"] == 0,
        "total": results["total"],
        "would_create": results["success"],
        "errors": results["errors"],
    }
