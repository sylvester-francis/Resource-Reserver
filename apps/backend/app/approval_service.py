"""Approval workflow service for resource reservations.

Handles the approval workflow for resources that require approval before
reservations can be confirmed.

Author: Sylvester-Francis
"""

import logging
from datetime import UTC, datetime

import anyio
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.services import NotificationService
from app.websocket import manager as ws_manager

logger = logging.getLogger(__name__)


def utcnow():
    """Get current UTC datetime that's timezone-aware."""
    return datetime.now(UTC)


class ApprovalService:
    """Service for managing approval workflows."""

    def __init__(self, db: Session):
        self.db = db

    def create_approval_request(
        self,
        reservation: models.Reservation,
        approver_id: int,
        request_message: str | None = None,
    ) -> models.ApprovalRequest:
        """Create an approval request for a reservation."""
        # Verify approver exists
        approver = (
            self.db.query(models.User).filter(models.User.id == approver_id).first()
        )
        if not approver:
            raise ValueError("Approver not found")

        # Create approval request
        approval_request = models.ApprovalRequest(
            reservation_id=reservation.id,
            approver_id=approver_id,
            status="pending",
            request_message=request_message,
        )

        self.db.add(approval_request)
        self.db.commit()
        self.db.refresh(approval_request)

        # Notify approver
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == reservation.resource_id)
            .first()
        )
        requester = (
            self.db.query(models.User)
            .filter(models.User.id == reservation.user_id)
            .first()
        )

        NotificationService(self.db).create_notification(
            user_id=approver_id,
            type=schemas.NotificationType.SYSTEM_ANNOUNCEMENT,
            title="Approval Request",
            message=f"{requester.username if requester else 'User'} is requesting to "
            f"reserve {resource.name if resource else 'a resource'}",
            link=f"/approvals/{approval_request.id}",
        )

        # Broadcast to approver via WebSocket
        try:
            anyio.from_thread.run(
                ws_manager.broadcast_to_user,
                approver_id,
                {
                    "type": "approval_request",
                    "approval_id": approval_request.id,
                    "reservation_id": reservation.id,
                    "resource_name": resource.name if resource else "Resource",
                    "requester": requester.username if requester else "Unknown",
                },
            )
        except Exception as exc:
            logger.warning(
                "Failed to broadcast approval request to user %s: %s",
                approver_id,
                exc,
            )

        return approval_request

    def get_pending_approvals_for_user(
        self, user_id: int
    ) -> list[models.ApprovalRequest]:
        """Get all pending approval requests where user is the approver."""
        return (
            self.db.query(models.ApprovalRequest)
            .options(
                joinedload(models.ApprovalRequest.reservation).joinedload(
                    models.Reservation.resource
                ),
                joinedload(models.ApprovalRequest.reservation).joinedload(
                    models.Reservation.user
                ),
            )
            .filter(
                models.ApprovalRequest.approver_id == user_id,
                models.ApprovalRequest.status == "pending",
            )
            .order_by(models.ApprovalRequest.created_at.desc())
            .all()
        )

    def get_approval_request(self, approval_id: int) -> models.ApprovalRequest | None:
        """Get a specific approval request with related data."""
        return (
            self.db.query(models.ApprovalRequest)
            .options(
                joinedload(models.ApprovalRequest.reservation).joinedload(
                    models.Reservation.resource
                ),
                joinedload(models.ApprovalRequest.reservation).joinedload(
                    models.Reservation.user
                ),
                joinedload(models.ApprovalRequest.approver),
            )
            .filter(models.ApprovalRequest.id == approval_id)
            .first()
        )

    def approve_request(
        self,
        approval_id: int,
        approver_id: int,
        response_message: str | None = None,
    ) -> models.ApprovalRequest:
        """Approve a reservation request."""
        approval_request = self.get_approval_request(approval_id)
        if not approval_request:
            raise ValueError("Approval request not found")

        if approval_request.approver_id != approver_id:
            raise ValueError("You are not the designated approver for this request")

        if approval_request.status != "pending":
            raise ValueError(f"Request has already been {approval_request.status}")

        # Update approval request
        approval_request.status = "approved"
        approval_request.response_message = response_message
        approval_request.responded_at = utcnow()

        # Update reservation status to active
        reservation = approval_request.reservation
        reservation.status = "active"

        self.db.commit()
        self.db.refresh(approval_request)

        # Notify requester
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == reservation.resource_id)
            .first()
        )

        NotificationService(self.db).create_notification(
            user_id=reservation.user_id,
            type=schemas.NotificationType.RESERVATION_CONFIRMED,
            title="Reservation Approved",
            message=f"Your reservation for {resource.name if resource else 'resource'} "
            f"has been approved!",
            link=f"/reservations/{reservation.id}",
        )

        # Broadcast to requester via WebSocket
        try:
            anyio.from_thread.run(
                ws_manager.broadcast_to_user,
                reservation.user_id,
                {
                    "type": "reservation_approved",
                    "reservation_id": reservation.id,
                    "approval_id": approval_request.id,
                    "resource_name": resource.name if resource else "Resource",
                },
            )
        except Exception as exc:
            logger.warning(
                "Failed to broadcast approval notification to user %s: %s",
                reservation.user_id,
                exc,
            )

        return approval_request

    def reject_request(
        self,
        approval_id: int,
        approver_id: int,
        response_message: str | None = None,
    ) -> models.ApprovalRequest:
        """Reject a reservation request."""
        approval_request = self.get_approval_request(approval_id)
        if not approval_request:
            raise ValueError("Approval request not found")

        if approval_request.approver_id != approver_id:
            raise ValueError("You are not the designated approver for this request")

        if approval_request.status != "pending":
            raise ValueError(f"Request has already been {approval_request.status}")

        # Update approval request
        approval_request.status = "rejected"
        approval_request.response_message = response_message
        approval_request.responded_at = utcnow()

        # Update reservation status to rejected
        reservation = approval_request.reservation
        reservation.status = "rejected"

        self.db.commit()
        self.db.refresh(approval_request)

        # Notify requester
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == reservation.resource_id)
            .first()
        )

        rejection_reason = ""
        if response_message:
            rejection_reason = f" Reason: {response_message}"

        NotificationService(self.db).create_notification(
            user_id=reservation.user_id,
            type=schemas.NotificationType.RESERVATION_CANCELLED,
            title="Reservation Rejected",
            message=f"Your reservation for {resource.name if resource else 'resource'} "
            f"was rejected.{rejection_reason}",
            link=f"/reservations/{reservation.id}",
        )

        # Broadcast to requester via WebSocket
        try:
            anyio.from_thread.run(
                ws_manager.broadcast_to_user,
                reservation.user_id,
                {
                    "type": "reservation_rejected",
                    "reservation_id": reservation.id,
                    "approval_id": approval_request.id,
                    "resource_name": resource.name if resource else "Resource",
                    "reason": response_message,
                },
            )
        except Exception as exc:
            logger.warning(
                "Failed to broadcast rejection notification to user %s: %s",
                reservation.user_id,
                exc,
            )

        return approval_request

    def get_user_pending_requests(self, user_id: int) -> list[models.ApprovalRequest]:
        """Get all pending approval requests submitted by a user."""
        return (
            self.db.query(models.ApprovalRequest)
            .join(models.Reservation)
            .options(
                joinedload(models.ApprovalRequest.reservation).joinedload(
                    models.Reservation.resource
                ),
                joinedload(models.ApprovalRequest.approver),
            )
            .filter(
                models.Reservation.user_id == user_id,
                models.ApprovalRequest.status == "pending",
            )
            .order_by(models.ApprovalRequest.created_at.desc())
            .all()
        )

    def cancel_pending_request(
        self, approval_id: int, user_id: int
    ) -> models.ApprovalRequest:
        """Cancel a pending approval request (by the requester)."""
        approval_request = self.get_approval_request(approval_id)
        if not approval_request:
            raise ValueError("Approval request not found")

        reservation = approval_request.reservation
        if reservation.user_id != user_id:
            raise ValueError("You can only cancel your own requests")

        if approval_request.status != "pending":
            raise ValueError(f"Request has already been {approval_request.status}")

        # Update both the approval request and reservation
        approval_request.status = "rejected"
        approval_request.response_message = "Cancelled by requester"
        approval_request.responded_at = utcnow()

        reservation.status = "cancelled"
        reservation.cancelled_at = utcnow()
        reservation.cancellation_reason = "Cancelled pending approval"

        self.db.commit()
        self.db.refresh(approval_request)

        return approval_request

    def update_resource_approval_settings(
        self,
        resource_id: int,
        requires_approval: bool,
        default_approver_id: int | None = None,
    ) -> models.Resource:
        """Update approval settings for a resource."""
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )
        if not resource:
            raise ValueError("Resource not found")

        # Validate approver if provided
        if default_approver_id is not None:
            approver = (
                self.db.query(models.User)
                .filter(models.User.id == default_approver_id)
                .first()
            )
            if not approver:
                raise ValueError("Default approver not found")

        resource.requires_approval = requires_approval
        resource.default_approver_id = default_approver_id

        self.db.commit()
        self.db.refresh(resource)

        return resource
