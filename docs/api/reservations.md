# Reservations API

All endpoints require authentication.

## Endpoints

- `POST /api/v1/reservations` - create a reservation
- `POST /api/v1/reservations/recurring` - create recurring reservations
- `GET /api/v1/reservations/my` - list the current user's reservations
- `POST /api/v1/reservations/{reservation_id}/cancel` - cancel a reservation
- `GET /api/v1/reservations/{reservation_id}/history` - reservation history

## Authorization

| Action | Who Can Do It |
|--------|---------------|
| Create reservation | Any authenticated user |
| View own reservations | Reservation owner |
| Cancel reservation | Reservation owner OR admin |
| View reservation history | Any authenticated user |

## Notes

- Conflicts return HTTP 409
- Time values are handled as ISO 8601 timestamps
- Users can reserve resources that are currently in use, as long as the requested time slot is available
- Reservations can only be cancelled if they haven't started yet
