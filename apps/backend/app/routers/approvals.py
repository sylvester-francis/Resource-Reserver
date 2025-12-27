"""Approval workflow endpoints for resource reservations.

Provides endpoints for:
- Viewing pending approvals (for approvers)
- Approving/rejecting reservation requests
- Viewing user's own pending requests
- Managing resource approval settings

Author: Sylvester-Francis
"""

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import models, schemas
from app.approval_service import ApprovalService
from app.auth import get_current_user
from app.database import get_db
from app.services import ReservationService

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


def ensure_timezone_aware(dt):
    """Ensure datetime is timezone-aware (convert to UTC if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@router.get("/pending")
def get_pending_approvals(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all pending approval requests for the current user (as approver)."""
    service = ApprovalService(db)
    approvals = service.get_pending_approvals_for_user(current_user.id)

    result = []
    for approval in approvals:
        reservation = approval.reservation
        result.append(
            {
                "id": approval.id,
                "reservation_id": reservation.id,
                "resource_id": reservation.resource_id,
                "resource_name": reservation.resource.name
                if reservation.resource
                else None,
                "requester_id": reservation.user_id,
                "requester_username": reservation.user.username
                if reservation.user
                else None,
                "start_time": reservation.start_time.isoformat(),
                "end_time": reservation.end_time.isoformat(),
                "request_message": approval.request_message,
                "created_at": approval.created_at.isoformat(),
            }
        )

    return {"pending_approvals": result, "count": len(result)}


@router.get("/my-requests")
def get_my_pending_requests(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all pending approval requests submitted by the current user."""
    service = ApprovalService(db)
    approvals = service.get_user_pending_requests(current_user.id)

    result = []
    for approval in approvals:
        reservation = approval.reservation
        result.append(
            {
                "id": approval.id,
                "reservation_id": reservation.id,
                "resource_id": reservation.resource_id,
                "resource_name": reservation.resource.name
                if reservation.resource
                else None,
                "approver_id": approval.approver_id,
                "approver_username": approval.approver.username
                if approval.approver
                else None,
                "start_time": reservation.start_time.isoformat(),
                "end_time": reservation.end_time.isoformat(),
                "request_message": approval.request_message,
                "status": approval.status,
                "created_at": approval.created_at.isoformat(),
            }
        )

    return {"my_requests": result, "count": len(result)}


@router.get("/{approval_id}")
def get_approval_request(
    approval_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a specific approval request."""
    service = ApprovalService(db)
    approval = service.get_approval_request(approval_id)

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    reservation = approval.reservation

    # Check if user is the approver or the requester
    if (
        approval.approver_id != current_user.id
        and reservation.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view this approval request",
        )

    return {
        "id": approval.id,
        "reservation_id": reservation.id,
        "resource_id": reservation.resource_id,
        "resource_name": reservation.resource.name if reservation.resource else None,
        "requester_id": reservation.user_id,
        "requester_username": reservation.user.username if reservation.user else None,
        "approver_id": approval.approver_id,
        "approver_username": approval.approver.username if approval.approver else None,
        "start_time": reservation.start_time.isoformat(),
        "end_time": reservation.end_time.isoformat(),
        "request_message": approval.request_message,
        "response_message": approval.response_message,
        "status": approval.status,
        "created_at": approval.created_at.isoformat(),
        "responded_at": (
            approval.responded_at.isoformat() if approval.responded_at else None
        ),
    }


@router.post("/{approval_id}/respond")
def respond_to_approval(
    approval_id: int,
    action: schemas.ApprovalAction,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Approve or reject a reservation request."""
    service = ApprovalService(db)

    try:
        if action.action == "approve":
            approval = service.approve_request(
                approval_id, current_user.id, action.response_message
            )
        else:
            approval = service.reject_request(
                approval_id, current_user.id, action.response_message
            )

        return {
            "success": True,
            "message": f"Request has been {action.action}d",
            "approval_id": approval.id,
            "status": approval.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{approval_id}")
def cancel_my_request(
    approval_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cancel a pending approval request (by the requester)."""
    service = ApprovalService(db)

    try:
        approval = service.cancel_pending_request(approval_id, current_user.id)
        return {
            "success": True,
            "message": "Request cancelled",
            "approval_id": approval.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Resource approval settings endpoints
@router.get("/resources/{resource_id}/settings")
def get_resource_approval_settings(
    resource_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get approval settings for a resource."""
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    approver = None
    if resource.default_approver_id:
        approver = (
            db.query(models.User)
            .filter(models.User.id == resource.default_approver_id)
            .first()
        )

    return {
        "resource_id": resource.id,
        "resource_name": resource.name,
        "requires_approval": resource.requires_approval,
        "default_approver_id": resource.default_approver_id,
        "default_approver_username": approver.username if approver else None,
    }


@router.put("/resources/{resource_id}/settings")
def update_resource_approval_settings(
    resource_id: int,
    settings: schemas.ResourceApprovalUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update approval settings for a resource (admin only)."""
    # TODO: Add proper admin/permission check
    service = ApprovalService(db)

    try:
        resource = service.update_resource_approval_settings(
            resource_id,
            settings.requires_approval,
            settings.default_approver_id,
        )
        return {
            "success": True,
            "resource_id": resource.id,
            "requires_approval": resource.requires_approval,
            "default_approver_id": resource.default_approver_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Reservation with approval endpoint
@router.post("/reservations")
def create_reservation_with_approval(
    data: schemas.ReservationWithApprovalCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a reservation, triggering approval workflow if required."""
    # Get resource
    resource = (
        db.query(models.Resource).filter(models.Resource.id == data.resource_id).first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not resource.available:
        raise HTTPException(
            status_code=400, detail="Resource is not available for reservations"
        )

    # Ensure timezone awareness
    start_time = ensure_timezone_aware(data.start_time)
    end_time = ensure_timezone_aware(data.end_time)

    # Check for conflicts
    reservation_service = ReservationService(db)
    conflicts = reservation_service._get_conflicts(resource.id, start_time, end_time)
    if conflicts:
        raise HTTPException(
            status_code=400, detail="Time slot conflicts with existing reservations"
        )

    # Determine if approval is required
    if resource.requires_approval:
        # Determine approver
        approver_id = resource.default_approver_id
        if not approver_id:
            # If no default approver, fail
            raise HTTPException(
                status_code=400,
                detail="Resource requires approval but no approver is configured",
            )

        # Create reservation with pending_approval status
        reservation = models.Reservation(
            user_id=current_user.id,
            resource_id=resource.id,
            start_time=start_time,
            end_time=end_time,
            status="pending_approval",
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)

        # Create approval request
        approval_service = ApprovalService(db)
        approval_request = approval_service.create_approval_request(
            reservation, approver_id, data.request_message
        )

        return {
            "success": True,
            "requires_approval": True,
            "status": "pending_approval",
            "reservation_id": reservation.id,
            "approval_id": approval_request.id,
            "message": "Reservation request submitted for approval",
        }
    else:
        # No approval required - create reservation directly
        reservation_data = schemas.ReservationCreate(
            resource_id=resource.id,
            start_time=start_time,
            end_time=end_time,
        )
        reservation = reservation_service.create_reservation(
            reservation_data, current_user.id
        )

        return {
            "success": True,
            "requires_approval": False,
            "status": "active",
            "reservation_id": reservation.id,
            "message": "Reservation created successfully",
        }
