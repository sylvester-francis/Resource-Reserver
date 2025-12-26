# API Overview

Resource Reserver provides a comprehensive REST API for all operations.

## Base URL

```
https://your-domain.com/api/v1
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Obtaining a Token

```bash
curl -X POST "http://localhost:8000/api/v1/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the `Authorization` header:

```bash
curl -X GET "http://localhost:8000/api/v1/resources" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

## API Versioning

The API supports versioning via URL path or header:

=== "URL Path (Recommended)" `     GET /api/v1/resources     GET /api/v2/resources     `

=== "Header" `bash     curl -H "X-API-Version: 1" /api/resources     `

## Response Format

All responses are JSON with consistent structure:

### Success Response

```json
{
  "id": 1,
  "name": "Conference Room A",
  "capacity": 12,
  "created_at": "2024-01-15T10:00:00Z"
}
```

### Error Response

```json
{
  "detail": "Resource not found"
}
```

### Paginated Response

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

## Rate Limiting

API requests are rate limited:

| Tier          | Requests/Minute |
| ------------- | --------------- |
| Anonymous     | 20              |
| Authenticated | 100             |
| Premium       | 500             |
| Admin         | 1000            |

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705312800
```

## Common Endpoints

| Endpoint            | Description         |
| ------------------- | ------------------- |
| `POST /token`       | Obtain access token |
| `GET /resources`    | List resources      |
| `GET /reservations` | List reservations   |
| `GET /health`       | Health check        |
| `GET /metrics`      | Prometheus metrics  |

## Interactive Documentation

Access interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
