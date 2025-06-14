# API Reference

## 🔌 Complete API Documentation

Base URL: `http://localhost:8000` (or your deployed backend URL)

All authenticated endpoints require an `Authorization: Bearer <token>` header.

## Authentication

### Register User
```http
POST /register
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "john_doe",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Login
```http
POST /token
Content-Type: application/x-www-form-urlencoded

username=john_doe&password=secure_password
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Resources

### Create Resource
```http
POST /resources
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Conference Room A",
  "tags": ["meeting", "projector", "whiteboard"],
  "available": true
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Conference Room A",
  "tags": ["meeting", "projector", "whiteboard"],
  "available": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### List All Resources
```http
GET /resources
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Conference Room A",
    "tags": ["meeting", "projector"],
    "available": true,
    "current_availability": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### Search Resources
```http
GET /resources/search?q=conference&available_only=true&available_from=2024-01-16T09:00:00Z&available_until=2024-01-16T17:00:00Z
```

**Query Parameters:**
- `q` (string, optional): Search term for resource names
- `available_only` (boolean, default: true): Filter to only available resources
- `available_from` (datetime, optional): Check availability from this time
- `available_until` (datetime, optional): Check availability until this time

**Response:**
```json
[
  {
    "id": 1,
    "name": "Conference Room A",
    "tags": ["meeting", "projector"],
    "available": true,
    "current_availability": true
  }
]
```

### Get Resource Availability Schedule
```http
GET /resources/1/availability?days_ahead=7
```

**Query Parameters:**
- `days_ahead` (integer, default: 7): Number of days to show schedule for

**Response:**
```json
{
  "success": true,
  "data": {
    "resource_id": 1,
    "resource_name": "Conference Room A",
    "current_time": "2024-01-15T10:30:00Z",
    "is_currently_available": true,
    "base_available": true,
    "schedule": [
      {
        "date": "2024-01-15",
        "time_slots": [
          {
            "time": "09:00",
            "available": true
          },
          {
            "time": "10:00",
            "available": false
          }
        ]
      }
    ],
    "reservations": [
      {
        "id": 1,
        "start_time": "2024-01-15T10:00:00Z",
        "end_time": "2024-01-15T11:00:00Z",
        "user_id": 1,
        "status": "active"
      }
    ]
  }
}
```

### Update Resource Availability
```http
PUT /resources/1/availability
Authorization: Bearer <token>
Content-Type: application/json

{
  "available": false
}
```

**Response:**
```json
{
  "message": "Resource availability updated to unavailable",
  "resource": {
    "id": 1,
    "name": "Conference Room A",
    "available": false
  }
}
```

### Upload Resources from CSV
```http
POST /resources/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: resources.csv
```

**CSV Format:**
```csv
name,tags,available
Conference Room A,"meeting,projector",true
Conference Room B,"meeting,video-call",true
Equipment Laptop,"laptop,portable",false
```

**Response:**
```json
{
  "created_count": 3,
  "errors": []
}
```

## Reservations

### Create Reservation
```http
POST /reservations
Authorization: Bearer <token>
Content-Type: application/json

{
  "resource_id": 1,
  "start_time": "2024-01-16T09:00:00Z",
  "end_time": "2024-01-16T10:00:00Z"
}
```

**Response:**
```json
{
  "id": 1,
  "resource_id": 1,
  "user_id": 1,
  "start_time": "2024-01-16T09:00:00Z",
  "end_time": "2024-01-16T10:00:00Z",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "resource": {
    "id": 1,
    "name": "Conference Room A"
  }
}
```

### Get My Reservations
```http
GET /reservations/my?include_cancelled=false
Authorization: Bearer <token>
```

**Query Parameters:**
- `include_cancelled` (boolean, default: false): Include cancelled reservations

**Response:**
```json
[
  {
    "id": 1,
    "resource_id": 1,
    "start_time": "2024-01-16T09:00:00Z",
    "end_time": "2024-01-16T10:00:00Z",
    "status": "active",
    "resource": {
      "id": 1,
      "name": "Conference Room A"
    }
  }
]
```

