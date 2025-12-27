# Authentication and Access

## Core authentication

- `POST /api/v1/register` - create a user
- `POST /api/v1/token` - login and receive tokens
- `POST /api/v1/token/refresh` - refresh access token (query param `refresh_token`)
- `POST /api/v1/logout` - revoke refresh tokens

## Current user

- `GET /api/v1/users/me` - current user profile
- `PATCH /api/v1/users/me/preferences` - notification preferences

## Setup (first run)

- `GET /setup/status` - setup status
- `POST /setup/initialize` - create the first admin
- `POST /setup/unlock` - reopen setup with token

## MFA

- `POST /api/v1/auth/mfa/setup`
- `POST /api/v1/auth/mfa/verify`
- `POST /api/v1/auth/mfa/disable`
- `POST /api/v1/auth/mfa/backup-codes`

## Roles

- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `POST /api/v1/roles/assign`
- `DELETE /api/v1/roles/assign`
- `GET /api/v1/roles/my-roles`

## OAuth2

- `POST /api/v1/oauth/clients`
- `GET /api/v1/oauth/clients`
- `DELETE /api/v1/oauth/clients/{client_id}`
- `GET /api/v1/oauth/authorize`
- `POST /api/v1/oauth/token`
- `POST /api/v1/oauth/revoke`
- `POST /api/v1/oauth/introspect`
- `GET /api/v1/oauth/protected`
