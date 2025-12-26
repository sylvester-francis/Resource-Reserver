# Reservations API

## List Reservations

```http
GET /api/v1/reservations
Authorization: Bearer <token>
```

**Query Parameters:**

| Parameter     | Type | Description          |
| ------------- | ---- | -------------------- |
| `resource_id` | int  | Filter by resource   |
| `start_date`  | date | Filter by start date |
| `end_date`    | date | Filter by end date   |

## Create Reservation

```http
POST /api/v1/reservations
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "resource_id": 1,
  "start_time": "2024-01-15T09:00:00Z",
  "end_time": "2024-01-15T10:00:00Z",
  "notes": "Team standup meeting"
}
```

## Cancel Reservation

```http
DELETE /api/v1/reservations/{reservation_id}
Authorization: Bearer <token>
```

## Get My Reservations

```http
GET /api/v1/reservations/mine
Authorization: Bearer <token>
```