### Cancel Reservation
```http
POST /reservations/1/cancel
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "Meeting moved to next week"
}
```

**Response:**
```json
{
  "message": "Reservation cancelled successfully",
  "reservation_id": 1,
  "cancelled_at": "2024-01-15T10:35:00Z"
}
```

### Get Reservation History
```http
GET /reservations/1/history
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 1,
    "reservation_id": 1,
    "action": "created",
    "user_id": 1,
    "details": "Reserved Conference Room A from 2024-01-16 09:00 to 10:00",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "reservation_id": 1,
    "action": "cancelled",
    "user_id": 1,
    "details": "Cancelled reservation (Reason: Meeting moved to next week)",
    "timestamp": "2024-01-15T10:35:00Z"
  }
]
```

## System Management

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "database": "healthy",
  "api": "healthy",
  "resources_count": 5,
  "background_tasks": {
    "cleanup_task": "running"
  }
}
```

### Availability Summary
```http
GET /resources/availability/summary
```

**Response:**
```json
{
  "total_resources": 10,
  "available_now": 7,
  "unavailable_now": 3,
  "currently_in_use": 2,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Manual Cleanup (Admin)
```http
POST /admin/cleanup-expired
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Successfully cleaned up 3 expired reservations",
  "expired_count": 3,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Resource not found",
  "status_code": 404
}
```

### Common Error Codes

- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Missing or invalid authentication token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **409 Conflict**: Reservation time conflict
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

## Rate Limits

- **Authentication endpoints**: 5 requests per minute per IP
- **Resource creation**: 10 requests per minute per user
- **Search endpoints**: 60 requests per minute per user
- **Other endpoints**: 100 requests per minute per user

## Webhooks (Future Feature)

Configure webhooks to receive real-time notifications:

```json
{
  "url": "https://your-app.com/webhooks/resource-reserver",
  "events": ["reservation.created", "reservation.cancelled", "resource.disabled"],
  "secret": "webhook-secret-for-verification"
}
```

## SDK Examples

### Python
```python
import requests

class ResourceReserver:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def create_resource(self, name, tags=None, available=True):
        data = {"name": name, "tags": tags or [], "available": available}
        response = requests.post(f"{self.base_url}/resources", 
                               json=data, headers=self.headers)
        return response.json()
    
    def search_resources(self, query=None, available_only=True):
        params = {"available_only": available_only}
        if query:
            params["q"] = query
        response = requests.get(f"{self.base_url}/resources/search", 
                              params=params)
        return response.json()

# Usage
client = ResourceReserver("http://localhost:8000", "your-token")
resource = client.create_resource("Meeting Room", ["meeting", "projector"])
```

### JavaScript/Node.js
```javascript
class ResourceReserver {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.headers = {'Authorization': `Bearer ${token}`};
    }
    
    async createReservation(resourceId, startTime, endTime) {
        const response = await fetch(`${this.baseUrl}/reservations`, {
            method: 'POST',
            headers: {...this.headers, 'Content-Type': 'application/json'},
            body: JSON.stringify({
                resource_id: resourceId,
                start_time: startTime,
                end_time: endTime
            })
        });
        return await response.json();
    }
}

// Usage
const client = new ResourceReserver('http://localhost:8000', 'your-token');
const reservation = await client.createReservation(1, '2024-01-16T09:00:00Z', '2024-01-16T10:00:00Z');
```

### cURL Examples

**Create a resource:**
```bash
curl -X POST http://localhost:8000/resources \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"name":"Conference Room","tags":["meeting"],"available":true}'
```

**Search resources:**
```bash
curl "http://localhost:8000/resources/search?q=conference&available_only=true"
```

**Create reservation:**
```bash
curl -X POST http://localhost:8000/reservations \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"resource_id":1,"start_time":"2024-01-16T09:00:00Z","end_time":"2024-01-16T10:00:00Z"}'
```

## OpenAPI Schema

The complete OpenAPI 3.0 schema is available at:
- Interactive documentation: `http://localhost:8000/docs`
- Raw schema: `http://localhost:8000/openapi.json`

For integration help, see our [Integration Examples](integration-examples.md) or [Quick Start Guide](quick-start.md).