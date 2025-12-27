# Reservations API

All endpoints require authentication.

## Endpoints

- `POST /api/v1/reservations` - create a reservation
- `POST /api/v1/reservations/recurring` - create recurring reservations
- `GET /api/v1/reservations/my` - list the current user's reservations
- `POST /api/v1/reservations/{reservation_id}/cancel` - cancel a reservation
- `GET /api/v1/reservations/{reservation_id}/history` - reservation history

## Notes

- Conflicts return HTTP 409
- Time values are handled as ISO 8601 timestamps
