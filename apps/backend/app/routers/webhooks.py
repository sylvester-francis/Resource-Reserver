"""Webhook management API endpoints.

This module provides a comprehensive REST API for managing webhooks within the
Resource Reserver application. It enables users to register webhook endpoints,
subscribe to specific events, view delivery history, and test webhook configurations.

Features:
    - Webhook registration with custom event subscriptions
    - HMAC-SHA256 signature verification for secure payload delivery
    - Delivery history tracking with detailed status information
    - Manual retry capability for failed deliveries
    - Test endpoint for verifying webhook configurations
    - Secret regeneration for compromised credentials

Example Usage:
    Register a new webhook::

        POST /api/v1/webhooks
        {
            "url": "https://example.com/webhook",
            "events": ["reservation.created", "reservation.cancelled"],
            "description": "My notification webhook"
        }

    Test the webhook::

        POST /api/v1/webhooks/{webhook_id}/test
        {
            "event_type": "reservation.created"
        }

    List all webhooks::

        GET /api/v1/webhooks

    View delivery history::

        GET /api/v1/webhooks/{webhook_id}/deliveries

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
    """Get all available webhook event types.

    Retrieves a list of all event types that can be subscribed to when
    creating or updating a webhook. Each event type includes a description
    explaining when the event is triggered.

    Returns:
        list[EventTypeResponse]: A list of event type objects, each containing:
            - type: The event type identifier string
            - description: Human-readable description of the event
    """
    return get_event_types()


@router.get("/signature-example")
def get_signature_example_early(
    current_user: models.User = Depends(get_current_user),
):
    """Get an example of how to verify webhook signatures.

    Provides documentation and example code for verifying HMAC-SHA256
    signatures on incoming webhook payloads. This helps developers
    implement secure webhook receivers that validate payload authenticity.

    Args:
        current_user: The authenticated user making the request. Injected
            by FastAPI dependency injection.

    Returns:
        dict: A dictionary containing:
            - algorithm: The signature algorithm used (HMAC-SHA256)
            - header: The HTTP header name containing the signature
            - format: The signature format pattern
            - example: Sample payload, secret, and resulting signature
            - python_example: Python code snippet for verification
            - javascript_example: JavaScript code snippet for verification
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
    """Register a new webhook subscription.

    Creates a new webhook endpoint that will receive HTTP POST requests
    when subscribed events occur. The response includes a secret key
    that should be stored securely for signature verification.

    Note:
        The secret is only returned once during creation. Store it
        immediately in a secure location. If lost, use the
        regenerate-secret endpoint to create a new one.

    Args:
        data: The webhook configuration containing:
            - url: The HTTPS endpoint URL to receive webhook events
            - events: List of event type strings to subscribe to
            - description: Optional human-readable description
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user creating the webhook.

    Returns:
        WebhookWithSecretResponse: The created webhook configuration
            including the secret key for signature verification.

    Raises:
        HTTPException: 400 Bad Request if any event types in the
            subscription list are invalid or unrecognized.
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
    """List all webhooks for the current user.

    Retrieves all webhook configurations belonging to the authenticated
    user. The response does not include webhook secrets for security.

    Args:
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user whose webhooks to retrieve.

    Returns:
        list[WebhookResponse]: A list of webhook configurations owned
            by the current user, excluding secret keys.
    """
    service = WebhookService(db)
    return service.get_user_webhooks(current_user.id)


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a specific webhook by ID.

    Retrieves the configuration for a single webhook. Users can only
    access webhooks they own.

    Args:
        webhook_id: The unique identifier of the webhook to retrieve.
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user making the request.

    Returns:
        WebhookResponse: The webhook configuration, excluding the secret.

    Raises:
        HTTPException: 404 Not Found if the webhook does not exist.
        HTTPException: 403 Forbidden if the user does not own the webhook.
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
    """Update a webhook configuration.

    Allows partial updates to an existing webhook. Only the fields
    provided in the request body will be modified; omitted fields
    retain their current values.

    Args:
        webhook_id: The unique identifier of the webhook to update.
        data: The fields to update. All fields are optional:
            - url: New endpoint URL for webhook delivery
            - events: New list of event types to subscribe to
            - description: Updated description text
            - is_active: Enable or disable the webhook
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user making the request.

    Returns:
        WebhookResponse: The updated webhook configuration.

    Raises:
        HTTPException: 404 Not Found if the webhook does not exist.
        HTTPException: 403 Forbidden if the user does not own the webhook.
        HTTPException: 400 Bad Request if any provided event types are invalid.
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
    """Delete a webhook.

    Permanently removes a webhook and all its associated delivery history.
    This action cannot be undone.

    Args:
        webhook_id: The unique identifier of the webhook to delete.
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user making the request.

    Returns:
        None: Returns HTTP 204 No Content on success.

    Raises:
        HTTPException: 404 Not Found if the webhook does not exist.
        HTTPException: 403 Forbidden if the user does not own the webhook.
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

    Creates a new cryptographically secure secret for the webhook,
    invalidating the previous secret. Use this endpoint if you believe
    the current secret has been compromised or exposed.

    Note:
        After regenerating, update your webhook receiver to use the
        new secret for signature verification. The old secret will
        immediately stop working.

    Args:
        webhook_id: The unique identifier of the webhook.
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user making the request.

    Returns:
        WebhookWithSecretResponse: The webhook configuration with the
            newly generated secret key.

    Raises:
        HTTPException: 404 Not Found if the webhook does not exist.
        HTTPException: 403 Forbidden if the user does not own the webhook.
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
    """Get delivery history for a webhook.

    Retrieves a list of recent webhook delivery attempts, ordered by
    creation time descending (newest first). This is useful for debugging
    delivery issues and monitoring webhook health.

    Args:
        webhook_id: The unique identifier of the webhook.
        limit: Maximum number of delivery records to return.
            Defaults to 50, must be between 1 and 100.
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user making the request.

    Returns:
        list[WebhookDeliveryResponse]: A list of delivery records containing
            event type, status, timestamps, and error information.

    Raises:
        HTTPException: 404 Not Found if the webhook does not exist.
        HTTPException: 403 Forbidden if the user does not own the webhook.
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

    Triggers an immediate delivery attempt to the webhook endpoint with
    a test payload. This allows verification that the webhook receiver
    is correctly configured and can process incoming events.

    The test payload includes a "test": true flag to distinguish it
    from real events.

    Args:
        webhook_id: The unique identifier of the webhook to test.
        data: Test configuration containing:
            - event_type: The type of event to simulate (defaults to
              resource.created)
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user making the request.

    Returns:
        WebhookTestResponse: Result of the test containing:
            - success: Whether the delivery succeeded
            - message: Descriptive result message
            - delivery_id: ID of the delivery record for further inspection

    Raises:
        HTTPException: 404 Not Found if the webhook does not exist.
        HTTPException: 403 Forbidden if the user does not own the webhook.
        HTTPException: 400 Bad Request if the event type is invalid.
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

    # Create delivery record
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
    """Get details of a specific delivery including payload.

    Retrieves comprehensive information about a single delivery attempt,
    including the full payload that was sent, response received, and
    any error details. Useful for debugging failed deliveries.

    Args:
        webhook_id: The unique identifier of the webhook.
        delivery_id: The unique identifier of the delivery record.
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user making the request.

    Returns:
        dict: Complete delivery details including:
            - id: Delivery record ID
            - webhook_id: Associated webhook ID
            - event_type: The event that triggered the delivery
            - payload: The full JSON payload that was sent
            - status: Current delivery status
            - status_code: HTTP response status code (if received)
            - response_body: Response body from the webhook endpoint
            - error_message: Error details (for failed deliveries)
            - created_at: When the delivery was created
            - delivered_at: When successful delivery occurred
            - retry_count: Number of retry attempts made
            - next_retry_at: Scheduled time for next retry (if pending)

    Raises:
        HTTPException: 404 Not Found if the webhook or delivery does not exist.
        HTTPException: 403 Forbidden if the user does not own the webhook.
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
    """Manually retry a failed delivery.

    Resets a failed delivery's status and immediately attempts redelivery.
    This is useful when the receiving endpoint was temporarily unavailable
    or when issues have been resolved on the receiver side.

    Note:
        Only failed or pending deliveries can be retried. Attempting to
        retry an already successful delivery will result in an error.

    Args:
        webhook_id: The unique identifier of the webhook.
        delivery_id: The unique identifier of the delivery to retry.
        db: Database session injected by FastAPI dependency.
        current_user: The authenticated user making the request.

    Returns:
        dict: Result of the retry attempt containing:
            - success: Whether the retry delivery succeeded
            - message: Descriptive result message
            - status: Current delivery status after retry

    Raises:
        HTTPException: 404 Not Found if the webhook or delivery does not exist.
        HTTPException: 403 Forbidden if the user does not own the webhook.
        HTTPException: 400 Bad Request if the delivery was already successful.
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
