# Resources API

## List Resources

```http
GET /api/v1/resources
```

**Query Parameters:**

| Parameter | Type | Description                            |
| --------- | ---- | -------------------------------------- |
| `skip`    | int  | Number of items to skip                |
| `limit`   | int  | Maximum items to return (default: 100) |

**Response:**

```json
[
  {
    "id": 1,
    "name": "Conference Room A",
    "description": "Main conference room with projector",
    "capacity": 12,
    "created_at": "2024-01-15T10:00:00Z"
  }
]
```

## Get Resource

```http
GET /api/v1/resources/{resource_id}
```

## Create Resource

```http
POST /api/v1/resources
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "name": "Meeting Room B",
  "description": "Small meeting room",
  "capacity": 6
}
```

## Update Resource

```http
PUT /api/v1/resources/{resource_id}
Authorization: Bearer <token>
```

## Delete Resource

```http
DELETE /api/v1/resources/{resource_id}
Authorization: Bearer <token>
```

!!! warning "Admin Only" Creating, updating, and deleting resources requires admin privileges.
