# Role Management

Role-based access control (RBAC) is used to manage permissions.

## Endpoints

- `GET /api/v1/roles` - list roles
- `POST /api/v1/roles` - create a role (admin)
- `POST /api/v1/roles/assign` - assign a role to a user (admin)
- `DELETE /api/v1/roles/assign` - remove a role (admin)
- `GET /api/v1/roles/my-roles` - current user's roles

## Admin-Only Actions

The following actions require the admin role:

| Category | Actions |
|----------|---------|
| **Resources** | Create, edit, delete resources |
| **Resources** | Upload CSV, set availability |
| **Resources** | Mark unavailable/available |
| **Tags** | Rename tags globally, delete tags |
| **Reservations** | Cancel any user's reservation |
| **Users** | Manage users and roles |
| **System** | Configure business hours, blackout dates |

## User Actions

All authenticated users can:

- View and search resources
- Create reservations on available resources
- Cancel their own reservations
- View their reservation history
- Join waitlists

## Notes

- Default roles are created during setup
- Admin-only actions require the admin role
- Users can only cancel reservations they own (admins can cancel any)
