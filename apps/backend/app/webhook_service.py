"""Webhook service for external integrations.

This module provides a comprehensive webhook management system for the Resource
Reserver application, enabling external systems to receive real-time notifications
about events such as reservation changes, resource updates, and user activities.

Features:
    - Webhook registration and lifecycle management
    - Event subscription with granular event type filtering
    - Secure payload signing using HMAC-SHA256
    - Automatic retry logic with exponential backoff
    - Delivery logging and history tracking
    - Asynchronous event dispatch for non-blocking operation

Example Usage:
    Basic webhook registration and event dispatch::

        from sqlalchemy.orm import Session
        from app.webhook_service import WebhookService, dispatch_event

        # Create a webhook subscription
        service = WebhookService(db)
        webhook = service.create_webhook(
            user_id=1,
            url="https://example.com/webhook",
            events=["reservation.created", "reservation.cancelled"],
            description="Notify on reservation changes"
        )

        # Dispatch an event to all subscribers
        await dispatch_event(
            db=db,
            event_type="reservation.created",
            payload={"reservation_id": 123, "resource_name": "Conference Room A"}
        )

    Verifying incoming webhook signatures::

        from app.webhook_service import verify_signature

        payload = request.body.decode('utf-8')
        signature = request.headers.get('X-Webhook-Signature')
        is_valid = verify_signature(payload, webhook_secret, signature)

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
    """Enumeration of supported webhook event types.

    This enum defines all event types that can trigger webhook notifications.
    Events are organized by domain (reservation, resource, user, waitlist)
    and action (created, updated, deleted, etc.).

    Attributes:
        RESERVATION_CREATED: Triggered when a new reservation is made.
        RESERVATION_CANCELLED: Triggered when an existing reservation is cancelled.
        RESERVATION_UPDATED: Triggered when reservation details are modified.
        RESERVATION_EXPIRED: Triggered when a reservation passes its end time.
        RESOURCE_CREATED: Triggered when a new resource is added to the system.
        RESOURCE_UPDATED: Triggered when resource properties are changed.
        RESOURCE_DELETED: Triggered when a resource is removed from the system.
        RESOURCE_UNAVAILABLE: Triggered when a resource becomes unavailable.
        RESOURCE_AVAILABLE: Triggered when a resource becomes available again.
        USER_CREATED: Triggered when a new user account is registered.
        WAITLIST_OFFER: Triggered when a waitlist position results in an offer.
        WAITLIST_ACCEPTED: Triggered when a user accepts a waitlist offer.
        WAITLIST_EXPIRED: Triggered when a waitlist offer expires without acceptance.
    """

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
    """Generate a cryptographically secure webhook secret.

    Creates a URL-safe base64-encoded random string suitable for use as
    a webhook signing secret. The generated secret provides sufficient
    entropy for secure HMAC operations.

    Returns:
        A 32-byte URL-safe base64-encoded random string.

    Example:
        >>> secret = generate_webhook_secret()
        >>> len(secret)
        43
    """
    return secrets.token_urlsafe(32)


def sign_payload(payload: str, secret: str) -> str:
    """Sign a webhook payload using HMAC-SHA256.

    Computes an HMAC signature for the given payload using the provided
    secret key. The signature is prefixed with 'sha256=' to indicate
    the algorithm used.

    Args:
        payload: The JSON string payload to sign.
        secret: The webhook secret key used for signing.

    Returns:
        The HMAC-SHA256 signature in the format 'sha256={hex_digest}'.

    Example:
        >>> signature = sign_payload('{"event": "test"}', 'my-secret')
        >>> signature.startswith('sha256=')
        True
    """
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def verify_signature(payload: str, secret: str, signature: str) -> bool:
    """Verify a webhook payload signature.

    Validates that the provided signature matches the expected HMAC-SHA256
    signature for the payload. Uses constant-time comparison to prevent
    timing attacks.

    Args:
        payload: The JSON string payload that was signed.
        secret: The webhook secret key used for signing.
        signature: The signature to verify, in 'sha256={hex_digest}' format.

    Returns:
        True if the signature is valid, False otherwise.

    Example:
        >>> payload = '{"event": "test"}'
        >>> secret = 'my-secret'
        >>> sig = sign_payload(payload, secret)
        >>> verify_signature(payload, secret, sig)
        True
    """
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


class WebhookService:
    """Service class for webhook CRUD operations and delivery management.

    Provides methods for creating, reading, updating, and deleting webhooks,
    as well as managing webhook deliveries and their retry logic.

    Attributes:
        db: SQLAlchemy database session for persistence operations.

    Example:
        >>> service = WebhookService(db_session)
        >>> webhook = service.create_webhook(
        ...     user_id=1,
        ...     url="https://example.com/hook",
        ...     events=["reservation.created"]
        ... )
    """

    def __init__(self, db: Session):
        """Initialize the WebhookService with a database session.

        Args:
            db: SQLAlchemy database session for database operations.
        """
        self.db = db

    def create_webhook(
        self,
        user_id: int,
        url: str,
        events: list[str],
        description: str | None = None,
    ) -> models.Webhook:
        """Register a new webhook subscription.

        Creates a new webhook with an automatically generated secret key.
        The webhook is active by default and will receive events matching
        the specified event types.

        Args:
            user_id: The ID of the user who owns this webhook.
            url: The endpoint URL where events will be delivered.
            events: List of event type strings to subscribe to
                (e.g., ["reservation.created", "resource.updated"]).
            description: Optional human-readable description of the webhook's
                purpose.

        Returns:
            The newly created Webhook model instance with its generated secret.

        Example:
            >>> webhook = service.create_webhook(
            ...     user_id=1,
            ...     url="https://api.example.com/webhooks",
            ...     events=["reservation.created"],
            ...     description="Sync reservations to external calendar"
            ... )
            >>> print(webhook.secret)  # Save this secret!
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
        """Retrieve a webhook by its unique identifier.

        Args:
            webhook_id: The unique ID of the webhook to retrieve.

        Returns:
            The Webhook model instance if found, None otherwise.
        """
        return (
            self.db.query(models.Webhook)
            .filter(models.Webhook.id == webhook_id)
            .first()
        )

    def get_user_webhooks(self, user_id: int) -> list[models.Webhook]:
        """Retrieve all webhooks owned by a specific user.

        Args:
            user_id: The ID of the user whose webhooks to retrieve.

        Returns:
            List of Webhook model instances owned by the user.
            Returns an empty list if the user has no webhooks.
        """
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
        """Update an existing webhook's configuration.

        Only the provided parameters will be updated; others remain unchanged.
        Note that this does not regenerate the webhook secret.

        Args:
            webhook_id: The ID of the webhook to update.
            url: New endpoint URL for event delivery.
            events: New list of event types to subscribe to.
            description: New description for the webhook.
            is_active: Whether the webhook should receive events.

        Returns:
            The updated Webhook model instance, or None if the webhook
            was not found.
        """
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
        """Regenerate the signing secret for a webhook.

        Generates a new cryptographically secure secret for the webhook.
        The old secret is immediately invalidated. Clients must update
        their signature verification to use the new secret.

        Args:
            webhook_id: The ID of the webhook whose secret to regenerate.

        Returns:
            The updated Webhook model instance with the new secret,
            or None if the webhook was not found.

        Note:
            This operation cannot be undone. Ensure webhook consumers are
            updated with the new secret to prevent delivery failures.
        """
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None

        webhook.secret = generate_webhook_secret()
        self.db.commit()
        self.db.refresh(webhook)

        logger.info(f"Regenerated secret for webhook {webhook_id}")
        return webhook

    def delete_webhook(self, webhook_id: int) -> bool:
        """Permanently delete a webhook and its delivery history.

        Args:
            webhook_id: The ID of the webhook to delete.

        Returns:
            True if the webhook was deleted, False if it was not found.
        """
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return False

        self.db.delete(webhook)
        self.db.commit()

        logger.info(f"Deleted webhook {webhook_id}")
        return True

    def get_webhooks_for_event(self, event_type: str) -> list[models.Webhook]:
        """Retrieve all active webhooks subscribed to a specific event type.

        Filters webhooks to return only those that are active and have
        the specified event type in their subscription list.

        Args:
            event_type: The event type to filter by
                (e.g., "reservation.created").

        Returns:
            List of active Webhook model instances subscribed to the event.
        """
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
        """Create a new webhook delivery record.

        Initializes a delivery record in 'pending' status. The actual
        delivery attempt is performed separately.

        Args:
            webhook_id: The ID of the target webhook.
            event_type: The type of event being delivered.
            payload: The event data to be sent as JSON.

        Returns:
            The newly created WebhookDelivery model instance.
        """
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
    ) -> None:
        """Update the status of a webhook delivery attempt.

        Records the outcome of a delivery attempt including HTTP response
        details or error information.

        Args:
            delivery_id: The ID of the delivery to update.
            status: New status string ('pending', 'delivered', or 'failed').
            status_code: HTTP response status code if available.
            response_body: Response body text (truncated to 1000 chars).
            error_message: Error message if the delivery failed.
        """
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
        """Increment the retry counter and schedule the next retry attempt.

        Calculates the next retry time using exponential backoff based on
        the RETRY_DELAYS configuration.

        Args:
            delivery_id: The ID of the delivery to update.

        Returns:
            The new retry count after incrementing, or 0 if the delivery
            was not found.
        """
        delivery = (
            self.db.query(models.WebhookDelivery)
            .filter(models.WebhookDelivery.id == delivery_id)
            .first()
        )
        if delivery:
            delivery.retry_count += 1
            # Calculate next retry delay using exponential backoff
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
        """Retrieve delivery history for a specific webhook.

        Returns deliveries in reverse chronological order (most recent first).

        Args:
            webhook_id: The ID of the webhook to get history for.
            limit: Maximum number of deliveries to return. Defaults to 50.

        Returns:
            List of WebhookDelivery model instances ordered by creation
            date descending.
        """
        return (
            self.db.query(models.WebhookDelivery)
            .filter(models.WebhookDelivery.webhook_id == webhook_id)
            .order_by(models.WebhookDelivery.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_pending_deliveries(self) -> list[models.WebhookDelivery]:
        """Retrieve all deliveries that are eligible for retry.

        Returns deliveries that are pending or failed, have not exceeded
        the maximum retry count, and whose next retry time has passed.

        Returns:
            List of WebhookDelivery model instances ready for retry.
        """
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
    """Deliver a webhook payload to the configured endpoint.

    Performs an HTTP POST request to the webhook URL with the signed payload.
    Updates the delivery record with the result of the attempt.

    The request includes the following headers:
        - Content-Type: application/json
        - X-Webhook-Signature: HMAC-SHA256 signature
        - X-Webhook-Event: The event type
        - X-Webhook-Delivery: Unique delivery ID
        - User-Agent: ResourceReserver-Webhook/1.0

    Args:
        webhook: The Webhook model instance with URL and secret.
        delivery: The WebhookDelivery record containing the payload.
        db: Database session for updating delivery status.

    Returns:
        True if the delivery succeeded (2xx response), False otherwise.

    Note:
        Failed deliveries are automatically scheduled for retry up to
        MAX_RETRIES times with exponential backoff.
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
    """Dispatch an event to all webhooks subscribed to the event type.

    Creates delivery records for each subscribed webhook and initiates
    asynchronous delivery. The event payload is wrapped with metadata
    including the event type and timestamp.

    Args:
        db: Database session for webhook and delivery operations.
        event_type: The type of event being dispatched
            (e.g., "reservation.created").
        payload: The event-specific data to include in the delivery.

    Returns:
        The number of webhook deliveries that were created and dispatched.

    Example:
        >>> count = await dispatch_event(
        ...     db=session,
        ...     event_type="reservation.created",
        ...     payload={
        ...         "reservation_id": 123,
        ...         "user_id": 456,
        ...         "resource_id": 789
        ...     }
        ... )
        >>> print(f"Dispatched to {count} webhooks")
    """
    service = WebhookService(db)
    webhooks = service.get_webhooks_for_event(event_type)

    if not webhooks:
        return 0

    deliveries_created = 0
    for webhook in webhooks:
        # Create delivery record with wrapped payload
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

        # Try to deliver immediately (async, non-blocking)
        asyncio.create_task(deliver_webhook(webhook, delivery, db))

    logger.info(f"Dispatched {event_type} to {deliveries_created} webhooks")
    return deliveries_created


def get_event_types() -> list[dict[str, str]]:
    """Get a list of all available webhook event types with descriptions.

    Provides a catalog of supported event types that can be used when
    creating or updating webhook subscriptions.

    Returns:
        List of dictionaries, each containing:
            - type: The event type identifier string.
            - description: Human-readable description of when the event fires.

    Example:
        >>> events = get_event_types()
        >>> for event in events:
        ...     print(f"{event['type']}: {event['description']}")
    """
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
