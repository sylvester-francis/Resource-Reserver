"""WebSocket connection manager for real-time updates."""

from fastapi import WebSocket


class ConnectionManager:
    """Track and manage active WebSocket connections by user ID.

    Attributes:
        active_connections: Mapping of user IDs to active WebSocket sets.
    """

    def __init__(self):
        """Initialize the connection manager with no active connections."""
        self.active_connections: dict[int, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a connection and associate it with a user.

        Args:
            websocket: The WebSocket instance to accept.
            user_id: The authenticated user ID for the connection.
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a connection for a given user.

        Args:
            websocket: The WebSocket instance to remove.
            user_id: The authenticated user ID for the connection.
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

    async def broadcast_to_user(self, user_id: int, message: dict):
        """Send a JSON message to all connections for one user.

        Args:
            user_id: The user ID to target.
            message: The JSON-serializable payload to send.
        """
        if user_id in self.active_connections:
            for connection in list(self.active_connections[user_id]):
                await connection.send_json(message)

    async def broadcast_all(self, message: dict):
        """Send a JSON message to every active connection.

        Args:
            message: The JSON-serializable payload to send.
        """
        for connections in self.active_connections.values():
            for connection in list(connections):
                await connection.send_json(message)


manager = ConnectionManager()
