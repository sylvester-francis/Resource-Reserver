"""Advanced search endpoints for resources and reservations.

Provides endpoints for:
- Searching resources with multiple filters
- Searching reservations with advanced criteria
- Search suggestions and autocomplete
- Saved searches management
- Popular tags

Author: Sylvester-Francis
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.search_service import SavedSearchService, SearchService

router = APIRouter(prefix="/api/v1/search", tags=["search"])


def ensure_timezone_aware(dt):
    """Ensure datetime is timezone-aware (convert to UTC if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@router.get("/resources")
def search_resources(
    request: Request,
    query: str | None = Query(None, description="Text search query"),
    tags: str | None = Query(None, description="Comma-separated tags"),
    status: str | None = Query(
        None, description="Filter by status (available, in_use, unavailable)"
    ),
    available_only: bool = Query(False, description="Only show available resources"),
    available_from: datetime | None = Query(
        None, description="Filter by availability start time"
    ),
    available_until: datetime | None = Query(
        None, description="Filter by availability end time"
    ),
    requires_approval: bool | None = Query(
        None, description="Filter by approval requirement"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Search resources with advanced filters.

    Supports:
    - Text search on name and tags
    - Tag filtering (comma-separated)
    - Status filtering
    - Time-based availability filtering
    - Approval requirement filtering
    - Pagination
    """
    # Parse tags from comma-separated string
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    service = SearchService(db)
    results = service.search_resources(
        query=query,
        tags=tag_list,
        status=status,
        available_only=available_only,
        available_from=ensure_timezone_aware(available_from),
        available_until=ensure_timezone_aware(available_until),
        requires_approval=requires_approval,
        limit=limit,
        offset=offset,
    )

    # Convert to response format
    return {
        "results": [
            {
                "id": r.id,
                "name": r.name,
                "available": r.available,
                "status": r.status,
                "tags": r.tags or [],
                "requires_approval": r.requires_approval,
            }
            for r in results["results"]
        ],
        "total": results["total"],
        "limit": results["limit"],
        "offset": results["offset"],
        "has_more": results["has_more"],
    }


@router.get("/reservations")
def search_reservations(
    request: Request,
    user_id: int | None = Query(None, description="Filter by user ID"),
    resource_id: int | None = Query(None, description="Filter by resource ID"),
    status: str | None = Query(None, description="Filter by status"),
    start_from: datetime | None = Query(
        None, description="Filter by reservation start time (from)"
    ),
    start_until: datetime | None = Query(
        None, description="Filter by reservation start time (until)"
    ),
    created_from: datetime | None = Query(
        None, description="Filter by creation date (from)"
    ),
    created_until: datetime | None = Query(
        None, description="Filter by creation date (until)"
    ),
    include_cancelled: bool = Query(
        False, description="Include cancelled reservations"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Search reservations with advanced filters.

    Supports:
    - User and resource filtering
    - Status filtering
    - Date range filtering (start time and creation date)
    - Pagination
    """
    # Parse status if comma-separated
    status_list = None
    if status:
        if "," in status:
            status_list = [s.strip() for s in status.split(",") if s.strip()]
        else:
            status_list = status

    service = SearchService(db)
    results = service.search_reservations(
        user_id=user_id,
        resource_id=resource_id,
        status=status_list,
        start_from=ensure_timezone_aware(start_from),
        start_until=ensure_timezone_aware(start_until),
        created_from=ensure_timezone_aware(created_from),
        created_until=ensure_timezone_aware(created_until),
        include_cancelled=include_cancelled,
        limit=limit,
        offset=offset,
    )

    # Convert to response format
    return {
        "results": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "username": r.user.username if r.user else None,
                "resource_id": r.resource_id,
                "resource_name": r.resource.name if r.resource else None,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results["results"]
        ],
        "total": results["total"],
        "limit": results["limit"],
        "offset": results["offset"],
        "has_more": results["has_more"],
    }


@router.get("/suggestions")
def get_suggestions(
    request: Request,
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get search suggestions based on query.

    Returns matching resource names and tags.
    """
    service = SearchService(db)
    suggestions = service.get_search_suggestions(query, limit)
    return suggestions


@router.get("/tags/popular")
def get_popular_tags(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the most popular tags across all resources."""
    service = SearchService(db)
    tags = service.get_popular_tags(limit)
    return {"tags": tags}


@router.get("/resources/{resource_id}/availability")
def get_resource_availability(
    resource_id: int,
    request: Request,
    days_ahead: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get availability windows for a resource.

    Returns a list of available and reserved time slots
    for the next N days.
    """
    # Check resource exists
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    service = SearchService(db)
    availability = service.get_upcoming_availability(resource_id, days_ahead)

    return {
        "resource_id": resource_id,
        "resource_name": resource.name,
        "days_ahead": days_ahead,
        "availability": availability,
    }


# Saved Searches endpoints
@router.get("/saved")
def get_saved_searches(
    request: Request,
    search_type: str | None = Query(
        None, description="Filter by type (resources or reservations)"
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get user's saved searches."""
    service = SavedSearchService(db)
    searches = service.get_user_saved_searches(current_user.id, search_type)

    return {
        "saved_searches": [
            {
                "id": s.id,
                "name": s.name,
                "search_type": s.search_type,
                "filters": s.filters,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in searches
        ],
        "count": len(searches),
    }


@router.post("/saved")
def create_saved_search(
    data: schemas.SavedSearchCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Save a search for later use."""
    service = SavedSearchService(db)
    saved_search = service.save_search(
        user_id=current_user.id,
        name=data.name,
        search_type=data.search_type,
        filters=data.filters,
    )

    return {
        "success": True,
        "id": saved_search.id,
        "name": saved_search.name,
        "search_type": saved_search.search_type,
    }


@router.delete("/saved/{search_id}")
def delete_saved_search(
    search_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a saved search."""
    service = SavedSearchService(db)
    deleted = service.delete_saved_search(search_id, current_user.id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Saved search not found")

    return {"success": True, "message": "Saved search deleted"}


@router.post("/saved/{search_id}/execute")
def execute_saved_search(
    search_id: int,
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Execute a saved search."""
    # Get the saved search
    saved_search = (
        db.query(models.SavedSearch)
        .filter(
            models.SavedSearch.id == search_id,
            models.SavedSearch.user_id == current_user.id,
        )
        .first()
    )

    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    service = SearchService(db)
    filters = saved_search.filters

    if saved_search.search_type == "resources":
        # Parse datetime strings back to datetime objects
        available_from = None
        available_until = None
        if filters.get("available_from"):
            available_from = datetime.fromisoformat(filters["available_from"])
        if filters.get("available_until"):
            available_until = datetime.fromisoformat(filters["available_until"])

        results = service.search_resources(
            query=filters.get("query"),
            tags=filters.get("tags"),
            status=filters.get("status"),
            available_only=filters.get("available_only", False),
            available_from=available_from,
            available_until=available_until,
            requires_approval=filters.get("requires_approval"),
            limit=limit,
            offset=offset,
        )

        return {
            "saved_search_name": saved_search.name,
            "search_type": "resources",
            "results": [
                {
                    "id": r.id,
                    "name": r.name,
                    "available": r.available,
                    "status": r.status,
                    "tags": r.tags or [],
                }
                for r in results["results"]
            ],
            "total": results["total"],
            "has_more": results["has_more"],
        }
    else:  # reservations
        # Parse datetime strings back to datetime objects
        start_from = None
        start_until = None
        created_from = None
        created_until = None

        if filters.get("start_from"):
            start_from = datetime.fromisoformat(filters["start_from"])
        if filters.get("start_until"):
            start_until = datetime.fromisoformat(filters["start_until"])
        if filters.get("created_from"):
            created_from = datetime.fromisoformat(filters["created_from"])
        if filters.get("created_until"):
            created_until = datetime.fromisoformat(filters["created_until"])

        results = service.search_reservations(
            user_id=filters.get("user_id"),
            resource_id=filters.get("resource_id"),
            status=filters.get("status"),
            start_from=start_from,
            start_until=start_until,
            created_from=created_from,
            created_until=created_until,
            include_cancelled=filters.get("include_cancelled", False),
            limit=limit,
            offset=offset,
        )

        return {
            "saved_search_name": saved_search.name,
            "search_type": "reservations",
            "results": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "resource_id": r.resource_id,
                    "start_time": r.start_time.isoformat(),
                    "end_time": r.end_time.isoformat(),
                    "status": r.status,
                }
                for r in results["results"]
            ],
            "total": results["total"],
            "has_more": results["has_more"],
        }
