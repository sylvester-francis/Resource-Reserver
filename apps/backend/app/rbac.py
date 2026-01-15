"""Role-Based Access Control (RBAC) module using Casbin.

This module implements a comprehensive Role-Based Access Control system for the
Resource Reserver application using the Casbin authorization library. It provides
fine-grained permission management at both global and resource-specific levels.

Features:
    - Role-based permission checking using Casbin enforcer
    - Global permissions for resources, reservations, users, and OAuth clients
    - Resource-specific permission grants for individual users or roles
    - FastAPI dependency injection for route-level authorization
    - Default role creation and management (admin, user, guest)
    - Role assignment and removal for users

Example Usage:
    Basic permission checking::

        from app.rbac import check_permission, has_role, is_admin

        # Check if user can create a resource
        if check_permission(user, "resource", "create", db):
            # User has permission
            pass

        # Check if user is an admin
        if is_admin(user, db):
            # User is an administrator
            pass

    FastAPI route protection::

        from app.rbac import require_permission, require_role

        @app.post("/resources")
        def create_resource(
            user: User = Depends(require_permission("resource", "create"))
        ):
            # Only users with resource:create permission can access
            pass

        @app.get("/admin/dashboard")
        def admin_dashboard(user: User = Depends(require_role("admin"))):
            # Only admins can access
            pass

    Resource-specific permissions::

        from app.rbac import grant_resource_permission, check_resource_permission

        # Grant user permission on specific resource
        grant_resource_permission(resource_id=1, user_id=2, action="update", db=db)

        # Check resource-specific permission
        if check_resource_permission(user, resource, "update", db):
            # User can update this specific resource
            pass

Author:
    Resource Reserver Development Team
"""

import tempfile

import casbin
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.database import get_db

# Casbin model configuration defining the RBAC structure.
# Uses PERM (Policy, Effect, Request, Matchers) model with role inheritance.
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

# Casbin policies defining role permissions.
# Each tuple follows the format: (policy_type, role, resource, action)
CASBIN_POLICIES = [
    # Admin role permissions - full CRUD access to all resources
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
    # User role permissions - standard user access
    ("p", "user", "resource", "read"),
    ("p", "user", "reservation", "create"),
    ("p", "user", "reservation", "read"),
    ("p", "user", "reservation", "update_own"),
    ("p", "user", "reservation", "delete_own"),
    ("p", "user", "oauth_client", "create"),
    ("p", "user", "oauth_client", "read_own"),
    ("p", "user", "oauth_client", "delete_own"),
    # Guest role permissions - read-only access
    ("p", "guest", "resource", "read"),
]


def get_enforcer() -> casbin.Enforcer:
    """Create and configure a new Casbin enforcer instance.

    Creates a Casbin enforcer by writing the RBAC model configuration to a
    temporary file and loading all defined policies. This enforcer evaluates
    permission requests against the defined policy rules.

    Returns:
        casbin.Enforcer: A configured Casbin enforcer instance with all
            policies loaded and ready for permission enforcement.

    Note:
        This function creates a new enforcer each time it is called.
        For production use, prefer `get_global_enforcer()` which caches
        the enforcer instance.
    """
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


# Global enforcer instance for singleton pattern
_enforcer = None


def get_global_enforcer() -> casbin.Enforcer:
    """Get or create the global Casbin enforcer singleton instance.

    Implements a singleton pattern to ensure only one enforcer instance
    exists throughout the application lifecycle. This improves performance
    by avoiding repeated enforcer initialization.

    Returns:
        casbin.Enforcer: The global Casbin enforcer instance. Creates a new
            instance on first call, returns the cached instance on subsequent
            calls.
    """
    global _enforcer
    if _enforcer is None:
        _enforcer = get_enforcer()
    return _enforcer


