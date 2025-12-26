"""Tests for webhook functionality.

Author: Sylvester-Francis
"""

from fastapi.testclient import TestClient


class TestWebhookService:
    """Tests for webhook service utilities."""

    def test_generate_webhook_secret(self):
        """Test webhook secret generation."""
        from app.webhook_service import generate_webhook_secret

        secret = generate_webhook_secret()
        assert len(secret) >= 32
        assert isinstance(secret, str)

    def test_sign_payload(self):
        """Test payload signing with HMAC-SHA256."""
        from app.webhook_service import sign_payload

        payload = '{"event":"test"}'
        secret = "test_secret"
        signature = sign_payload(payload, secret)

        assert signature.startswith("sha256=")
        assert len(signature) > 10

    def test_verify_signature_valid(self):
        """Test signature verification with valid signature."""
        from app.webhook_service import sign_payload, verify_signature

        payload = '{"event":"test"}'
        secret = "test_secret"
        signature = sign_payload(payload, secret)

        assert verify_signature(payload, secret, signature) is True

    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature."""
        from app.webhook_service import verify_signature

        payload = '{"event":"test"}'
        secret = "test_secret"
        wrong_signature = "sha256=invalid"

        assert verify_signature(payload, secret, wrong_signature) is False

    def test_get_event_types(self):
        """Test getting available event types."""
        from app.webhook_service import get_event_types

        events = get_event_types()
        assert len(events) > 0
        assert all("type" in e and "description" in e for e in events)

    def test_webhook_event_types_enum(self):
        """Test WebhookEventType enum values."""
        from app.webhook_service import WebhookEventType

        assert WebhookEventType.RESERVATION_CREATED.value == "reservation.created"
        assert WebhookEventType.RESOURCE_CREATED.value == "resource.created"


class TestWebhookServiceDB:
    """Tests for webhook service with database."""

    def test_create_webhook(self, test_db):
        """Test creating a webhook."""
        from app import models
        from app.webhook_service import WebhookService

        db = test_db()

        # Create user
        user = models.User(username="webhook_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        service = WebhookService(db)
        webhook = service.create_webhook(
            user_id=user.id,
            url="https://example.com/webhook",
            events=["reservation.created", "resource.updated"],
            description="Test webhook",
        )

        assert webhook.id is not None
        assert webhook.url == "https://example.com/webhook"
        assert webhook.secret is not None
        assert len(webhook.secret) >= 32
        assert webhook.events == ["reservation.created", "resource.updated"]
        assert webhook.is_active is True

        db.close()

    def test_get_webhook(self, test_db):
        """Test getting a webhook by ID."""
        from app import models
        from app.webhook_service import WebhookService

        db = test_db()

        user = models.User(username="webhook_get_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        service = WebhookService(db)
        created = service.create_webhook(
            user_id=user.id,
            url="https://example.com/hook",
            events=["reservation.created"],
        )

        fetched = service.get_webhook(created.id)
        assert fetched is not None
        assert fetched.id == created.id

        db.close()

    def test_get_user_webhooks(self, test_db):
        """Test getting all webhooks for a user."""
        from app import models
        from app.webhook_service import WebhookService

        db = test_db()

        user = models.User(username="webhook_list_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        service = WebhookService(db)
        service.create_webhook(
            user_id=user.id,
            url="https://example.com/hook1",
            events=["reservation.created"],
        )
        service.create_webhook(
            user_id=user.id,
            url="https://example.com/hook2",
            events=["resource.updated"],
        )

        webhooks = service.get_user_webhooks(user.id)
        assert len(webhooks) == 2

        db.close()

    def test_update_webhook(self, test_db):
        """Test updating a webhook."""
        from app import models
        from app.webhook_service import WebhookService

        db = test_db()

        user = models.User(username="webhook_update_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        service = WebhookService(db)
        webhook = service.create_webhook(
            user_id=user.id,
            url="https://example.com/old",
            events=["reservation.created"],
        )

        updated = service.update_webhook(
            webhook_id=webhook.id,
            url="https://example.com/new",
            events=["resource.updated"],
            is_active=False,
        )

        assert updated.url == "https://example.com/new"
        assert updated.events == ["resource.updated"]
        assert updated.is_active is False

        db.close()

    def test_regenerate_secret(self, test_db):
        """Test regenerating webhook secret."""
        from app import models
        from app.webhook_service import WebhookService

        db = test_db()

        user = models.User(username="webhook_regen_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        service = WebhookService(db)
        webhook = service.create_webhook(
            user_id=user.id,
            url="https://example.com/hook",
            events=["reservation.created"],
        )

        old_secret = webhook.secret
        updated = service.regenerate_secret(webhook.id)

        assert updated.secret != old_secret
        assert len(updated.secret) >= 32

        db.close()

    def test_delete_webhook(self, test_db):
        """Test deleting a webhook."""
        from app import models
        from app.webhook_service import WebhookService

        db = test_db()

        user = models.User(username="webhook_delete_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        service = WebhookService(db)
        webhook = service.create_webhook(
            user_id=user.id,
            url="https://example.com/hook",
            events=["reservation.created"],
        )

        result = service.delete_webhook(webhook.id)
        assert result is True

        fetched = service.get_webhook(webhook.id)
        assert fetched is None

        db.close()

    def test_get_webhooks_for_event(self, test_db):
        """Test getting webhooks subscribed to an event."""
        from app import models
        from app.webhook_service import WebhookService

        db = test_db()

        user = models.User(username="webhook_event_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        service = WebhookService(db)

        # Create webhooks with different events
        service.create_webhook(
            user_id=user.id,
            url="https://example.com/hook1",
            events=["reservation.created", "resource.updated"],
        )
        service.create_webhook(
            user_id=user.id,
            url="https://example.com/hook2",
            events=["resource.updated"],
        )

        # Query by event
        res_hooks = service.get_webhooks_for_event("reservation.created")
        assert len(res_hooks) == 1

        resource_hooks = service.get_webhooks_for_event("resource.updated")
        assert len(resource_hooks) == 2

        db.close()

    def test_create_delivery(self, test_db):
        """Test creating a delivery record."""
        from app import models
        from app.webhook_service import WebhookService

        db = test_db()

        user = models.User(username="webhook_delivery_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        service = WebhookService(db)
        webhook = service.create_webhook(
            user_id=user.id,
            url="https://example.com/hook",
            events=["reservation.created"],
        )

        delivery = service.create_delivery(
            webhook_id=webhook.id,
            event_type="reservation.created",
            payload={"test": "data"},
        )

        assert delivery.id is not None
        assert delivery.status == "pending"
        assert delivery.webhook_id == webhook.id

        db.close()


class TestWebhookEndpoints:
    """Tests for webhook API endpoints."""

    def test_list_event_types(self, client: TestClient, auth_headers: dict):
        """Test listing available event types."""
        response = client.get("/api/v1/webhooks/events", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "type" in data[0]
        assert "description" in data[0]

    def test_create_webhook(self, client: TestClient, auth_headers: dict):
        """Test creating a webhook."""
        response = client.post(
            "/api/v1/webhooks/",
            headers=auth_headers,
            json={
                "url": "https://example.com/webhook",
                "events": ["reservation.created"],
                "description": "Test webhook",
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert "secret" in data
        assert data["url"] == "https://example.com/webhook"
        assert data["events"] == ["reservation.created"]
        assert data["is_active"] is True

    def test_create_webhook_invalid_event(self, client: TestClient, auth_headers: dict):
        """Test creating webhook with invalid event type."""
        response = client.post(
            "/api/v1/webhooks/",
            headers=auth_headers,
            json={
                "url": "https://example.com/webhook",
                "events": ["invalid.event"],
            },
        )
        assert response.status_code == 400
        assert "Invalid event types" in response.json()["detail"]

    def test_list_webhooks(self, client: TestClient, auth_headers: dict):
        """Test listing user's webhooks."""
        # Create a webhook first
        client.post(
            "/api/v1/webhooks/",
            headers=auth_headers,
            json={
                "url": "https://example.com/list-test",
                "events": ["reservation.created"],
            },
        )

        response = client.get("/api/v1/webhooks/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_webhook(self, client: TestClient, auth_headers: dict):
        """Test getting a specific webhook."""
        # Create
        create_response = client.post(
            "/api/v1/webhooks/",
            headers=auth_headers,
            json={
                "url": "https://example.com/get-test",
                "events": ["reservation.created"],
            },
        )
        webhook_id = create_response.json()["id"]

        # Get
        response = client.get(f"/api/v1/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == webhook_id

    def test_update_webhook(self, client: TestClient, auth_headers: dict):
        """Test updating a webhook."""
        # Create
        create_response = client.post(
            "/api/v1/webhooks/",
            headers=auth_headers,
            json={
                "url": "https://example.com/update-test",
                "events": ["reservation.created"],
            },
        )
        webhook_id = create_response.json()["id"]

        # Update
        response = client.patch(
            f"/api/v1/webhooks/{webhook_id}",
            headers=auth_headers,
            json={
                "url": "https://example.com/updated",
                "is_active": False,
            },
        )
        assert response.status_code == 200
        assert response.json()["url"] == "https://example.com/updated"
        assert response.json()["is_active"] is False

    def test_delete_webhook(self, client: TestClient, auth_headers: dict):
        """Test deleting a webhook."""
        # Create
        create_response = client.post(
            "/api/v1/webhooks/",
            headers=auth_headers,
            json={
                "url": "https://example.com/delete-test",
                "events": ["reservation.created"],
            },
        )
        webhook_id = create_response.json()["id"]

        # Delete
        response = client.delete(f"/api/v1/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/api/v1/webhooks/{webhook_id}", headers=auth_headers
        )
        assert get_response.status_code == 404

    def test_regenerate_secret(self, client: TestClient, auth_headers: dict):
        """Test regenerating webhook secret."""
        # Create
        create_response = client.post(
            "/api/v1/webhooks/",
            headers=auth_headers,
            json={
                "url": "https://example.com/regen-test",
                "events": ["reservation.created"],
            },
        )
        webhook_id = create_response.json()["id"]
        old_secret = create_response.json()["secret"]

        # Regenerate
        response = client.post(
            f"/api/v1/webhooks/{webhook_id}/regenerate-secret", headers=auth_headers
        )
        assert response.status_code == 200
        assert "secret" in response.json()
        assert response.json()["secret"] != old_secret

    def test_get_deliveries(self, client: TestClient, auth_headers: dict):
        """Test getting delivery history."""
        # Create webhook
        create_response = client.post(
            "/api/v1/webhooks/",
            headers=auth_headers,
            json={
                "url": "https://example.com/deliveries-test",
                "events": ["reservation.created"],
            },
        )
        webhook_id = create_response.json()["id"]

        # Get deliveries (should be empty initially)
        response = client.get(
            f"/api/v1/webhooks/{webhook_id}/deliveries", headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_signature_example(self, client: TestClient, auth_headers: dict):
        """Test getting signature example."""
        response = client.get(
            "/api/v1/webhooks/signature-example", headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "algorithm" in data
        assert data["algorithm"] == "HMAC-SHA256"
        assert "python_example" in data
        assert "javascript_example" in data

    def test_webhook_not_found(self, client: TestClient, auth_headers: dict):
        """Test accessing non-existent webhook."""
        response = client.get("/api/v1/webhooks/99999", headers=auth_headers)
        assert response.status_code == 404


class TestWebhookModels:
    """Tests for webhook models."""

    def test_webhook_model(self, test_db):
        """Test Webhook model creation."""
        from app import models

        db = test_db()

        user = models.User(username="webhook_model_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        webhook = models.Webhook(
            user_id=user.id,
            url="https://example.com/webhook",
            secret="test_secret_12345678901234567890",
            events=["reservation.created"],
        )
        db.add(webhook)
        db.commit()
        db.refresh(webhook)

        assert webhook.id is not None
        assert webhook.is_active is True
        assert webhook.created_at is not None

        db.close()

    def test_webhook_delivery_model(self, test_db):
        """Test WebhookDelivery model creation."""
        from app import models

        db = test_db()

        user = models.User(username="delivery_model_user", hashed_password="test")
        db.add(user)
        db.commit()
        db.refresh(user)

        webhook = models.Webhook(
            user_id=user.id,
            url="https://example.com/webhook",
            secret="test_secret_12345678901234567890",
            events=["reservation.created"],
        )
        db.add(webhook)
        db.commit()
        db.refresh(webhook)

        delivery = models.WebhookDelivery(
            webhook_id=webhook.id,
            event_type="reservation.created",
            payload={"test": "data"},
            status="pending",
        )
        db.add(delivery)
        db.commit()
        db.refresh(delivery)

        assert delivery.id is not None
        assert delivery.status == "pending"
        assert delivery.retry_count == 0

        db.close()
