"""Label management endpoints for resource categorization.

This module provides CRUD operations for labels and label-resource assignments.
Labels enable normalized categorization of resources with admin-controlled
vocabulary and color-coded visual indicators.

Features:
    - Label CRUD with category/value/color management
    - Resource-label assignment (many-to-many)
    - Label merging for consolidating duplicates
    - Category listing for filtering UI
    - Pagination and filtering support

Access Control:
    - Read operations: All authenticated users
    - Write operations: Admin only
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.rbac import check_permission

router = APIRouter(prefix="/api/v1/labels", tags=["Labels"])


def require_admin_permission(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.User:
    """Dependency that ensures the current user has admin permissions.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The current user if they have admin permissions.

    Raises:
        HTTPException: 403 error if user lacks admin permissions.
    """
    if not check_permission(current_user, resource="resource", action="create", db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get(
    "",
    response_model=schemas.PaginatedResponse[schemas.LabelResponse],
    status_code=status.HTTP_200_OK,
)
def list_labels(
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search in category and value"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("category", description="Sort by: id, category, value"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all labels with optional filtering and pagination.

    Args:
        category: Optional category filter.
        search: Optional search term for category or value.
        cursor: Pagination cursor from previous response.
        limit: Maximum number of labels to return.
        sort_by: Field to sort by.
        sort_order: Sort direction.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        Paginated list of labels with resource counts.
    """
    query = db.query(models.Label)

    # Apply category filter
    if category:
        query = query.filter(models.Label.category == category)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.Label.category.ilike(search_pattern))
            | (models.Label.value.ilike(search_pattern))
        )

    # Get total count before pagination
    total_count = query.count()

    # Apply sorting
    sort_column = getattr(models.Label, sort_by, models.Label.category)
    if sort_order.lower() == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column, models.Label.id)

    # Apply cursor-based pagination
    if cursor:
        try:
            cursor_id = int(cursor)
            query = query.filter(models.Label.id > cursor_id)
        except ValueError:
            pass

    # Fetch labels with limit + 1 to check for more
    labels = query.limit(limit + 1).all()
    has_more = len(labels) > limit
    if has_more:
        labels = labels[:limit]

    # Get resource counts for each label
    label_ids = [label.id for label in labels]
    resource_counts = {}
    if label_ids:
        counts = (
            db.query(
                models.ResourceLabel.label_id,
                func.count(models.ResourceLabel.id).label("count"),
            )
            .filter(models.ResourceLabel.label_id.in_(label_ids))
            .group_by(models.ResourceLabel.label_id)
            .all()
        )
        resource_counts = {count.label_id: count.count for count in counts}

    # Build response
    response_labels = [
        schemas.LabelResponse.from_model(label, resource_counts.get(label.id, 0))
        for label in labels
    ]

    next_cursor = str(labels[-1].id) if labels and has_more else None

    return schemas.PaginatedResponse(
        data=response_labels,
        next_cursor=next_cursor,
        prev_cursor=None,
        has_more=has_more,
        total_count=total_count,
    )


