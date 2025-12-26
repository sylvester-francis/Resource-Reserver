"""Webhook management API endpoints.

Provides endpoints for:
- Registering webhooks
- Managing webhook subscriptions
- Viewing delivery history
- Testing webhooks

Author: Sylvester-Francis
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.database import get_db
from app.webhook_service import (
    WebhookEventType,
    WebhookService,
    get_event_types,
    sign_payload,
)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


# ============================================================================
# Schemas
# ============================================================================


class WebhookCreate(BaseModel):
    """Create a new webhook."""

    url: HttpUrl = Field(..., description="URL to send webhook events to")
    events: list[str] = Field(
        ..., min_length=1, description="List of event types to subscribe to"
    )
    description: str | None = Field(None, max_length=255)


class WebhookUpdate(BaseModel):
    """Update webhook configuration."""

    url: HttpUrl | None = None
    events: list[str] | None = None
    description: str | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    """Webhook configuration response."""

    id: int
    url: str
    events: list[str]
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookWithSecretResponse(WebhookResponse):
    """Webhook response including secret (only on create/regenerate)."""

    secret: str


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery record response."""

    id: int
    event_type: str
    status: str
    status_code: int | None
    error_message: str | None
    created_at: datetime
    delivered_at: datetime | None
    retry_count: int

    model_config = {"from_attributes": True}


class EventTypeResponse(BaseModel):
    """Event type information."""

    type: str
    description: str


class WebhookTestRequest(BaseModel):
    """Request to test a webhook."""

    event_type: str = Field(
        WebhookEventType.RESOURCE_CREATED.value, description="Event type to simulate"
    )


class WebhookTestResponse(BaseModel):
    """Response from webhook test."""

    success: bool
    message: str
    delivery_id: int | None = None


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/events", response_model=list[EventTypeResponse])
def list_event_types():
    """Get list of available webhook event types."""
    return get_event_types()


@router.get("/signature-example")
def get_signature_example_early(
    current_user: models.User = Depends(get_current_user),
):
    """Get an example of how to verify webhook signatures.

    Returns example code for verifying HMAC-SHA256 signatures.
    """
    example_payload = (
        '{"event":"reservation.created","timestamp":"2025-01-01T00:00:00Z","data":{}}'
    )
    example_secret = "your_webhook_secret"  # nosec B105 - intentional example
    example_signature = sign_payload(example_payload, example_secret)

    return {
        "algorithm": "HMAC-SHA256",
        "header": "X-Webhook-Signature",
        "format": "sha256=<signature>",
        "example": {
            "payload": example_payload,
            "secret": example_secret,
            "signature": example_signature,
        },
        "python_example": """
import hmac
import hashlib

def verify_signature(payload: str, secret: str, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
""",
        "javascript_example": """
const crypto = require('crypto');

function verifySignature(payload, secret, signature) {
    const expected = 'sha256=' + crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');
    return crypto.timingSafeEqual(
        Buffer.from(expected),
        Buffer.from(signature)
    );
}
""",
    }


