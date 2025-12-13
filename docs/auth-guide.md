# Authentication, Authorization & OAuth2 Guide

## Overview

Resource-Reserver now includes enterprise-grade authentication and authorization features:

- **Multi-Factor Authentication (MFA/TOTP)**
- **Role-Based Access Control (RBAC)**
- **OAuth2 Authorization Server**
- **Resource-Level Permissions**

## Table of Contents

1. [Multi-Factor Authentication](#multi-factor-authentication)
2. [Role-Based Access Control](#role-based-access-control)
3. [OAuth2 Integration](#oauth2-integration)
4. [API Reference](#api-reference)

---

## Multi-Factor Authentication

### Setup MFA

**Endpoint**: `POST /auth/mfa/setup`

Enable two-factor authentication for your account.

**Request**:
```bash
curl -X POST http://localhost:8000/auth/mfa/setup \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "secret": "BASE32_SECRET",
  "qr_code": "data:image/png;base64,...",
  "backup_codes": ["CODE1", "CODE2", ...],
  "totp_uri": "otpauth://totp/..."
}
```

**Steps**:
1. Scan QR code with authenticator app (Google Authenticator, Authy, etc.)
2. Save backup codes in a secure location
3. Verify setup by entering a code

### Verify and Enable MFA

**Endpoint**: `POST /auth/mfa/verify`

**Request**:
```bash
curl -X POST http://localhost:8000/auth/mfa/verify \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'
```

### Disable MFA

**Endpoint**: `POST /auth/mfa/disable`

**Request**:
```bash
curl -X POST http://localhost:8000/auth/mfa/disable \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "your_password"}'
```

### Regenerate Backup Codes

**Endpoint**: `POST /auth/mfa/backup-codes`

---

## Role-Based Access Control

### Default Roles

Three default roles are created automatically:

| Role   | Description                    | Permissions                           |
|--------|--------------------------------|---------------------------------------|
| admin  | Full system access             | All operations on all resources       |
| user   | Standard user                  | Read resources, manage own reservations |
| guest  | Read-only access               | View resources only                   |

### List All Roles

**Endpoint**: `GET /roles/`

```bash
curl http://localhost:8000/roles/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Current User's Roles

**Endpoint**: `GET /roles/my-roles`

```bash
curl http://localhost:8000/roles/my-roles \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Assign Role (Admin Only)

**Endpoint**: `POST /roles/assign`

```bash
curl -X POST http://localhost:8000/roles/assign \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "role_name": "admin"}'
```

### Permission System

Permissions follow the format: `resource:action`

**Resources**:
- `resource` - Physical resources
- `reservation` - Bookings
- `user` - User management
- `oauth_client` - OAuth2 clients

**Actions**:
- `create` - Create new items
- `read` - View items
- `update` - Modify items
- `delete` - Remove items

**Example**: Check if user can delete resources
```python
from app.rbac import check_permission

if check_permission(user, "resource", "delete", db):
    # User has permission
    delete_resource()
```

---

## OAuth2 Integration

### Create OAuth2 Client

**Endpoint**: `POST /oauth/clients`

```bash
curl -X POST http://localhost:8000/oauth/clients \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "My Application",
    "redirect_uris": ["http://localhost:3000/callback"],
    "grant_types": "authorization_code",
    "scope": "read write"
  }'
```

**Response**:
```json
{
  "client_id": "CLIENT_ID",
  "client_secret": "CLIENT_SECRET",
  "client_name": "My Application",
  "message": "Save the client_secret now - it won't be shown again!"
}
```

> **Important**: Save the `client_secret` immediately - it cannot be retrieved later!

### Authorization Code Flow

Complete OAuth2 authorization code flow for accessing the API.

#### Step 1: Get Authorization Code

**Endpoint**: `GET /oauth/authorize`

```
http://localhost:8000/oauth/authorize?
  client_id=CLIENT_ID&
  redirect_uri=http://localhost:3000/callback&
  response_type=code&
  scope=read%20write&
  state=RANDOM_STATE
```

User must be logged in. Returns:
```json
{
  "code": "AUTHORIZATION_CODE",
  "redirect_uri": "http://localhost:3000/callback?code=...&state=..."
}
```

#### Step 2: Exchange Code for Token

**Endpoint**: `POST /oauth/token`

```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE" \
  -d "redirect_uri=http://localhost:3000/callback" \
  -d "client_id=CLIENT_ID" \
  -d "client_secret=CLIENT_SECRET"
```

**Response**:
```json
{
  "access_token": "ACCESS_TOKEN",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "REFRESH_TOKEN",
  "scope": "read write"
}
```

### Using Access Tokens

Include the access token in the `Authorization` header:

```bash
curl http://localhost:8000/oauth/protected \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### Refresh Token

**Endpoint**: `POST /oauth/token`

```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=REFRESH_TOKEN" \
  -d "client_id=CLIENT_ID" \
  -d "client_secret=CLIENT_SECRET"
```

### Token Introspection

**Endpoint**: `POST /oauth/introspect`

```bash
curl -X POST http://localhost:8000/oauth/introspect \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=ACCESS_TOKEN" \
  -d "client_id=CLIENT_ID" \
  -d "client_secret=CLIENT_SECRET"
```

**Response**:
```json
{
  "active": true,
  "client_id": "CLIENT_ID",
  "username": 1,
  "scope": "read write",
  "exp": 1234567890,
  "iat": 1234564290
}
```

### Revoke Token

**Endpoint**: `POST /oauth/revoke`

```bash
curl -X POST http://localhost:8000/oauth/revoke \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=ACCESS_TOKEN" \
  -d "client_id=CLIENT_ID" \
  -d "client_secret=CLIENT_SECRET"
```

### OAuth2 Scopes

| Scope | Description |
|-------|-------------|
| `read` | Read access to resources and reservations |
| `write` | Create and update resources and reservations |
| `delete` | Delete resources and reservations |
| `admin` | Administrative access |
| `user:profile` | Access user profile information |

---

## Database Migration

Run the migration script to add new tables:

```bash
cd /path/to/Resource-Reserver
python scripts/migrate_auth.py
```

This will:
- Create new tables (roles, oauth2_clients, oauth2_tokens, etc.)
- Seed default roles (admin, user, guest)
- Assign 'user' role to all existing users

---

## Security Best Practices

### MFA
- Always enable MFA for admin accounts
- Store backup codes securely (password manager, safe place)
- Regenerate backup codes after use

### OAuth2
- Keep client secrets secure - treat like passwords
- Use HTTPS in production for redirect URIs
- Implement PKCE for public clients (mobile/SPA apps)
- Rotate tokens regularly
- Revoke tokens when no longer needed

### Roles
- Follow principle of least privilege
- Assign minimum required roles
- Regularly audit role assignments
- Use resource-level permissions for fine-grained control

---

## Examples

### Python Client Example

```python
import requests

# OAuth2 Authorization Code Flow
class APIClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
    
    def authorize(self, code, redirect_uri):
        """Exchange authorization code for access token."""
        response = requests.post(
            "http://localhost:8000/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )
        data = response.json()
        self.access_token = data["access_token"]
        return data
    
    def get_resources(self):
        """Get resources using access token."""
        response = requests.get(
            "http://localhost:8000/resources/search",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        return response.json()

# Usage
client = APIClient("YOUR_CLIENT_ID", "YOUR_CLIENT_SECRET")
client.authorize(code="AUTH_CODE", redirect_uri="http://localhost:3000/callback")
resources = client.get_resources()
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

class APIClient {
  constructor(clientId, clientSecret) {
    this.clientId = clientId;
    this.clientSecret = clientSecret;
    this.accessToken = null;
  }
  
  async authorize(code, redirectUri) {
    const response = await axios.post(
      'http://localhost:8000/oauth/token',
      new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: redirectUri,
        client_id: this.clientId,
        client_secret: this.clientSecret
      })
    );
    
    this.accessToken = response.data.access_token;
    return response.data;
  }
  
  async getResources() {
    const response = await axios.get(
      'http://localhost:8000/resources/search',
      {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      }
    );
    
    return response.data;
  }
}

// Usage
const client = new APIClient('YOUR_CLIENT_ID', 'YOUR_CLIENT_SECRET');
await client.authorize('AUTH_CODE', 'http://localhost:3000/callback');
const resources = await client.getResources();
```

---

## Troubleshooting

### MFA Issues

**Problem**: QR code won't scan
- Solution: Manually enter the secret into your authenticator app

**Problem**: Code always invalid
- Solution: Check your device time is synchronized (TOTP requires accurate time)

### OAuth2 Issues

**Problem**: "Invalid redirect_uri"
- Solution: Ensure redirect_uri exactly matches one registered with the client

**Problem**: "Invalid client credentials"
- Solution: Double-check client_id and client_secret are correct

**Problem**: Token expired
- Solution: Use refresh_token to get a new access_token

### Permission Issues

**Problem**: 403 Forbidden
- Solution: Check user has required role/permission using `/roles/my-roles`

---

## API Reference

### MFA Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/mfa/setup` | Setup MFA for user |
| POST | `/auth/mfa/verify` | Verify and enable MFA |
| POST | `/auth/mfa/disable` | Disable MFA |
| POST | `/auth/mfa/backup-codes` | Regenerate backup codes |

### Role Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/roles/` | List all roles |
| POST | `/roles/` | Create role (admin only) |
| GET | `/roles/my-roles` | Get current user's roles |
| POST | `/roles/assign` | Assign role to user (admin) |
| DELETE | `/roles/assign` | Remove role from user (admin) |

### OAuth2 Endpoints

| Method | Endpoint| Description |
|--------|----------|-------------|
| POST | `/oauth/clients` | Create OAuth2 client |
| GET | `/oauth/clients` | List user's clients |
| DELETE | `/oauth/clients/{id}` | Delete client |
| GET | `/oauth/authorize` | Authorization endpoint |
| POST | `/oauth/token` | Token endpoint |
| POST | `/oauth/revoke` | Revoke token |
| POST | `/oauth/introspect` | Introspect token |
| GET | `/oauth/protected` | Example protected endpoint |

---

## Next Steps

1. Enable MFA for your account
2. Create an OAuth2 client for your app
3. Implement authorization code flow
4. Assign appropriate roles to users

For more information, see the main [README.md](../README.md)
