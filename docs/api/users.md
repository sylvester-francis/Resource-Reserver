# Users API

## List Users (Admin)

```http
GET /api/v1/users
Authorization: Bearer <admin_token>
```

## Get User

```http
GET /api/v1/users/{user_id}
Authorization: Bearer <token>
```

## Update User

```http
PUT /api/v1/users/{user_id}
Authorization: Bearer <token>
```

## Assign Role

```http
POST /api/v1/users/{user_id}/roles
Authorization: Bearer <admin_token>
Content-Type: application/json
```

```json
{
  "role_name": "admin"
}
```
