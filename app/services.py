# app/services.py - Updated with timezone-aware datetime handling

"""Business logic layer with clear separation of concerns."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import hash_password


def ensure_timezone_aware(dt):
    """Ensure datetime is timezone-aware (convert to UTC if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If naive, assume it's UTC
        return dt.replace(tzinfo=UTC)
    return dt


def utcnow():
    """Get current UTC datetime that's timezone-aware."""
    return datetime.now(UTC)


class ResourceService:
    """Service for resource management operations with dynamic availability."""

    def __init__(self, db: Session):
        self.db = db

    def create_resource(self, resource_data: schemas.ResourceCreate) -> models.Resource:
        resource = models.Resource(
            name=resource_data.name,
            available=resource_data.available,
            tags=resource_data.tags or [],
        )
        try:
            self.db.add(resource)
            self.db.commit()
            self.db.refresh(resource)
            return resource
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Resource '{resource_data.name}' already exists.") from e

    def get_all_resources(self) -> list[models.Resource]:
        """Get all resources with real-time availability status."""
        resources = self.db.query(models.Resource).all()

        # Update availability status based on current reservations
        for resource in resources:
            resource.available = self._is_resource_currently_available(resource.id)

        return resources

    def search_resources(
        self,
        query: str = None,
        available_only: bool = True,
        available_from: datetime = None,
        available_until: datetime = None,
    ) -> list[models.Resource]:
        """Search resources with optional time-based filtering and real-time availability."""

        # Ensure timezone awareness for datetime parameters
        if available_from:
            available_from = ensure_timezone_aware(available_from)
        if available_until:
            available_until = ensure_timezone_aware(available_until)

        # If time period specified, filter out booked resources
        if available_from and available_until:
            available_resources = []

            # Get all resources that are not permanently disabled
            resources = (
                self.db.query(models.Resource)
                .filter(models.Resource.available)  # Only include enabled resources
                .all()
            )

            for resource in resources:
                if not self._has_conflict(resource.id, available_from, available_until):
                    # Set dynamic availability for the response
                    resource.available = True
                    available_resources.append(resource)

            # Apply text search if provided
            if query:
                query_lower = query.lower()
                available_resources = [
                    r for r in available_resources if query_lower in r.name.lower()
                ]

            return available_resources

        # Regular search without time filtering
        db_query = self.db.query(models.Resource)

        # Get base resources
        resources = db_query.all()

        # Update real-time availability for each resource
        filtered_resources = []
        for resource in resources:
            # Check real-time availability
            is_currently_available = self._is_resource_currently_available(resource.id)

            # Apply availability filter
            if available_only and not is_currently_available:
                continue

            # Apply text search filter
            if query:
                query_lower = query.lower()
                if not (
                    query_lower in resource.name.lower()
                    or any(query_lower in tag.lower() for tag in resource.tags)
                ):
                    continue

            # Set dynamic availability status
            resource.available = is_currently_available
            filtered_resources.append(resource)

        return filtered_resources

    def _is_resource_currently_available(self, resource_id: int) -> bool:
        """Check if a resource is currently available (not in an active reservation)."""
        now = utcnow()

        # Check if resource has any active reservations right now
        current_reservation = (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.start_time <= now,
                models.Reservation.end_time > now,
            )
            .first()
        )

        # Also check the base availability setting
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            return False

        # Resource is available if:
        # 1. It's not disabled (base available = True)
        # 2. It's not currently reserved
        return resource.available and current_reservation is None

    def _has_conflict(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> bool:
        """Check if resource has conflicting reservations during specified time period."""
        # Ensure timezone awareness
        start_time = ensure_timezone_aware(start_time)
        end_time = ensure_timezone_aware(end_time)

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

    def update_resource_availability(
        self, resource_id: int, available: bool
    ) -> models.Resource:
        """Manually update resource base availability (for maintenance, etc.)."""
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            raise ValueError("Resource not found")

        resource.available = available
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def get_resource_availability_schedule(
        self, resource_id: int, days_ahead: int = 7
    ) -> dict:
        """Get detailed availability schedule for a resource."""
        now = utcnow()
        end_date = now + timedelta(days=days_ahead)

        # Get the resource
        resource = (
            self.db.query(models.Resource)
            .filter(models.Resource.id == resource_id)
            .first()
        )

        if not resource:
            raise ValueError("Resource not found")

        # Get all reservations for this resource in the time period
        reservations = (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.start_time < end_date,
                models.Reservation.end_time > now,
            )
            .order_by(models.Reservation.start_time)
            .all()
        )

        # Generate 7-day schedule with hourly time slots
        schedule = []
        for day_offset in range(days_ahead):
            current_date = (now + timedelta(days=day_offset)).date()

            # Generate time slots for each day (9 AM to 5 PM)
            time_slots = []
            for hour in range(9, 17):  # 9 AM to 4 PM (last slot is 4-5 PM)
                slot_time = f"{hour:02d}:00"
                # Create timezone-aware slot times in UTC
                slot_datetime_start = datetime.combine(
                    current_date, datetime.min.time(), tzinfo=UTC
                ) + timedelta(hours=hour)
                slot_datetime_end = slot_datetime_start + timedelta(hours=1)

                # Check if this time slot conflicts with any reservation
                is_available = True
                if not resource.available:  # Base availability check
                    is_available = False
                else:
                    for res in reservations:
                        # Ensure database times are timezone-aware (assume they're UTC)
                        res_start = res.start_time
                        res_end = res.end_time
                        
                        # If database times are timezone-naive, assume they're UTC
                        if res_start.tzinfo is None:
                            res_start = res_start.replace(tzinfo=UTC)
                        if res_end.tzinfo is None:
                            res_end = res_end.replace(tzinfo=UTC)
                        
                        # Check overlap: slot overlaps if slot_start < res_end AND slot_end > res_start
                        if (
                            slot_datetime_start < res_end
                            and slot_datetime_end > res_start
                        ):
                            is_available = False
                            break

                time_slots.append({"time": slot_time, "available": is_available})

            schedule.append(
                {"date": current_date.isoformat(), "time_slots": time_slots}
            )

        return {
            "success": True,
            "data": {
                "resource_id": resource_id,
                "resource_name": resource.name,
                "current_time": now.isoformat(),
                "is_currently_available": self._is_resource_currently_available(
                    resource_id
                ),
                "base_available": resource.available,
                "schedule": schedule,
                "reservations": [
                    {
                        "id": res.id,
                        "start_time": res.start_time.isoformat(),
                        "end_time": res.end_time.isoformat(),
                        "user_id": res.user_id,
                        "status": res.status,
                    }
                    for res in reservations
                ],
            },
        }


