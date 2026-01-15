"""Advanced search service for resources and reservations.

Provides functionality for:
- Full-text search for resources
- Advanced filtering with multiple criteria
- Saved search functionality
- Search suggestions

Author: Sylvester-Francis
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app import models

logger = logging.getLogger(__name__)


def utcnow():
    """Get current UTC datetime that's timezone-aware."""
    return datetime.now(UTC)


def ensure_timezone_aware(dt):
    """Ensure datetime is timezone-aware (convert to UTC if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class SearchService:
    """Service for advanced search functionality."""

    def __init__(self, db: Session):
        self.db = db

    def search_resources(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
        available_only: bool = False,
        available_from: datetime | None = None,
        available_until: datetime | None = None,
        requires_approval: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search resources with multiple filters.

        Args:
            query: Text search query (matches name and tags)
            tags: Filter by specific tags
            status: Filter by status (available, in_use, unavailable)
            available_only: Only show available resources
            available_from: Filter by availability start time
            available_until: Filter by availability end time
            requires_approval: Filter by approval requirement
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            Dict with results and metadata
        """
        db_query = self.db.query(models.Resource)

        # Text search on name
        if query:
            query_lower = query.lower()
            # Search in name and tags
            db_query = db_query.filter(
                or_(
                    models.Resource.name.ilike(f"%{query_lower}%"),
                    # For JSON tags, we need to do a string match
                    models.Resource.tags.cast(models.String).ilike(f"%{query_lower}%"),
                )
            )

        # Status filter
        if status:
            db_query = db_query.filter(models.Resource.status == status)

        # Available only filter
        if available_only:
            db_query = db_query.filter(models.Resource.available.is_(True))

        # Approval requirement filter
        if requires_approval is not None:
            db_query = db_query.filter(
                models.Resource.requires_approval == requires_approval
            )

        # Get all matching resources
        all_resources = db_query.all()

        # Filter by tags (needs Python filtering for JSON)
        # AND logic: resource must have ALL selected tags
        if tags:
            tag_set = {tag.lower() for tag in tags}
            all_resources = [
                r
                for r in all_resources
                if tag_set.issubset({t.lower() for t in (r.tags or [])})
            ]

        # Filter by time availability
        if available_from and available_until:
            available_from = ensure_timezone_aware(available_from)
            available_until = ensure_timezone_aware(available_until)

            filtered_resources = []
            for resource in all_resources:
                # Check if there are any conflicting reservations
                conflict = (
                    self.db.query(models.Reservation)
                    .filter(
                        models.Reservation.resource_id == resource.id,
                        models.Reservation.status == "active",
                        models.Reservation.end_time > available_from,
                        models.Reservation.start_time < available_until,
                    )
                    .first()
                )
                if not conflict:
                    filtered_resources.append(resource)
            all_resources = filtered_resources

        total_count = len(all_resources)

        # Apply pagination
        paginated_resources = all_resources[offset : offset + limit]

        return {
            "results": paginated_resources,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count,
        }

    def search_reservations(
        self,
        user_id: int | None = None,
        resource_id: int | None = None,
        status: str | list[str] | None = None,
        start_from: datetime | None = None,
        start_until: datetime | None = None,
        created_from: datetime | None = None,
        created_until: datetime | None = None,
        include_cancelled: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search reservations with multiple filters.

        Args:
            user_id: Filter by user ID
            resource_id: Filter by resource ID
            status: Filter by status (single or list)
            start_from: Filter by reservation start time (from)
            start_until: Filter by reservation start time (until)
            created_from: Filter by creation date (from)
            created_until: Filter by creation date (until)
            include_cancelled: Include cancelled reservations
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            Dict with results and metadata
        """
        db_query = self.db.query(models.Reservation).options(
            joinedload(models.Reservation.resource),
            joinedload(models.Reservation.user),
        )

        # User filter
        if user_id is not None:
            db_query = db_query.filter(models.Reservation.user_id == user_id)

        # Resource filter
        if resource_id is not None:
            db_query = db_query.filter(models.Reservation.resource_id == resource_id)

        # Status filter
        if status:
            if isinstance(status, list):
                db_query = db_query.filter(models.Reservation.status.in_(status))
            else:
                db_query = db_query.filter(models.Reservation.status == status)
        elif not include_cancelled:
            db_query = db_query.filter(models.Reservation.status != "cancelled")

        # Start time filters
        if start_from:
            start_from = ensure_timezone_aware(start_from)
            db_query = db_query.filter(models.Reservation.start_time >= start_from)

        if start_until:
            start_until = ensure_timezone_aware(start_until)
            db_query = db_query.filter(models.Reservation.start_time <= start_until)

        # Created date filters
        if created_from:
            created_from = ensure_timezone_aware(created_from)
            db_query = db_query.filter(models.Reservation.created_at >= created_from)

        if created_until:
            created_until = ensure_timezone_aware(created_until)
            db_query = db_query.filter(models.Reservation.created_at <= created_until)

        # Get total count (before pagination)
        total_count = db_query.count()

        # Apply pagination and ordering
        reservations = (
            db_query.order_by(models.Reservation.start_time.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "results": reservations,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count,
        }

    def get_search_suggestions(
        self, query: str, limit: int = 10
    ) -> dict[str, list[str]]:
        """Get search suggestions based on query.

        Returns suggestions from:
        - Resource names
        - Tags
        """
        query_lower = query.lower()
        suggestions = {
            "resources": [],
            "tags": [],
        }

        # Get matching resource names
        resources = (
            self.db.query(models.Resource)
            .filter(models.Resource.name.ilike(f"%{query_lower}%"))
            .limit(limit)
            .all()
        )
        suggestions["resources"] = [r.name for r in resources]

        # Collect all unique tags from matching resources
        all_tags = set()
        for resource in self.db.query(models.Resource).all():
            for tag in resource.tags or []:
                if query_lower in tag.lower():
                    all_tags.add(tag)

        suggestions["tags"] = list(all_tags)[:limit]

        return suggestions

    def get_popular_tags(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get most popular tags across all resources."""
        tag_counts = {}

        for resource in self.db.query(models.Resource).all():
            for tag in resource.tags or []:
                tag_lower = tag.lower()
                tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

        # Sort by count and return top tags
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"tag": tag, "count": count} for tag, count in sorted_tags[:limit]]

    def get_upcoming_availability(
        self, resource_id: int, days_ahead: int = 7
    ) -> list[dict[str, Any]]:
        """Get availability windows for a resource in the next N days."""
        now = utcnow()
        end_date = now + timedelta(days=days_ahead)

        # Get all active reservations in this period
        reservations = (
            self.db.query(models.Reservation)
            .filter(
                models.Reservation.resource_id == resource_id,
                models.Reservation.status == "active",
                models.Reservation.end_time > now,
                models.Reservation.start_time < end_date,
            )
            .order_by(models.Reservation.start_time)
            .all()
        )

        # Build availability windows
        availability = []
        current_start = now

        for reservation in reservations:
            if reservation.start_time > current_start:
                # There's a gap - available window
                availability.append(
                    {
                        "start": current_start.isoformat(),
                        "end": reservation.start_time.isoformat(),
                        "available": True,
                        "duration_hours": round(
                            (reservation.start_time - current_start).total_seconds()
                            / 3600,
                            2,
                        ),
                    }
                )

            # Add reservation block
            availability.append(
                {
                    "start": reservation.start_time.isoformat(),
                    "end": reservation.end_time.isoformat(),
                    "available": False,
                    "reservation_id": reservation.id,
                }
            )

            current_start = reservation.end_time

        # Add final availability window if there's time left
        if current_start < end_date:
            availability.append(
                {
                    "start": current_start.isoformat(),
                    "end": end_date.isoformat(),
                    "available": True,
                    "duration_hours": round(
                        (end_date - current_start).total_seconds() / 3600, 2
                    ),
                }
            )

        return availability


