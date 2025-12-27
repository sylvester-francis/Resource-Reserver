# Role Management

Role-based access control (RBAC) is used to manage permissions.

## Endpoints

- `GET /api/v1/roles` - list roles
- `POST /api/v1/roles` - create a role (admin)
- `POST /api/v1/roles/assign` - assign a role to a user (admin)
- `DELETE /api/v1/roles/assign` - remove a role (admin)
- `GET /api/v1/roles/my-roles` - current user's roles

## Notes

- Default roles are created during setup
- Admin-only actions require the admin role
