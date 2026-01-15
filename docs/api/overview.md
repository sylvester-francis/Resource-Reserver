# API Overview

Base URL:

```
http://localhost:8000
```

For Docker deployments using API proxy mode, the frontend proxies requests to `/api/v1/*`.

## Authentication

Most endpoints require a bearer token:

```
Authorization: Bearer <access_token>
```

Tokens are issued by `POST /api/v1/token` and refreshed via `POST /api/v1/token/refresh`.

## Authorization

Endpoints are divided into:

- **Public endpoints**: Available to any authenticated user (e.g., list resources, create reservations)
- **Owner endpoints**: Restricted to the owner of a record (e.g., cancel own reservation)
- **Admin endpoints**: Restricted to users with admin role (e.g., create/edit resources, manage tags)

See individual endpoint documentation for specific authorization requirements.

## Pagination

Many list endpoints use cursor-based pagination:

- `cursor`: pagination cursor
- `limit`: number of items per page
- `sort_by`, `sort_order`: sorting
- `include_total`: include a total count in the response

## Rate limits

Rate limits are controlled by `RATE_LIMIT_*` settings. When exceeded, the API returns HTTP 429.

## Timezones

Timestamps are ISO 8601 strings. Use timezone-aware values when possible.

## WebSocket

A real-time channel is available at:

```
/ws?token=<access_token>
```

For API proxy mode deployments, WebSocket is available at `/ws` (proxied through the frontend).
