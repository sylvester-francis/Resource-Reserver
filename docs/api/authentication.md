# Authentication API

## Login

Obtain an access token for API authentication.

```http
POST /api/v1/token
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**

| Field      | Type   | Required | Description     |
| ---------- | ------ | -------- | --------------- |
| `username` | string | Yes      | User's username |
| `password` | string | Yes      | User's password |

**Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/token" \
  -d "username=john&password=secret123"
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Register User

Create a new user account.

```http
POST /api/v1/users/
Content-Type: application/json
```

**Request Body:**

```json
{
  "username": "newuser",
  "password": "securepassword123"
}
```

**Response:**

```json
{
  "id": 1,
  "username": "newuser",
  "created_at": "2024-01-15T10:00:00Z"
}
```

## Get Current User

Get the authenticated user's profile.

```http
GET /api/v1/users/me
Authorization: Bearer <token>
```

**Response:**

```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "roles": ["user"],
  "created_at": "2024-01-15T10:00:00Z"
}
```

## Update Preferences

Update user notification preferences.

```http
PATCH /api/v1/users/me/preferences
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "email_notifications": true,
  "reminder_hours": 24
}
```

## Token Refresh

Tokens expire after 30 minutes by default. Request a new token before expiration.

!!! tip "Best Practice" Store the token securely and refresh it before it expires to maintain session continuity.
