# Webhooks API

All endpoints require authentication.

## Core endpoints

- `GET /api/v1/webhooks/events` - list supported event types
- `GET /api/v1/webhooks/signature-example` - signature verification examples
- `POST /api/v1/webhooks` - create a webhook
- `GET /api/v1/webhooks` - list webhooks
- `GET /api/v1/webhooks/{webhook_id}` - get a webhook
- `PATCH /api/v1/webhooks/{webhook_id}` - update a webhook
- `DELETE /api/v1/webhooks/{webhook_id}` - delete a webhook

## Deliveries

- `GET /api/v1/webhooks/{webhook_id}/deliveries` - delivery history
- `GET /api/v1/webhooks/{webhook_id}/deliveries/{delivery_id}` - delivery details
- `POST /api/v1/webhooks/{webhook_id}/deliveries/{delivery_id}/retry` - retry

## Testing

- `POST /api/v1/webhooks/{webhook_id}/test` - send a test event

## Signature verification

Payloads include the `X-Webhook-Signature` header using HMAC-SHA256:

```
X-Webhook-Signature: sha256=<signature>
```

Use `/api/v1/webhooks/signature-example` for ready-to-use examples.
