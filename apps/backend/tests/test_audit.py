"""Tests for the audit log endpoints.

Author: Sylvester-Francis
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


class TestAuditLogEndpoints:
    """Tests for audit log API endpoints."""

    def test_audit_logs_requires_auth(self, client: TestClient):
        """Test that audit logs require authentication."""
        response = client.get("/api/v1/audit/logs")
        assert response.status_code == 401

    def test_audit_logs_requires_admin(self, client: TestClient, auth_headers: dict):
        """Test that audit logs require admin role."""
        response = client.get("/api/v1/audit/logs", headers=auth_headers)
        # Regular user should be denied
        assert response.status_code == 403

    def test_my_activity_for_regular_user(self, client: TestClient, auth_headers: dict):
        """Test that regular users can view their own activity."""
        response = client.get("/api/v1/audit/my-activity", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestAuditService:
    """Tests for audit service functionality."""

    def test_log_action_creates_entry(self, test_db):
        """Test that log_action creates an audit entry."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        log = service.log_action(
            action="create",
            entity_type="test_entity",
            entity_id=1,
            entity_name="Test Entity",
            user_id=1,
            username="testuser",
            details="Created test entity",
        )
        db.close()

        assert log.id is not None
        assert log.action == "create"
        assert log.entity_type == "test_entity"
        assert log.entity_id == 1
        assert log.username == "testuser"
        assert log.success is True

    def test_log_action_with_old_new_values(self, test_db):
        """Test logging action with change tracking."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        old_values = {"name": "Old Name", "status": "inactive"}
        new_values = {"name": "New Name", "status": "active"}

        log = service.log_action(
            action="update",
            entity_type="resource",
            entity_id=5,
            old_values=old_values,
            new_values=new_values,
        )
        db.close()

        assert log.old_values == old_values
        assert log.new_values == new_values

    def test_log_action_failed(self, test_db):
        """Test logging a failed action."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        log = service.log_action(
            action="delete",
            entity_type="reservation",
            entity_id=10,
            success=False,
            error_message="Permission denied",
        )
        db.close()

        assert log.success is False
        assert log.error_message == "Permission denied"

    def test_get_logs_with_filters(self, test_db):
        """Test querying logs with filters."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create some test logs
        service.log_action(action="create", entity_type="resource", user_id=1)
        service.log_action(action="update", entity_type="resource", user_id=1)
        service.log_action(action="delete", entity_type="reservation", user_id=2)

        # Filter by action
        logs, total = service.get_logs(action="create")
        assert total == 1
        assert logs[0].action == "create"

        # Filter by entity type
        logs, total = service.get_logs(entity_type="resource")
        assert total == 2

        # Filter by user
        logs, total = service.get_logs(user_id=1)
        assert total == 2

        db.close()

    def test_get_logs_with_date_range(self, test_db):
        """Test querying logs with date range."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create a log
        service.log_action(action="test", entity_type="test")

        # Query with date range including now
        now = datetime.now(UTC)
        logs, total = service.get_logs(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
        )
        assert total >= 1

        # Query with date range in the past
        logs, total = service.get_logs(
            start_date=now - timedelta(days=10),
            end_date=now - timedelta(days=5),
        )
        assert total == 0

        db.close()

    def test_get_entity_history(self, test_db):
        """Test getting history for a specific entity."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create history for an entity
        service.log_action(action="create", entity_type="resource", entity_id=100)
        service.log_action(action="update", entity_type="resource", entity_id=100)
        service.log_action(action="update", entity_type="resource", entity_id=100)
        service.log_action(action="delete", entity_type="resource", entity_id=200)

        history = service.get_entity_history("resource", 100)
        assert len(history) == 3

        db.close()

    def test_get_user_activity(self, test_db):
        """Test getting activity for a user."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create activity for users
        service.log_action(action="login", entity_type="auth", user_id=10)
        service.log_action(action="create", entity_type="reservation", user_id=10)
        service.log_action(action="view", entity_type="resource", user_id=20)

        activity = service.get_user_activity(10)
        assert len(activity) == 2

        db.close()

    def test_get_action_statistics(self, test_db):
        """Test getting audit statistics."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create various logs
        service.log_action(action="create", entity_type="resource", username="user1")
        service.log_action(action="create", entity_type="reservation", username="user1")
        service.log_action(action="update", entity_type="resource", username="user2")
        service.log_action(action="delete", entity_type="resource", success=False)

        stats = service.get_action_statistics()

        assert "by_action" in stats
        assert stats["by_action"]["create"] == 2
        assert stats["by_action"]["update"] == 1
        assert stats["by_action"]["delete"] == 1

        assert "by_entity_type" in stats
        assert stats["by_entity_type"]["resource"] == 3

        assert "by_success" in stats
        assert stats["by_success"]["success"] == 3
        assert stats["by_success"]["failed"] == 1

        assert "most_active_users" in stats
        assert len(stats["most_active_users"]) >= 1

        db.close()

    def test_export_to_csv(self, test_db):
        """Test exporting logs to CSV."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create some logs
        service.log_action(action="create", entity_type="resource")
        service.log_action(action="update", entity_type="reservation")

        csv_content = service.export_to_csv()

        assert "id,timestamp,user_id" in csv_content
        assert "create" in csv_content
        assert "update" in csv_content

        db.close()

    def test_export_to_json(self, test_db):
        """Test exporting logs to JSON."""
        import json

        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create some logs
        service.log_action(action="create", entity_type="resource")

        json_content = service.export_to_json()
        data = json.loads(json_content)

        assert "total" in data
        assert "logs" in data
        assert "exported_at" in data
        assert len(data["logs"]) >= 1

        db.close()

    def test_apply_retention_policy(self, test_db):
        """Test retention policy application."""
        from app import models
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create a log
        service.log_action(action="test", entity_type="test")

        # Apply retention (short period - nothing should be deleted)
        deleted = service.apply_retention_policy(retention_days=1)
        assert deleted == 0

        # Manually create an old log for testing
        old_log = models.AuditLog(
            action="old_action",
            entity_type="old_type",
            timestamp=datetime.now(UTC) - timedelta(days=100),
        )
        db.add(old_log)
        db.commit()

        # Apply retention (should delete the old log)
        deleted = service.apply_retention_policy(retention_days=90)
        assert deleted == 1

        db.close()

    def test_get_available_actions(self, test_db):
        """Test getting available action types."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create logs with different actions
        service.log_action(action="create", entity_type="test")
        service.log_action(action="update", entity_type="test")
        service.log_action(action="delete", entity_type="test")

        actions = service.get_available_actions()
        assert "create" in actions
        assert "update" in actions
        assert "delete" in actions

        db.close()

    def test_get_available_entity_types(self, test_db):
        """Test getting available entity types."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create logs with different entity types
        service.log_action(action="test", entity_type="resource")
        service.log_action(action="test", entity_type="reservation")
        service.log_action(action="test", entity_type="user")

        types = service.get_available_entity_types()
        assert "resource" in types
        assert "reservation" in types
        assert "user" in types

        db.close()

    def test_search_in_logs(self, test_db):
        """Test searching within audit logs."""
        from app.audit_service import AuditService

        db = test_db()
        service = AuditService(db)

        # Create logs with searchable content
        service.log_action(
            action="create",
            entity_type="resource",
            entity_name="Conference Room A",
            details="Created new conference room",
        )
        service.log_action(
            action="update",
            entity_type="resource",
            entity_name="Meeting Room B",
            details="Updated meeting room capacity",
        )

        # Search for "conference"
        logs, total = service.get_logs(search="conference")
        assert total == 1

        # Search for "room"
        logs, total = service.get_logs(search="room")
        assert total == 2

        db.close()
