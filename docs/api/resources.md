# Resources API

All endpoints require authentication. Endpoints that modify resources require **admin privileges**.

## Endpoints

### Public Endpoints (Any Authenticated User)
- `GET /api/v1/resources` - list resources (cursor pagination)
- `GET /api/v1/resources/search` - search resources with filters
- `GET /api/v1/resources/tags` - list all unique tags
- `GET /api/v1/resources/{resource_id}/schedule` - availability schedule
- `GET /api/v1/resources/{resource_id}/availability` - availability summary
- `GET /api/v1/resources/{resource_id}/status` - status details
- `GET /api/v1/resources/availability/summary` - system-wide summary

### Admin-Only Endpoints
- `POST /api/v1/resources` - create a resource
- `PUT /api/v1/resources/{resource_id}` - update resource (name, description, tags)
- `POST /api/v1/resources/upload` - CSV import
- `PUT /api/v1/resources/{resource_id}/status/unavailable` - mark unavailable
- `PUT /api/v1/resources/{resource_id}/status/available` - mark available
- `PUT /api/v1/resources/{resource_id}/availability` - set base availability
- `GET /api/v1/resources/tags/details` - list tags with usage counts
- `PUT /api/v1/resources/tags/rename` - rename a tag globally
- `DELETE /api/v1/resources/tags/{tag_name}` - delete a tag globally

## Tag Filtering

When filtering resources by tags, the filter uses **AND logic** - resources must have **all** selected tags to be included in results.

## Resource Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique identifier |
| `name` | string | Resource name (1-200 characters) |
| `description` | string | Optional description text |
| `tags` | array | List of categorization tags |
| `available` | bool | Base availability flag |
| `status` | string | Current status: `available`, `in_use`, `unavailable` |

## Related endpoints

Business hours and blackout dates live under `/api/v1` and are documented in `admin/business-hours.md`.