class SavedSearchService:
    """Service for managing saved searches."""

    def __init__(self, db: Session):
        self.db = db

    def save_search(
        self,
        user_id: int,
        name: str,
        search_type: str,
        filters: dict[str, Any],
    ) -> models.SavedSearch:
        """Save a search for a user."""
        # Check if user already has a search with this name
        existing = (
            self.db.query(models.SavedSearch)
            .filter(
                models.SavedSearch.user_id == user_id,
                models.SavedSearch.name == name,
            )
            .first()
        )

        if existing:
            # Update existing
            existing.search_type = search_type
            existing.filters = filters
            existing.updated_at = utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new
        saved_search = models.SavedSearch(
            user_id=user_id,
            name=name,
            search_type=search_type,
            filters=filters,
        )
        self.db.add(saved_search)
        self.db.commit()
        self.db.refresh(saved_search)
        return saved_search

    def get_user_saved_searches(
        self, user_id: int, search_type: str | None = None
    ) -> list[models.SavedSearch]:
        """Get all saved searches for a user."""
        query = self.db.query(models.SavedSearch).filter(
            models.SavedSearch.user_id == user_id
        )

        if search_type:
            query = query.filter(models.SavedSearch.search_type == search_type)

        return query.order_by(models.SavedSearch.updated_at.desc()).all()

    def delete_saved_search(self, search_id: int, user_id: int) -> bool:
        """Delete a saved search."""
        saved_search = (
            self.db.query(models.SavedSearch)
            .filter(
                models.SavedSearch.id == search_id,
                models.SavedSearch.user_id == user_id,
            )
            .first()
        )

        if not saved_search:
            return False

        self.db.delete(saved_search)
        self.db.commit()
        return True
