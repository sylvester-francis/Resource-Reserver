# Webhooks API

## Overview

Webhooks allow you to receive real-time notifications about events in Resource Reserver.

## Available Events

| Event                   | Description                 |
| ----------------------- | --------------------------- |
| `reservation.created`   | New reservation created     |
| `reservation.updated`   | Reservation modified        |
| `reservation.cancelled` | Reservation cancelled       |
| `resource.created`      | New resource added          |
| `resource.updated`      | Resource modified           |
| `user.created`          | New user registered         |
| `waitlist.promoted`     | User promoted from waitlist |

## Register Webhook

```http
POST /api/v1/webhooks
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "url": "https://your-server.com/webhook",
  "events": ["reservation.created", "reservation.cancelled"]
}
```

## Webhook Payload

```json
{
  "event": "reservation.created",
  "timestamp": "2024-01-15T10:00:00Z",
  "data": {
    "reservation_id": 123,
    "resource_id": 1,
    "user_id": 5
  }
}
```

## Signature Verification

Webhooks include an HMAC-SHA256 signature in the `X-Webhook-Signature` header:

```python
import hmac
import hashlib


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```
