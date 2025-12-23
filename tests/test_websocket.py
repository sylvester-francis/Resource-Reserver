import anyio
import pytest
from starlette.websockets import WebSocketDisconnect

from app.websocket import manager as ws_manager


def test_websocket_rejects_missing_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws"):
            pass


def test_websocket_broadcast_to_user(client, test_user):
    token_response = client.post(
        "/api/v1/token",
        data={"username": "testuser", "password": "testpass123"},
    )
    assert token_response.status_code == 200
    access_token = token_response.json()["access_token"]

    with client.websocket_connect(f"/ws?token={access_token}") as websocket:
        anyio.run(
            ws_manager.broadcast_to_user,
            test_user.id,
            {"type": "test_event", "payload": "hello"},
        )

        message = websocket.receive_json()
        assert message["type"] == "test_event"
        assert message["payload"] == "hello"