@router.post(
    "/", response_model=WebhookWithSecretResponse, status_code=status.HTTP_201_CREATED
)
def create_webhook(
    data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Register a new webhook.

    Returns the webhook configuration including the secret.
    The secret is only returned on creation - store it securely.
    """
    # Validate event types
    valid_events = {e.value for e in WebhookEventType}
    invalid_events = set(data.events) - valid_events
    if invalid_events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event types: {', '.join(invalid_events)}",
        )

    service = WebhookService(db)
    webhook = service.create_webhook(
        user_id=current_user.id,
        url=str(data.url),
        events=data.events,
        description=data.description,
    )

    return WebhookWithSecretResponse(
        id=webhook.id,
        url=webhook.url,
        secret=webhook.secret,
        events=webhook.events,
        description=webhook.description,
        is_active=webhook.is_active,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.get("/", response_model=list[WebhookResponse])
def list_webhooks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all webhooks for the current user."""
    service = WebhookService(db)
    return service.get_user_webhooks(current_user.id)


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a specific webhook."""
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    if webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this webhook",
        )

    return webhook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: int,
    data: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a webhook configuration."""
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    if webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this webhook",
        )

    # Validate event types if provided
    if data.events:
        valid_events = {e.value for e in WebhookEventType}
        invalid_events = set(data.events) - valid_events
        if invalid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event types: {', '.join(invalid_events)}",
            )

    updated = service.update_webhook(
        webhook_id=webhook_id,
        url=str(data.url) if data.url else None,
        events=data.events,
        description=data.description,
        is_active=data.is_active,
    )

    return updated


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a webhook."""
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    if webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this webhook",
        )

    service.delete_webhook(webhook_id)


@router.post(
    "/{webhook_id}/regenerate-secret", response_model=WebhookWithSecretResponse
)
def regenerate_webhook_secret(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Regenerate the secret for a webhook.

    Use this if you believe the secret has been compromised.
    """
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    if webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this webhook",
        )

    updated = service.regenerate_secret(webhook_id)

    return WebhookWithSecretResponse(
        id=updated.id,
        url=updated.url,
        secret=updated.secret,
        events=updated.events,
        description=updated.description,
        is_active=updated.is_active,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
def list_webhook_deliveries(
    webhook_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get delivery history for a webhook."""
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    if webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this webhook",
        )

    return service.get_delivery_history(webhook_id, limit)


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: int,
    data: WebhookTestRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Send a test event to a webhook.

    This allows you to verify your webhook endpoint is working correctly.
    """
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    if webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to test this webhook",
        )

    # Validate event type
    try:
        WebhookEventType(data.event_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event type: {data.event_type}",
        ) from None

    # Create test payload
    test_payload: dict[str, Any] = {
        "test": True,
        "message": "This is a test webhook delivery",
        "webhook_id": webhook_id,
        "triggered_by": current_user.username,
        "triggered_at": datetime.now(UTC).isoformat(),
    }

    # Create delivery
    delivery = service.create_delivery(
        webhook_id=webhook_id,
        event_type=data.event_type,
        payload={
            "event": data.event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": test_payload,
        },
    )

    # Attempt delivery
    from app.webhook_service import deliver_webhook

    success = await deliver_webhook(webhook, delivery, db)

    # Refresh delivery to get updated status
    db.refresh(delivery)

    return WebhookTestResponse(
        success=success,
        message="Test webhook delivered successfully"
        if success
        else f"Test webhook delivery failed: {delivery.error_message or 'Unknown error'}",
        delivery_id=delivery.id,
    )


@router.get("/{webhook_id}/deliveries/{delivery_id}")
def get_delivery_details(
    webhook_id: int,
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get details of a specific delivery including payload."""
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    if webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this webhook",
        )

    delivery = (
        db.query(models.WebhookDelivery)
        .filter(
            models.WebhookDelivery.id == delivery_id,
            models.WebhookDelivery.webhook_id == webhook_id,
        )
        .first()
    )

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found"
        )

    return {
        "id": delivery.id,
        "webhook_id": delivery.webhook_id,
        "event_type": delivery.event_type,
        "payload": delivery.payload,
        "status": delivery.status,
        "status_code": delivery.status_code,
        "response_body": delivery.response_body,
        "error_message": delivery.error_message,
        "created_at": delivery.created_at,
        "delivered_at": delivery.delivered_at,
        "retry_count": delivery.retry_count,
        "next_retry_at": delivery.next_retry_at,
    }


@router.post("/{webhook_id}/deliveries/{delivery_id}/retry")
async def retry_delivery(
    webhook_id: int,
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Manually retry a failed delivery."""
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    if webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this webhook",
        )

    delivery = (
        db.query(models.WebhookDelivery)
        .filter(
            models.WebhookDelivery.id == delivery_id,
            models.WebhookDelivery.webhook_id == webhook_id,
        )
        .first()
    )

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found"
        )

    if delivery.status == "delivered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery was already successful",
        )

    # Reset status for retry
    delivery.status = "pending"
    delivery.next_retry_at = None
    db.commit()

    # Attempt delivery
    from app.webhook_service import deliver_webhook

    success = await deliver_webhook(webhook, delivery, db)

    db.refresh(delivery)

    return {
        "success": success,
        "message": "Retry successful"
        if success
        else f"Retry failed: {delivery.error_message}",
        "status": delivery.status,
    }
