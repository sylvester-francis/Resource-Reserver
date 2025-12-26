"""Webhook service for external integrations.

Provides:
- Webhook registration and management
- Event delivery with retry logic
- Payload signing with HMAC
- Delivery logging

Author: Sylvester-Francis
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Supported webhook event types."""

    RESERVATION_CREATED = "reservation.created"
    RESERVATION_CANCELLED = "reservation.cancelled"
    RESERVATION_UPDATED = "reservation.updated"
    RESERVATION_EXPIRED = "reservation.expired"
    RESOURCE_CREATED = "resource.created"
    RESOURCE_UPDATED = "resource.updated"
    RESOURCE_DELETED = "resource.deleted"
    RESOURCE_UNAVAILABLE = "resource.unavailable"
    RESOURCE_AVAILABLE = "resource.available"
    USER_CREATED = "user.created"
    WAITLIST_OFFER = "waitlist.offer"
    WAITLIST_ACCEPTED = "waitlist.accepted"
    WAITLIST_EXPIRED = "waitlist.expired"


# Retry configuration
MAX_RETRIES = 5
RETRY_DELAYS = [60, 300, 900, 3600, 7200]  # 1m, 5m, 15m, 1h, 2h


def generate_webhook_secret() -> str:
    """Generate a secure webhook secret."""
    return secrets.token_urlsafe(32)


def sign_payload(payload: str, secret: str) -> str:
    """Sign a webhook payload with HMAC-SHA256."""
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def verify_signature(payload: str, secret: str, signature: str) -> bool:
    """Verify a webhook signature."""
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


