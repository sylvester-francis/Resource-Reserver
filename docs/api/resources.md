# Resources API

All endpoints require authentication.

## Endpoints

- `POST /api/v1/resources` - create a resource
- `GET /api/v1/resources` - list resources (cursor pagination)
- `GET /api/v1/resources/search` - search resources with filters
- `POST /api/v1/resources/upload` - CSV import
- `GET /api/v1/resources/{resource_id}/schedule` - availability schedule
- `GET /api/v1/resources/{resource_id}/availability` - availability summary
- `PUT /api/v1/resources/{resource_id}/status/unavailable` - mark unavailable
- `PUT /api/v1/resources/{resource_id}/status/available` - mark available
- `GET /api/v1/resources/{resource_id}/status` - status details
- `PUT /api/v1/resources/{resource_id}/availability` - set base availability
- `GET /api/v1/resources/availability/summary` - system-wide summary

## Related endpoints

Business hours and blackout dates live under `/api/v1` and are documented in `admin/business-hours.md`.
