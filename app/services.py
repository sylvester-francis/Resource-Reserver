# app/services.py
"""Business logic layer with clear separation of concerns."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app import models, schemas
from app.auth import hash_password


class ResourceService:
    """Service for resource management operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_resource(self, resource_data: schemas.ResourceCreate) -> models.Resource:  # noqa :E501
        """Create a new resource."""
        resource = models.Resource(
            name=resource_data.name,
            available=resource_data.available,
            tags=resource_data.tags or [],
        )
        self.db.add(resource)
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def get_all_resources(self) -> List[models.Resource]:
        """Get all resources."""
        return self.db.query(models.Resource).all()

    def search_resources(
        self,
        query: str = None,
        available_only: bool = True,
        available_from: datetime = None,
        available_until: datetime = None,
    ) -> List[models.Resource]:
        """Search resources with optional time-based filtering."""

        # If time period specified, filter out booked resources
        if available_from and available_until:
            available_resources = []
            resources = (
                self.db.query(models.Resource).filter(models.Resource.available).all()  # noqa :E501
            )

            for resource in resources:
                if not self._has_conflict(resource.id, available_from, available_until):  # noqa :E501
                    available_resources.append(resource)

            # Apply text search if provided
            if query:
                query_lower = query.lower()
                available_resources = [
                    r
                    for r in available_resources
                    if query_lower in r.name.lower()  # noqa :E501
                ]

            return available_resources

        # Regular search without time filtering
        db_query = self.db.query(models.Resource)

        if available_only:
            db_query = db_query.filter(models.Resource.available)

        if query:
            db_query = db_query.filter(models.Resource.name.ilike(f"%{query}%"))  # noqa :E501

        return db_query.all()

    def _has_conflict(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> bool:
        """Check if resource has conflicting reservations."""
        conflict = (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.end_time > start_time,
                models.Reservation.start_time < end_time,
            )
            .first()
        )

        return conflict is not None


class ReservationService:
    """Service for reservation management operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_reservation(
        self, reservation_data: schemas.ReservationCreate, user_id: int
    ) -> models.Reservation:
        """Create a new reservation with conflict validation."""

        # Validate resource exists and is available
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == reservation_data.resource_id)
            .first()
        )

        if not resource:
            raise ValueError("Resource not found")

        if not resource.available:
            raise ValueError("Resource is not available for reservations")

        # Check for conflicts
        conflicts = self._get_conflicts(
            reservation_data.resource_id,
            reservation_data.start_time,
            reservation_data.end_time,
        )

        if conflicts:
            conflict_times = []
            for conflict in conflicts:
                conflict_times.append(
                    f"{conflict.start_time.strftime('%H:%M')} to {conflict.end_time.strftime('%H:%M')}"  # noqa :E501
                )
            raise ValueError(
                f"Time slot conflicts with existing reservations: {', '.join(conflict_times)}"  # noqa :E501
            )

        # Create reservation
        reservation = models.Reservation(
            user_id=user_id,
            resource_id=reservation_data.resource_id,
            start_time=reservation_data.start_time,
            end_time=reservation_data.end_time,
            status="active",
        )

        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)

        # Log the action
        self._log_action(
            reservation.id,
            "created",
            user_id,
            f"Reserved {resource.name} from {reservation_data.start_time} to {reservation_data.end_time}",  # noqa :E501
        )

        return reservation

    def cancel_reservation(
        self,
        reservation_id: int,
        cancellation: schemas.ReservationCancel,
        user_id: int,
    ) -> models.Reservation:
        """Cancel a reservation."""
        reservation = (
            self.db.query(models.Reservation)
            .filter(models.Reservation.id == reservation_id)
            .first()
        )

        if not reservation:
            raise ValueError("Reservation not found")

        if reservation.user_id != user_id:
            raise ValueError("You can only cancel your own reservations")

        if reservation.status == "cancelled":
            raise ValueError("Reservation is already cancelled")

        # Update reservation
        reservation.status = "cancelled"
        reservation.cancelled_at = datetime.utcnow()
        reservation.cancellation_reason = cancellation.reason

        self.db.commit()
        self.db.refresh(reservation)

        # Log the action
        reason_text = f" (Reason: {cancellation.reason})" if cancellation.reason else ""  # noqa :E501
        self._log_action(
            reservation_id,
            "cancelled",
            user_id,
            f"Cancelled reservation{reason_text}",
        )

        return reservation

    def get_user_reservations(
        self, user_id: int, include_cancelled: bool = False
    ) -> List[models.Reservation]:
        """Get reservations for a specific user."""
        query = (
            self.db.query(models.Reservation)
            .options(joinedload(models.Reservation.resource))
            .filter(models.Reservation.user_id == user_id)
        )

        if not include_cancelled:
            query = query.filter(models.Reservation.status == "active")

        return query.order_by(models.Reservation.start_time.desc()).all()

    def get_reservation_history(
        self, reservation_id: int
    ) -> List[models.ReservationHistory]:
        """Get history for a specific reservation."""
        return (
            self.db.query(models.ReservationHistory)
            .filter(models.ReservationHistory.reservation_id == reservation_id)
            .order_by(models.ReservationHistory.timestamp.desc())
            .all()
        )

    def _get_conflicts(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> List[models.Reservation]:
        """Get all conflicting reservations for a time slot."""
        return (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.end_time > start_time,
                models.Reservation.start_time < end_time,
            )
            .all()
        )

    def _log_action(self, reservation_id: int, action: str, user_id: int, details: str):  # noqa :E501
        """Log a reservation action for audit trail."""
        history = models.ReservationHistory(
            reservation_id=reservation_id,
            action=action,
            user_id=user_id,
            details=details,
        )
        self.db.add(history)
        self.db.commit()


class UserService:
    """Service for user management operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_data: schemas.UserCreate) -> models.User:
        """Create a new user with hashed password."""
        hashed_password = hash_password(user_data.password)
        user = models.User(username=user_data.username, hashed_password=hashed_password)  # noqa :E501
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_username(self, username: str) -> Optional[models.User]:
        """Get user by username."""
        return (
            self.db.query(models.User).filter(models.User.username == username).first()  # noqa :E501
        )