@router.post(
    "",
    response_model=schemas.LabelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_label(
    label_data: schemas.LabelCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin_permission),
):
    """Create a new label.

    Requires admin privileges. Category + value must be unique.

    Args:
        label_data: Label creation data.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        The created label.

    Raises:
        HTTPException: If label with same category/value exists.
    """
    # Check for duplicate
    existing = (
        db.query(models.Label)
        .filter(
            models.Label.category == label_data.category,
            models.Label.value == label_data.value,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Label '{label_data.category}:{label_data.value}' already exists",
        )

    label = models.Label(
        category=label_data.category,
        value=label_data.value,
        color=label_data.color,
        description=label_data.description,
    )
    db.add(label)
    db.commit()
    db.refresh(label)

    return schemas.LabelResponse.from_model(label, 0)


@router.get(
    "/categories",
    response_model=list[schemas.LabelCategoryResponse],
    status_code=status.HTTP_200_OK,
)
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all unique label categories with counts.

    Args:
        db: Database session.
        current_user: Authenticated user.

    Returns:
        List of categories with label counts.
    """
    categories = (
        db.query(
            models.Label.category,
            func.count(models.Label.id).label("label_count"),
        )
        .group_by(models.Label.category)
        .order_by(models.Label.category)
        .all()
    )

    return [
        schemas.LabelCategoryResponse(
            category=cat.category,
            label_count=cat.label_count,
        )
        for cat in categories
    ]


@router.get(
    "/{label_id}",
    response_model=schemas.LabelResponse,
    status_code=status.HTTP_200_OK,
)
def get_label(
    label_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a specific label by ID.

    Args:
        label_id: The label ID.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        The label details.

    Raises:
        HTTPException: If label not found.
    """
    label = db.query(models.Label).filter(models.Label.id == label_id).first()
    if not label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found",
        )

    resource_count = (
        db.query(func.count(models.ResourceLabel.id))
        .filter(models.ResourceLabel.label_id == label_id)
        .scalar()
    )

    return schemas.LabelResponse.from_model(label, resource_count)


@router.put(
    "/{label_id}",
    response_model=schemas.LabelResponse,
    status_code=status.HTTP_200_OK,
)
def update_label(
    label_id: int,
    label_data: schemas.LabelUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin_permission),
):
    """Update a label.

    Requires admin privileges. Category + value must remain unique.

    Args:
        label_id: The label ID to update.
        label_data: Updated label data.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        The updated label.

    Raises:
        HTTPException: If label not found or duplicate would be created.
    """
    label = db.query(models.Label).filter(models.Label.id == label_id).first()
    if not label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found",
        )

    # Check for duplicate if category or value is changing
    new_category = label_data.category if label_data.category else label.category
    new_value = label_data.value if label_data.value else label.value

    if new_category != label.category or new_value != label.value:
        existing = (
            db.query(models.Label)
            .filter(
                models.Label.category == new_category,
                models.Label.value == new_value,
                models.Label.id != label_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Label '{new_category}:{new_value}' already exists",
            )

    # Update fields
    if label_data.category is not None:
        label.category = label_data.category
    if label_data.value is not None:
        label.value = label_data.value
    if label_data.color is not None:
        label.color = label_data.color
    if label_data.description is not None:
        label.description = label_data.description

    db.commit()
    db.refresh(label)

    resource_count = (
        db.query(func.count(models.ResourceLabel.id))
        .filter(models.ResourceLabel.label_id == label_id)
        .scalar()
    )

    return schemas.LabelResponse.from_model(label, resource_count)


@router.delete(
    "/{label_id}",
    status_code=status.HTTP_200_OK,
)
def delete_label(
    label_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin_permission),
):
    """Delete a label.

    Requires admin privileges. Also removes all resource-label associations.

    Args:
        label_id: The label ID to delete.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If label not found.
    """
    label = db.query(models.Label).filter(models.Label.id == label_id).first()
    if not label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found",
        )

    db.delete(label)
    db.commit()

    return {"message": f"Label '{label.category}:{label.value}' deleted successfully"}