def check_permission(
    user: models.User, resource: str, action: str, db: Session
) -> bool:
    """Check if a user has permission to perform an action on a resource type.

    Evaluates the user's roles against the Casbin policy rules to determine
    if the requested action is allowed on the specified resource type.

    Args:
        user: The user object whose permissions are being checked.
        resource: The resource type to check permissions for. Valid values
            include 'resource', 'reservation', 'user', 'oauth_client'.
        action: The action to check permission for. Common values include
            'create', 'read', 'update', 'delete', 'update_own', 'delete_own'.
        db: The SQLAlchemy database session for querying user roles.

    Returns:
        bool: True if the user has at least one role that grants permission
            for the specified action on the resource type, False otherwise.

    Example:
        >>> if check_permission(current_user, "resource", "create", db):
        ...     # User can create resources
        ...     pass
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
    """Retrieve all roles assigned to a specific user.

    Args:
        user_id: The unique identifier of the user whose roles to retrieve.
        db: The SQLAlchemy database session for querying role assignments.

    Returns:
        list[models.Role]: A list of Role model instances assigned to the user.
            Returns an empty list if the user has no assigned roles.
    """
    user_roles = (
        db.query(models.UserRole).filter(models.UserRole.user_id == user_id).all()
    )

    return [db.get(models.Role, ur.role_id) for ur in user_roles]


def has_role(user: models.User, role_name: str, db: Session) -> bool:
    """Check if a user has a specific role assigned.

    Args:
        user: The user object to check for role membership.
        role_name: The name of the role to check for (e.g., 'admin', 'user',
            'guest').
        db: The SQLAlchemy database session for querying role assignments.

    Returns:
        bool: True if the user has the specified role, False otherwise.

    Example:
        >>> if has_role(current_user, "admin", db):
        ...     # User is an admin
        ...     pass
    """
    roles = get_user_roles(user.id, db)
    return any(role.name == role_name for role in roles)


def is_admin(user: models.User, db: Session) -> bool:
    """Check if a user has administrator privileges.

    Convenience function that checks if the user has the 'admin' role.

    Args:
        user: The user object to check for admin status.
        db: The SQLAlchemy database session for querying role assignments.

    Returns:
        bool: True if the user has the 'admin' role, False otherwise.
    """
    return has_role(user, "admin", db)


def assign_role(user_id: int, role_name: str, db: Session) -> bool:
    """Assign a role to a user.

    Creates a new user-role association if it does not already exist.
    If the user already has the role, the function succeeds without
    creating a duplicate assignment.

    Args:
        user_id: The unique identifier of the user to assign the role to.
        role_name: The name of the role to assign (e.g., 'admin', 'user',
            'guest'). Case-insensitive.
        db: The SQLAlchemy database session for database operations.

    Returns:
        bool: True if the role was successfully assigned or already existed,
            False if the specified role does not exist in the database.

    Example:
        >>> success = assign_role(user_id=1, role_name="admin", db=db)
        >>> if success:
        ...     print("Role assigned successfully")
    """
    from sqlalchemy import func
    role = db.query(models.Role).filter(func.lower(models.Role.name) == role_name.lower()).first()
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
    """Remove a role from a user.

    Deletes the user-role association if it exists. If the user does not
    have the role, the function still returns True (idempotent behavior).

    Args:
        user_id: The unique identifier of the user to remove the role from.
        role_name: The name of the role to remove. Case-insensitive.
        db: The SQLAlchemy database session for database operations.

    Returns:
        bool: True if the operation completed successfully (role was removed
            or user did not have the role), False if the specified role does
            not exist in the database.
    """
    from sqlalchemy import func
    role = db.query(models.Role).filter(func.lower(models.Role.name) == role_name.lower()).first()
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


def create_default_roles(db: Session) -> None:
    """Create the default system roles if they do not exist.

    Initializes the database with the standard role hierarchy:
    - admin: Full administrative access to all resources
    - user: Standard user permissions with own-resource restrictions
    - guest: Read-only access to resources

    Args:
        db: The SQLAlchemy database session for database operations.

    Note:
        This function is idempotent and safe to call multiple times.
        Existing roles will not be modified or duplicated.
    """
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


def require_permission(resource: str, action: str):
    """Create a FastAPI dependency that enforces permission requirements.

    Returns a dependency function that checks if the current authenticated
    user has permission to perform the specified action on the resource type.
    If the user lacks permission, an HTTP 403 Forbidden error is raised.

    Args:
        resource: The resource type to require permission for (e.g.,
            'resource', 'reservation', 'user', 'oauth_client').
        action: The action to require permission for (e.g., 'create',
            'read', 'update', 'delete').

    Returns:
        Callable: A FastAPI dependency function that returns the authenticated
            user if permission is granted.

    Raises:
        HTTPException: 403 Forbidden if the user lacks the required permission.

    Example:
        >>> @app.post("/resources")
        ... def create_resource(
        ...     user: User = Depends(require_permission("resource", "create"))
        ... ):
        ...     # Only users with resource:create permission reach here
        ...     return {"status": "created"}
    """

    def permission_checker(
        user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> models.User:
        """Inner dependency function that performs the permission check.

        Args:
            user: The current authenticated user (injected by FastAPI).
            db: The database session (injected by FastAPI).

        Returns:
            models.User: The authenticated user if permission check passes.

        Raises:
            HTTPException: 403 Forbidden if permission check fails.
        """
        if not check_permission(user, resource, action, db):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions: {action} on {resource}",
            )
        return user

    return permission_checker


def require_role(role_name: str):
    """Create a FastAPI dependency that enforces role requirements.

    Returns a dependency function that checks if the current authenticated
    user has the specified role. If the user lacks the role, an HTTP 403
    Forbidden error is raised.

    Args:
        role_name: The name of the required role (e.g., 'admin', 'user',
            'guest').

    Returns:
        Callable: A FastAPI dependency function that returns the authenticated
            user if the role requirement is met.

    Raises:
        HTTPException: 403 Forbidden if the user lacks the required role.

    Example:
        >>> @app.get("/admin/dashboard")
        ... def admin_dashboard(user: User = Depends(require_role("admin"))):
        ...     # Only admins can access this endpoint
        ...     return {"status": "admin access granted"}
    """

    def role_checker(
        user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> models.User:
        """Inner dependency function that performs the role check.

        Args:
            user: The current authenticated user (injected by FastAPI).
            db: The database session (injected by FastAPI).

        Returns:
            models.User: The authenticated user if role check passes.

        Raises:
            HTTPException: 403 Forbidden if role check fails.
        """
        if not has_role(user, role_name, db):
            raise HTTPException(status_code=403, detail=f"Role required: {role_name}")
        return user

    return role_checker


def check_resource_permission(
    user: models.User, resource: models.Resource, action: str, db: Session
) -> bool:
    """Check if a user can perform an action on a specific resource instance.

    Performs a two-level permission check:
    1. Global role-based permissions (via Casbin policies)
    2. Resource-specific permissions (via ResourcePermission model)

    Resource-specific permissions can be granted directly to users or through
    their roles, enabling fine-grained access control beyond global policies.

    Args:
        user: The user object whose permissions are being checked.
        resource: The specific resource instance to check access for.
        action: The action to check permission for (e.g., 'read', 'update',
            'delete').
        db: The SQLAlchemy database session for querying permissions.

    Returns:
        bool: True if the user has permission through either global policies
            or resource-specific grants, False otherwise.

    Example:
        >>> if check_resource_permission(user, conference_room, "update", db):
        ...     # User can update this specific conference room
        ...     pass
    """
    # Check global permissions first
    if check_permission(user, "resource", action, db):
        return True

    # Check resource-specific permissions for the user directly
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
    """Grant a user permission to perform an action on a specific resource.

    Creates a new ResourcePermission record that grants the specified user
    the ability to perform the given action on the resource.

    Args:
        resource_id: The unique identifier of the resource to grant access to.
        user_id: The unique identifier of the user to grant permission to.
        action: The action to grant permission for (e.g., 'read', 'update',
            'delete').
        db: The SQLAlchemy database session for database operations.

    Returns:
        models.ResourcePermission: The newly created permission record.

    Note:
        This function does not check for duplicate permissions. Calling it
        multiple times with the same parameters will create duplicate records.
        Consider checking for existing permissions before calling.

    Example:
        >>> perm = grant_resource_permission(
        ...     resource_id=1,
        ...     user_id=2,
        ...     action="update",
        ...     db=db
        ... )
        >>> print(f"Granted permission ID: {perm.id}")
    """
    perm = models.ResourcePermission(
        resource_id=resource_id, user_id=user_id, action=action
    )
    db.add(perm)
    db.commit()
    return perm


def revoke_resource_permission(
    resource_id: int, user_id: int, action: str, db: Session
) -> bool:
    """Revoke a user's permission to perform an action on a specific resource.

    Removes the ResourcePermission record that grants the user access to
    perform the specified action on the resource, if such a record exists.

    Args:
        resource_id: The unique identifier of the resource to revoke access
            from.
        user_id: The unique identifier of the user to revoke permission from.
        action: The action to revoke permission for (e.g., 'read', 'update',
            'delete').
        db: The SQLAlchemy database session for database operations.

    Returns:
        bool: True if a permission was found and revoked, False if no matching
            permission existed.

    Example:
        >>> revoked = revoke_resource_permission(
        ...     resource_id=1,
        ...     user_id=2,
        ...     action="update",
        ...     db=db
        ... )
        >>> if revoked:
        ...     print("Permission successfully revoked")
    """
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
