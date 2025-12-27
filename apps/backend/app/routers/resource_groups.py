"""Resource groups API endpoints for hierarchical resource organization.

Provides endpoints for:
- Creating and managing resource groups
- Organizing resources into groups
- Hierarchical group structures (parent-child)
- Location-based organization (building/floor/room)

Author: Sylvester-Francis
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.database import get_db
from app.rbac import require_role

router = APIRouter(prefix="/api/v1/resource-groups", tags=["Resource Groups"])


# ============================================================================
# Schemas
# ============================================================================


class ResourceGroupCreate(BaseModel):
    """Create a new resource group."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    parent_id: int | None = None
    building: str | None = Field(None, max_length=200)
    floor: str | None = Field(None, max_length=50)
    room: str | None = Field(None, max_length=100)


class ResourceGroupUpdate(BaseModel):
    """Update a resource group."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    parent_id: int | None = None
    building: str | None = Field(None, max_length=200)
    floor: str | None = Field(None, max_length=50)
    room: str | None = Field(None, max_length=100)


class ResourceGroupResponse(BaseModel):
    """Resource group response."""

    id: int
    name: str
    description: str | None
    parent_id: int | None
    building: str | None
    floor: str | None
    room: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResourceGroupWithChildren(ResourceGroupResponse):
    """Resource group with nested children."""

    children: list["ResourceGroupWithChildren"] = []
    resource_count: int = 0


class ResourceGroupTree(BaseModel):
    """Full resource group tree structure."""

    groups: list[ResourceGroupWithChildren]
    total_groups: int
    total_resources: int


class ResourceInGroupResponse(BaseModel):
    """Resource in a group."""

    id: int
    name: str
    available: bool
    status: str
    tags: list[str]
    group_id: int | None
    parent_id: int | None

    model_config = {"from_attributes": True}


class AssignResourceToGroup(BaseModel):
    """Assign a resource to a group."""

    resource_id: int
    group_id: int | None = None


class SetResourceParent(BaseModel):
    """Set parent resource for hierarchy."""

    resource_id: int
    parent_id: int | None = None


# ============================================================================
# Group CRUD Endpoints
# ============================================================================


@router.post(
    "/", response_model=ResourceGroupResponse, status_code=status.HTTP_201_CREATED
)
def create_resource_group(
    data: ResourceGroupCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Create a new resource group.

    Admin only. Groups can be nested by specifying a parent_id.
    """
    # Validate parent exists if specified
    if data.parent_id:
        parent = (
            db.query(models.ResourceGroup)
            .filter(models.ResourceGroup.id == data.parent_id)
            .first()
        )
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent group not found",
            )

    group = models.ResourceGroup(
        name=data.name,
        description=data.description,
        parent_id=data.parent_id,
        building=data.building,
        floor=data.floor,
        room=data.room,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    return group


@router.get("/", response_model=list[ResourceGroupResponse])
def list_resource_groups(
    parent_id: int | None = Query(None, description="Filter by parent group"),
    building: str | None = Query(None, description="Filter by building"),
    include_children: bool = Query(False, description="Include child groups"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all resource groups.

    Can filter by parent_id to get only top-level groups (parent_id=null)
    or children of a specific group.
    """
    query = db.query(models.ResourceGroup)

    if parent_id is not None:
        query = query.filter(models.ResourceGroup.parent_id == parent_id)
    elif not include_children:
        # By default, only return top-level groups
        query = query.filter(models.ResourceGroup.parent_id.is_(None))

    if building:
        query = query.filter(models.ResourceGroup.building == building)

    return query.order_by(models.ResourceGroup.name).all()


@router.get("/tree", response_model=ResourceGroupTree)
def get_resource_group_tree(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the complete resource group tree structure.

    Returns hierarchical tree with resource counts.
    """
    # Get all groups
    all_groups = db.query(models.ResourceGroup).all()

    # Count resources per group
    resource_counts: dict[int, int] = {}
    resources = (
        db.query(models.Resource.group_id)
        .filter(models.Resource.group_id.isnot(None))
        .all()
    )
    for (group_id,) in resources:
        resource_counts[group_id] = resource_counts.get(group_id, 0) + 1

    # Build tree structure
    def build_tree(parent_id: int | None) -> list[dict[str, Any]]:
        children = []
        for group in all_groups:
            if group.parent_id == parent_id:
                group_dict = {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "parent_id": group.parent_id,
                    "building": group.building,
                    "floor": group.floor,
                    "room": group.room,
                    "created_at": group.created_at,
                    "updated_at": group.updated_at,
                    "children": build_tree(group.id),
                    "resource_count": resource_counts.get(group.id, 0),
                }
                children.append(group_dict)
        return children

    tree = build_tree(None)
    total_resources = db.query(models.Resource).count()

    return ResourceGroupTree(
        groups=tree,
        total_groups=len(all_groups),
        total_resources=total_resources,
    )


@router.get("/buildings")
def list_buildings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get list of unique buildings from all groups."""
    buildings = (
        db.query(models.ResourceGroup.building)
        .filter(models.ResourceGroup.building.isnot(None))
        .distinct()
        .all()
    )
    return {"buildings": [b[0] for b in buildings if b[0]]}


@router.get("/ungrouped", response_model=list[ResourceInGroupResponse])
def list_ungrouped_resources(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all resources not assigned to any group."""
    resources = (
        db.query(models.Resource)
        .filter(models.Resource.group_id.is_(None))
        .order_by(models.Resource.name)
        .all()
    )

    return resources


@router.get("/{group_id}", response_model=ResourceGroupWithChildren)
def get_resource_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a specific resource group with its children."""
    group = (
        db.query(models.ResourceGroup)
        .filter(models.ResourceGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource group not found",
        )

    # Get child groups
    children = (
        db.query(models.ResourceGroup)
        .filter(models.ResourceGroup.parent_id == group_id)
        .all()
    )

    # Count resources
    resource_count = (
        db.query(models.Resource).filter(models.Resource.group_id == group_id).count()
    )

    return ResourceGroupWithChildren(
        id=group.id,
        name=group.name,
        description=group.description,
        parent_id=group.parent_id,
        building=group.building,
        floor=group.floor,
        room=group.room,
        created_at=group.created_at,
        updated_at=group.updated_at,
        children=[
            ResourceGroupWithChildren(
                id=c.id,
                name=c.name,
                description=c.description,
                parent_id=c.parent_id,
                building=c.building,
                floor=c.floor,
                room=c.room,
                created_at=c.created_at,
                updated_at=c.updated_at,
                children=[],
                resource_count=db.query(models.Resource)
                .filter(models.Resource.group_id == c.id)
                .count(),
            )
            for c in children
        ],
        resource_count=resource_count,
    )


@router.patch("/{group_id}", response_model=ResourceGroupResponse)
def update_resource_group(
    group_id: int,
    data: ResourceGroupUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Update a resource group."""
    group = (
        db.query(models.ResourceGroup)
        .filter(models.ResourceGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource group not found",
        )

    # Validate parent if changing
    if data.parent_id is not None and data.parent_id != group.parent_id:
        # Can't set parent to self
        if data.parent_id == group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group cannot be its own parent",
            )
        # Check parent exists
        parent = (
            db.query(models.ResourceGroup)
            .filter(models.ResourceGroup.id == data.parent_id)
            .first()
        )
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent group not found",
            )
        # Check for circular reference
        current = parent
        while current.parent_id:
            if current.parent_id == group_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Circular parent reference detected",
                )
            current = (
                db.query(models.ResourceGroup)
                .filter(models.ResourceGroup.id == current.parent_id)
                .first()
            )
            if not current:
                break

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    db.commit()
    db.refresh(group)

    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource_group(
    group_id: int,
    cascade: bool = Query(False, description="Also delete child groups"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Delete a resource group.

    By default, fails if the group has children or resources.
    Use cascade=true to also delete children (resources are unassigned).
    """
    group = (
        db.query(models.ResourceGroup)
        .filter(models.ResourceGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource group not found",
        )

    # Check for children
    children = (
        db.query(models.ResourceGroup)
        .filter(models.ResourceGroup.parent_id == group_id)
        .count()
    )

    if children > 0 and not cascade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group has {children} child group(s). Use cascade=true to delete.",
        )

    # Unassign resources from this group
    db.query(models.Resource).filter(models.Resource.group_id == group_id).update(
        {"group_id": None}
    )

    # If cascade, delete children recursively
    if cascade:

        def delete_children(parent_id: int) -> None:
            child_groups = (
                db.query(models.ResourceGroup)
                .filter(models.ResourceGroup.parent_id == parent_id)
                .all()
            )
            for child in child_groups:
                # Unassign resources from child
                db.query(models.Resource).filter(
                    models.Resource.group_id == child.id
                ).update({"group_id": None})
                # Recurse
                delete_children(child.id)
                db.delete(child)

        delete_children(group_id)

    db.delete(group)
    db.commit()


# ============================================================================
# Resource Assignment Endpoints
# ============================================================================


@router.get("/{group_id}/resources", response_model=list[ResourceInGroupResponse])
def list_resources_in_group(
    group_id: int,
    include_children: bool = Query(
        False, description="Include resources from child groups"
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all resources in a group."""
    group = (
        db.query(models.ResourceGroup)
        .filter(models.ResourceGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource group not found",
        )

    if include_children:
        # Get all descendant group IDs
        group_ids = [group_id]

        def get_child_ids(parent_id: int) -> None:
            children = (
                db.query(models.ResourceGroup.id)
                .filter(models.ResourceGroup.parent_id == parent_id)
                .all()
            )
            for (child_id,) in children:
                group_ids.append(child_id)
                get_child_ids(child_id)

        get_child_ids(group_id)
        query = db.query(models.Resource).filter(
            models.Resource.group_id.in_(group_ids)
        )
    else:
        query = db.query(models.Resource).filter(models.Resource.group_id == group_id)

    return query.order_by(models.Resource.name).all()


@router.post("/{group_id}/resources", status_code=status.HTTP_200_OK)
def assign_resource_to_group(
    group_id: int,
    data: AssignResourceToGroup,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Assign a resource to a group."""
    group = (
        db.query(models.ResourceGroup)
        .filter(models.ResourceGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource group not found",
        )

    resource = (
        db.query(models.Resource).filter(models.Resource.id == data.resource_id).first()
    )

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    resource.group_id = group_id
    db.commit()

    return {"message": f"Resource '{resource.name}' assigned to group '{group.name}'"}


@router.delete("/{group_id}/resources/{resource_id}", status_code=status.HTTP_200_OK)
def remove_resource_from_group(
    group_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Remove a resource from a group (unassign)."""
    resource = (
        db.query(models.Resource)
        .filter(
            models.Resource.id == resource_id,
            models.Resource.group_id == group_id,
        )
        .first()
    )

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found in this group",
        )

    resource.group_id = None
    db.commit()

    return {"message": f"Resource '{resource.name}' removed from group"}


# ============================================================================
# Resource Hierarchy Endpoints
# ============================================================================


@router.post("/resources/set-parent", status_code=status.HTTP_200_OK)
def set_resource_parent(
    data: SetResourceParent,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Set parent resource for resource hierarchy.

    This allows creating resource hierarchies like:
    - Conference Room -> Projector, Whiteboard
    - Server Rack -> Server 1, Server 2
    """
    resource = (
        db.query(models.Resource).filter(models.Resource.id == data.resource_id).first()
    )

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    if data.parent_id:
        if data.parent_id == data.resource_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resource cannot be its own parent",
            )

        parent = (
            db.query(models.Resource)
            .filter(models.Resource.id == data.parent_id)
            .first()
        )

        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent resource not found",
            )

        # Check for circular reference
        current = parent
        while current.parent_id:
            if current.parent_id == data.resource_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Circular parent reference detected",
                )
            current = (
                db.query(models.Resource)
                .filter(models.Resource.id == current.parent_id)
                .first()
            )
            if not current:
                break

    resource.parent_id = data.parent_id
    db.commit()

    parent_name = None
    if data.parent_id:
        parent = (
            db.query(models.Resource)
            .filter(models.Resource.id == data.parent_id)
            .first()
        )
        parent_name = parent.name if parent else None

    return {
        "message": f"Resource '{resource.name}' parent set to '{parent_name}'"
        if parent_name
        else f"Resource '{resource.name}' parent removed",
    }


@router.get(
    "/resources/{resource_id}/children", response_model=list[ResourceInGroupResponse]
)
def get_resource_children(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get child resources of a parent resource."""
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    children = (
        db.query(models.Resource)
        .filter(models.Resource.parent_id == resource_id)
        .order_by(models.Resource.name)
        .all()
    )

    return children
