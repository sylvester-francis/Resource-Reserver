"""Role-Based Access Control (RBAC) using Casbin."""

import tempfile

import casbin
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.database import get_db

# Casbin model configuration
CASBIN_MODEL = """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
"""

# Casbin policies (roles and permissions)
CASBIN_POLICIES = [
    # Admin role permissions
    ("p", "admin", "resource", "create"),
    ("p", "admin", "resource", "read"),
    ("p", "admin", "resource", "update"),
    ("p", "admin", "resource", "delete"),
    ("p", "admin", "reservation", "create"),
    ("p", "admin", "reservation", "read"),
    ("p", "admin", "reservation", "update"),
    ("p", "admin", "reservation", "delete"),
    ("p", "admin", "user", "create"),
    ("p", "admin", "user", "read"),
    ("p", "admin", "user", "update"),
    ("p", "admin", "user", "delete"),
    ("p", "admin", "oauth_client", "create"),
    ("p", "admin", "oauth_client", "read"),
    ("p", "admin", "oauth_client", "update"),
    ("p", "admin", "oauth_client", "delete"),
    # User role permissions
    ("p", "user", "resource", "read"),
    ("p", "user", "reservation", "create"),
    ("p", "user", "reservation", "read"),
    ("p", "user", "reservation", "update_own"),
    ("p", "user", "reservation", "delete_own"),
    ("p", "user", "oauth_client", "create"),
    ("p", "user", "oauth_client", "read_own"),
    ("p", "user", "oauth_client", "delete_own"),
    # Guest role permissions
    ("p", "guest", "resource", "read"),
]


def get_enforcer() -> casbin.Enforcer:
    """Get Casbin enforcer instance."""
    # Create model in secure temp directory
    import os

    model_path = os.path.join(tempfile.gettempdir(), "rbac_model.conf")
    with open(model_path, "w") as f:
        f.write(CASBIN_MODEL)

    # Create enforcer with in-memory adapter
    enforcer = casbin.Enforcer(model_path)

    # Load policies
    for policy in CASBIN_POLICIES:
        enforcer.add_policy(*policy[1:])  # Skip policy type 'p'

    return enforcer


# Global enforcer instance
_enforcer = None


def get_global_enforcer() -> casbin.Enforcer:
    """Get or create global enforcer instance."""
    global _enforcer
    if _enforcer is None:
        _enforcer = get_enforcer()
    return _enforcer


def check_permission(
    user: models.User, resource: str, action: str, db: Session
) -> bool:
    """
    Check if user has permission for action on resource.

    Args:
        user: User to check
        resource: Resource type (e.g., 'resource', 'reservation')
        action: Action (e.g., 'read', 'create', 'update', 'delete')
        db: Database session

    Returns:
        True if user has permission, False otherwise
    """
    enforcer = get_global_enforcer()

    # Get user roles
    roles = get_user_roles(user.id, db)

    # Check each role
    for role in roles:
        if enforcer.enforce(role.name, resource, action):
            return True

    return False


def get_user_roles(user_id: int, db: Session) -> list[models.Role]:
    """Get all roles for a user."""
    user_roles = (
        db.query(models.UserRole).filter(models.UserRole.user_id == user_id).all()
    )

    return [db.query(models.Role).get(ur.role_id) for ur in user_roles]


def has_role(user: models.User, role_name: str, db: Session) -> bool:
    """Check if user has a specific role."""
    roles = get_user_roles(user.id, db)
    return any(role.name == role_name for role in roles)


def is_admin(user: models.User, db: Session) -> bool:
    """Check if user is an admin."""
    return has_role(user, "admin", db)


def assign_role(user_id: int, role_name: str, db: Session) -> bool:
    """
    Assign a role to a user.

    Args:
        user_id: User ID
        role_name: Role name
        db: Database session

    Returns:
        True if assigned successfully, False if role doesn't exist
    """
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        return False

    # Check if already assigned
    existing = (
        db.query(models.UserRole)
        .filter(models.UserRole.user_id == user_id, models.UserRole.role_id == role.id)
        .first()
    )

    if existing:
        return True  # Already assigned

    user_role = models.UserRole(user_id=user_id, role_id=role.id)
    db.add(user_role)
    db.commit()
    return True


def remove_role(user_id: int, role_name: str, db: Session) -> bool:
    """Remove a role from a user."""
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        return False

    user_role = (
        db.query(models.UserRole)
        .filter(models.UserRole.user_id == user_id, models.UserRole.role_id == role.id)
        .first()
    )

    if user_role:
        db.delete(user_role)
        db.commit()

    return True


def create_default_roles(db: Session):
    """Create default roles if they don't exist."""
    roles_data = [
        ("admin", "Administrator with full access"),
        ("user", "Regular user with standard permissions"),
        ("guest", "Guest user with read-only access"),
    ]

    for role_name, description in roles_data:
        existing = db.query(models.Role).filter(models.Role.name == role_name).first()
        if not existing:
            role = models.Role(name=role_name, description=description)
            db.add(role)

    db.commit()


# FastAPI dependency for permission checking
def require_permission(resource: str, action: str):
    """
    Dependency to check if current user has permission.

    Usage:
        @app.post("/resources")
        def create_resource(user: User = Depends(require_permission("resource", "create"))):
            ...
    """

    def permission_checker(
        user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
    ):
        if not check_permission(user, resource, action, db):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions: {action} on {resource}",
            )
        return user

    return permission_checker


def require_role(role_name: str):
    """
    Dependency to check if current user has a specific role.

    Usage:
        @app.get("/admin")
        def admin_page(user: User = Depends(require_role("admin"))):
            ...
    """

    def role_checker(
        user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
    ):
        if not has_role(user, role_name, db):
            raise HTTPException(status_code=403, detail=f"Role required: {role_name}")
        return user

    return role_checker


# Resource-level permission checking
def check_resource_permission(
    user: models.User, resource: models.Resource, action: str, db: Session
) -> bool:
    """
    Check if user can perform action on specific resource.

    This checks both:
    1. Global role-based permissions
    2. Resource-specific permissions
    """
    # Check global permissions first
    if check_permission(user, "resource", action, db):
        return True

    # Check resource-specific permissions
    perm = (
        db.query(models.ResourcePermission)
        .filter(
            models.ResourcePermission.resource_id == resource.id,
            models.ResourcePermission.user_id == user.id,
            models.ResourcePermission.action == action,
        )
        .first()
    )

    if perm:
        return True

    # Check role-based resource permissions
    user_roles = get_user_roles(user.id, db)
    for role in user_roles:
        perm = (
            db.query(models.ResourcePermission)
            .filter(
                models.ResourcePermission.resource_id == resource.id,
                models.ResourcePermission.role_id == role.id,
                models.ResourcePermission.action == action,
            )
            .first()
        )
        if perm:
            return True

    return False


def grant_resource_permission(
    resource_id: int, user_id: int, action: str, db: Session
) -> models.ResourcePermission:
    """Grant a user permission to perform action on resource."""
    perm = models.ResourcePermission(
        resource_id=resource_id, user_id=user_id, action=action
    )
    db.add(perm)
    db.commit()
    return perm


def revoke_resource_permission(
    resource_id: int, user_id: int, action: str, db: Session
) -> bool:
    """Revoke a user's permission to perform action on resource."""
    perm = (
        db.query(models.ResourcePermission)
        .filter(
            models.ResourcePermission.resource_id == resource_id,
            models.ResourcePermission.user_id == user_id,
            models.ResourcePermission.action == action,
        )
        .first()
    )

    if perm:
        db.delete(perm)
        db.commit()
        return True

    return False
