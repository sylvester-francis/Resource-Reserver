from fastapi import status

from app.schemas import NotificationType
from app.services import NotificationService

API_V1 = "/api/v1"


def seed_notifications(test_db, user_id: int, count: int = 3):
    db = test_db()
    try:
        service = NotificationService(db)
        for idx in range(count):
            service.create_notification(
                user_id=user_id,
                type=NotificationType.RESERVATION_CONFIRMED,
                title=f"Test Notification {idx + 1}",
                message="This is a test notification",
            )
    finally:
        db.close()


class TestNotifications:
    def test_list_notifications(self, client, auth_headers, test_db, test_user):
        seed_notifications(test_db, test_user.id, count=2)
        # Create notifications for another user to ensure isolation
        other_user_id = test_user.id + 1
        seed_notifications(test_db, other_user_id, count=1)

        response = client.get(f"{API_V1}/notifications", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert isinstance(payload["data"], list)
        assert payload["has_more"] is False
        assert len(payload["data"]) == 2
        assert all(n["read"] is False for n in payload["data"])

    def test_mark_notification_read(self, client, auth_headers, test_db, test_user):
        db = test_db()
        try:
            service = NotificationService(db)
            notification = service.create_notification(
                user_id=test_user.id,
                type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title="Action Needed",
                message="Please review recent changes.",
            )
        finally:
            db.close()

        response = client.post(
            f"{API_V1}/notifications/{notification.id}/read", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == notification.id
        assert data["read"] is True

    def test_mark_all_notifications_read(
        self, client, auth_headers, test_db, test_user
    ):
        seed_notifications(test_db, test_user.id, count=3)

        response = client.post(
            f"{API_V1}/notifications/mark-all-read", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated"] >= 3

        # Verify all are now read
        follow_up = client.get(f"{API_V1}/notifications", headers=auth_headers)
        payload = follow_up.json()
        assert all(n["read"] is True for n in payload["data"])

    def test_requires_auth(self, client):
        response = client.get(f"{API_V1}/notifications")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