@router.post(
    "/merge",
    response_model=schemas.LabelResponse,
    status_code=status.HTTP_200_OK,
)
def merge_labels(
    merge_data: schemas.LabelMerge,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin_permission),
):
    """Merge multiple labels into one.

    Requires admin privileges. Moves all resource assignments from source
    labels to target label, then deletes source labels. Source and target
    labels must be in the same category.

    Args:
        merge_data: Merge configuration with source and target label IDs.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        The target label with updated resource count.

    Raises:
        HTTPException: If labels not found, not in same category, or target
            is in source list.
    """
    # Validate target not in sources
    if merge_data.target_label_id in merge_data.source_label_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target label cannot be in source labels list",
        )

    # Get target label
    target_label = (
        db.query(models.Label)
        .filter(models.Label.id == merge_data.target_label_id)
        .first()
    )
    if not target_label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target label not found",
        )

    # Get source labels
    source_labels = (
        db.query(models.Label)
        .filter(models.Label.id.in_(merge_data.source_label_ids))
        .all()
    )
    if len(source_labels) != len(merge_data.source_label_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more source labels not found",
        )

    # Verify same category
    for source in source_labels:
        if source.category != target_label.category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All labels must be in the same category to merge",
            )

    # Get all resource IDs currently assigned to source labels
    source_resource_labels = (
        db.query(models.ResourceLabel)
        .filter(models.ResourceLabel.label_id.in_(merge_data.source_label_ids))
        .all()
    )

    # Get resource IDs already assigned to target
    existing_target_resources = set(
        db.query(models.ResourceLabel.resource_id)
        .filter(models.ResourceLabel.label_id == merge_data.target_label_id)
        .all()
    )
    existing_target_resources = {r[0] for r in existing_target_resources}

    # Move assignments to target (only if not already assigned)
    for resource_label in source_resource_labels:
        if resource_label.resource_id not in existing_target_resources:
            new_assignment = models.ResourceLabel(
                resource_id=resource_label.resource_id,
                label_id=merge_data.target_label_id,
            )
            db.add(new_assignment)
            existing_target_resources.add(resource_label.resource_id)

    # Delete source labels (cascade will remove their ResourceLabel entries)
    for source in source_labels:
        db.delete(source)

    db.commit()
    db.refresh(target_label)

    resource_count = (
        db.query(func.count(models.ResourceLabel.id))
        .filter(models.ResourceLabel.label_id == merge_data.target_label_id)
        .scalar()
    )

    return schemas.LabelResponse.from_model(target_label, resource_count)


@router.put(
    "/resources/{resource_id}",
    response_model=list[schemas.LabelResponse],
    status_code=status.HTTP_200_OK,
)
def assign_labels_to_resource(
    resource_id: int,
    labels_data: schemas.ResourceLabelsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin_permission),
):
    """Assign labels to a resource.

    Requires admin privileges. Replaces all existing label assignments
    for the resource with the provided list.

    Args:
        resource_id: The resource ID to assign labels to.
        labels_data: List of label IDs to assign.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        List of labels now assigned to the resource.

    Raises:
        HTTPException: If resource not found or any label ID is invalid.
    """
    # Verify resource exists
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    # Verify all labels exist
    if labels_data.label_ids:
        existing_labels = (
            db.query(models.Label)
            .filter(models.Label.id.in_(labels_data.label_ids))
            .all()
        )
        if len(existing_labels) != len(labels_data.label_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more label IDs are invalid",
            )

    # Remove existing assignments
    db.query(models.ResourceLabel).filter(
        models.ResourceLabel.resource_id == resource_id
    ).delete()

    # Create new assignments
    for label_id in labels_data.label_ids:
        assignment = models.ResourceLabel(
            resource_id=resource_id,
            label_id=label_id,
        )
        db.add(assignment)

    db.commit()

    # Fetch and return assigned labels
    assigned_labels = (
        db.query(models.Label)
        .join(models.ResourceLabel)
        .filter(models.ResourceLabel.resource_id == resource_id)
        .all()
    )

    return [schemas.LabelResponse.from_model(label, 0) for label in assigned_labels]


@router.get(
    "/resources/{resource_id}",
    response_model=list[schemas.LabelResponse],
    status_code=status.HTTP_200_OK,
)
def get_resource_labels(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all labels assigned to a resource.

    Args:
        resource_id: The resource ID.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        List of labels assigned to the resource.

    Raises:
        HTTPException: If resource not found.
    """
    # Verify resource exists
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    labels = (
        db.query(models.Label)
        .join(models.ResourceLabel)
        .filter(models.ResourceLabel.resource_id == resource_id)
        .all()
    )

    return [schemas.LabelResponse.from_model(label, 0) for label in labels]