class WebhookService:
    """Service for webhook operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_webhook(
        self,
        user_id: int,
        url: str,
        events: list[str],
        description: str | None = None,
    ) -> models.Webhook:
        """Register a new webhook.

        Args:
            user_id: Owner of the webhook
            url: URL to send events to
            events: List of event types to subscribe to
            description: Optional description

        Returns:
            Created webhook with secret
        """
        secret = generate_webhook_secret()

        webhook = models.Webhook(
            user_id=user_id,
            url=url,
            secret=secret,
            events=events,
            description=description,
            is_active=True,
        )

        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)

        logger.info(f"Created webhook {webhook.id} for user {user_id}")
        return webhook

    def get_webhook(self, webhook_id: int) -> models.Webhook | None:
        """Get a webhook by ID."""
        return (
            self.db.query(models.Webhook)
            .filter(models.Webhook.id == webhook_id)
            .first()
        )

    def get_user_webhooks(self, user_id: int) -> list[models.Webhook]:
        """Get all webhooks for a user."""
        return (
            self.db.query(models.Webhook)
            .filter(models.Webhook.user_id == user_id)
            .all()
        )

    def update_webhook(
        self,
        webhook_id: int,
        url: str | None = None,
        events: list[str] | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> models.Webhook | None:
        """Update a webhook configuration."""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None

        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = events
        if description is not None:
            webhook.description = description
        if is_active is not None:
            webhook.is_active = is_active

        self.db.commit()
        self.db.refresh(webhook)
        return webhook

    def regenerate_secret(self, webhook_id: int) -> models.Webhook | None:
        """Regenerate the secret for a webhook."""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None

        webhook.secret = generate_webhook_secret()
        self.db.commit()
        self.db.refresh(webhook)

        logger.info(f"Regenerated secret for webhook {webhook_id}")
        return webhook

    def delete_webhook(self, webhook_id: int) -> bool:
        """Delete a webhook."""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return False

        self.db.delete(webhook)
        self.db.commit()

        logger.info(f"Deleted webhook {webhook_id}")
        return True

    def get_webhooks_for_event(self, event_type: str) -> list[models.Webhook]:
        """Get all active webhooks subscribed to an event type."""
        webhooks = (
            self.db.query(models.Webhook)
            .filter(models.Webhook.is_active == True)  # noqa: E712
            .all()
        )
        # Filter by event type (events is a JSON array)
        return [w for w in webhooks if event_type in (w.events or [])]

    def create_delivery(
        self,
        webhook_id: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> models.WebhookDelivery:
        """Create a webhook delivery record."""
        delivery = models.WebhookDelivery(
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            status="pending",
        )

        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)

        return delivery

    def update_delivery_status(
        self,
        delivery_id: int,
        status: str,
        status_code: int | None = None,
        response_body: str | None = None,
        error_message: str | None = None,
    ):
        """Update delivery status after attempt."""
        delivery = (
            self.db.query(models.WebhookDelivery)
            .filter(models.WebhookDelivery.id == delivery_id)
            .first()
        )
        if delivery:
            delivery.status = status
            delivery.status_code = status_code
            delivery.response_body = response_body[:1000] if response_body else None
            delivery.error_message = error_message
            delivery.delivered_at = datetime.now(UTC) if status == "delivered" else None
            self.db.commit()

    def increment_retry(self, delivery_id: int) -> int:
        """Increment retry count and return new count."""
        delivery = (
            self.db.query(models.WebhookDelivery)
            .filter(models.WebhookDelivery.id == delivery_id)
            .first()
        )
        if delivery:
            delivery.retry_count += 1
            next_delay = RETRY_DELAYS[
                min(delivery.retry_count - 1, len(RETRY_DELAYS) - 1)
            ]
            delivery.next_retry_at = datetime.now(UTC) + timedelta(seconds=next_delay)
            self.db.commit()
            return delivery.retry_count
        return 0

    def get_delivery_history(
        self,
        webhook_id: int,
        limit: int = 50,
    ) -> list[models.WebhookDelivery]:
        """Get delivery history for a webhook."""
        return (
            self.db.query(models.WebhookDelivery)
            .filter(models.WebhookDelivery.webhook_id == webhook_id)
            .order_by(models.WebhookDelivery.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_pending_deliveries(self) -> list[models.WebhookDelivery]:
        """Get deliveries that need to be retried."""
        now = datetime.now(UTC)
        return (
            self.db.query(models.WebhookDelivery)
            .filter(
                models.WebhookDelivery.status.in_(["pending", "failed"]),
                models.WebhookDelivery.retry_count < MAX_RETRIES,
                (models.WebhookDelivery.next_retry_at <= now)
                | (models.WebhookDelivery.next_retry_at.is_(None)),
            )
            .all()
        )


async def deliver_webhook(
    webhook: models.Webhook,
    delivery: models.WebhookDelivery,
    db: Session,
) -> bool:
    """Deliver a webhook payload to the endpoint.

    Args:
        webhook: Webhook configuration
        delivery: Delivery record
        db: Database session

    Returns:
        True if delivery succeeded
    """
    service = WebhookService(db)
    payload_str = json.dumps(delivery.payload, default=str)
    signature = sign_payload(payload_str, webhook.secret)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": delivery.event_type,
        "X-Webhook-Delivery": str(delivery.id),
        "User-Agent": "ResourceReserver-Webhook/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook.url,
                content=payload_str,
                headers=headers,
            )

            if response.status_code >= 200 and response.status_code < 300:
                service.update_delivery_status(
                    delivery.id,
                    status="delivered",
                    status_code=response.status_code,
                    response_body=response.text,
                )
                logger.info(
                    f"Webhook delivery {delivery.id} succeeded: {response.status_code}"
                )
                return True
            else:
                retry_count = service.increment_retry(delivery.id)
                service.update_delivery_status(
                    delivery.id,
                    status="failed" if retry_count >= MAX_RETRIES else "pending",
                    status_code=response.status_code,
                    response_body=response.text,
                    error_message=f"HTTP {response.status_code}",
                )
                logger.warning(
                    f"Webhook delivery {delivery.id} failed: {response.status_code}"
                )
                return False

    except Exception as e:
        retry_count = service.increment_retry(delivery.id)
        service.update_delivery_status(
            delivery.id,
            status="failed" if retry_count >= MAX_RETRIES else "pending",
            error_message=str(e)[:500],
        )
        logger.error(f"Webhook delivery {delivery.id} error: {e}")
        return False


async def dispatch_event(
    db: Session,
    event_type: str,
    payload: dict[str, Any],
) -> int:
    """Dispatch an event to all subscribed webhooks.

    Args:
        db: Database session
        event_type: Type of event (e.g., "reservation.created")
        payload: Event data

    Returns:
        Number of webhooks notified
    """
    service = WebhookService(db)
    webhooks = service.get_webhooks_for_event(event_type)

    if not webhooks:
        return 0

    deliveries_created = 0
    for webhook in webhooks:
        # Create delivery record
        delivery = service.create_delivery(
            webhook_id=webhook.id,
            event_type=event_type,
            payload={
                "event": event_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "data": payload,
            },
        )
        deliveries_created += 1

        # Try to deliver immediately (async)
        asyncio.create_task(deliver_webhook(webhook, delivery, db))

    logger.info(f"Dispatched {event_type} to {deliveries_created} webhooks")
    return deliveries_created


def get_event_types() -> list[dict[str, str]]:
    """Get list of available event types with descriptions."""
    return [
        {
            "type": WebhookEventType.RESERVATION_CREATED.value,
            "description": "A new reservation was created",
        },
        {
            "type": WebhookEventType.RESERVATION_CANCELLED.value,
            "description": "A reservation was cancelled",
        },
        {
            "type": WebhookEventType.RESERVATION_UPDATED.value,
            "description": "A reservation was updated",
        },
        {
            "type": WebhookEventType.RESERVATION_EXPIRED.value,
            "description": "A reservation has expired",
        },
        {
            "type": WebhookEventType.RESOURCE_CREATED.value,
            "description": "A new resource was created",
        },
        {
            "type": WebhookEventType.RESOURCE_UPDATED.value,
            "description": "A resource was updated",
        },
        {
            "type": WebhookEventType.RESOURCE_DELETED.value,
            "description": "A resource was deleted",
        },
        {
            "type": WebhookEventType.RESOURCE_UNAVAILABLE.value,
            "description": "A resource became unavailable",
        },
        {
            "type": WebhookEventType.RESOURCE_AVAILABLE.value,
            "description": "A resource became available",
        },
        {
            "type": WebhookEventType.USER_CREATED.value,
            "description": "A new user was registered",
        },
        {
            "type": WebhookEventType.WAITLIST_OFFER.value,
            "description": "A waitlist offer was made",
        },
        {
            "type": WebhookEventType.WAITLIST_ACCEPTED.value,
            "description": "A waitlist offer was accepted",
        },
        {
            "type": WebhookEventType.WAITLIST_EXPIRED.value,
            "description": "A waitlist offer expired",
        },
    ]