class ReservationService:
    """Service for reservation management operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_reservation(
        self, reservation_data: schemas.ReservationCreate, user_id: int
    ) -> models.Reservation:
        """Create a new reservation with conflict validation."""

        # Ensure timezone awareness
        start_time = ensure_timezone_aware(reservation_data.start_time)
        end_time = ensure_timezone_aware(reservation_data.end_time)

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
            start_time,
            end_time,
        )

        if conflicts:
            conflict_times = []
            for conflict in conflicts:
                conflict_times.append(
                    f"{conflict.start_time.strftime('%H:%M')} to {conflict.end_time.strftime('%H:%M')}"
                )
            raise ValueError(
                f"Time slot conflicts with existing reservations: {', '.join(conflict_times)}"
            )

        # Create reservation
        reservation = models.Reservation(
            user_id=user_id,
            resource_id=reservation_data.resource_id,
            start_time=start_time,
            end_time=end_time,
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
            f"Reserved {resource.name} from {start_time} to {end_time}",
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
        reservation.cancelled_at = utcnow()
        reservation.cancellation_reason = cancellation.reason

        self.db.commit()
        self.db.refresh(reservation)

        # Log the action
        reason_text = f" (Reason: {cancellation.reason})" if cancellation.reason else ""
        self._log_action(
            reservation_id,
            "cancelled",
            user_id,
            f"Cancelled reservation{reason_text}",
        )

        return reservation

    def get_user_reservations(
        self, user_id: int, include_cancelled: bool = False
    ) -> list[models.Reservation]:
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
    ) -> list[models.ReservationHistory]:
        """Get history for a specific reservation."""
        return (
            self.db.query(models.ReservationHistory)
            .filter(models.ReservationHistory.reservation_id == reservation_id)
            .order_by(models.ReservationHistory.timestamp.desc())
            .all()
        )

    def _get_conflicts(
        self, resource_id: int, start_time: datetime, end_time: datetime
    ) -> list[models.Reservation]:
        """Get all conflicting reservations for a time slot."""
        # Ensure timezone awareness
        start_time = ensure_timezone_aware(start_time)
        end_time = ensure_timezone_aware(end_time)

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

    def _log_action(self, reservation_id: int, action: str, user_id: int, details: str):
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
        user = models.User(username=user_data.username, hashed_password=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_username(self, username: str) -> models.User | None:
        """Get user by username (case-insensitive)."""
        # Normalize username to lowercase for case-insensitive search
        normalized_username = username.lower()
        return (
            self.db.query(models.User)
            .filter(models.User.username == normalized_username)
            .first()
        )
