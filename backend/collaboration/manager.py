"""WebSocket connection manager for real-time board collaboration."""

import asyncio
import logging
import time
import uuid
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections organized by board channels."""

    def __init__(self):
        # board_id -> {user_id -> WebSocket}
        self.board_connections: dict[uuid.UUID, dict[uuid.UUID, WebSocket]] = {}
        # board_id -> {user_id -> {x, y, name, color, last_update}}
        self.cursors: dict[uuid.UUID, dict[uuid.UUID, dict]] = {}
        # board_id -> {user_id -> {name, avatar_url, connected_at}}
        self.presence: dict[uuid.UUID, dict[uuid.UUID, dict]] = {}

    async def connect(self, board_id: uuid.UUID, user_id: uuid.UUID, ws: WebSocket, user_name: str = "Anonymous", avatar_url: str = None):
        await ws.accept()
        if board_id not in self.board_connections:
            self.board_connections[board_id] = {}
            self.cursors[board_id] = {}
            self.presence[board_id] = {}

        self.board_connections[board_id][user_id] = ws
        self.presence[board_id][user_id] = {
            "name": user_name,
            "avatar_url": avatar_url,
            "connected_at": time.time(),
            "color": self._user_color(user_id),
        }
        logger.info(f"User {user_name} connected to board {board_id}")

    async def disconnect(self, board_id: uuid.UUID, user_id: uuid.UUID):
        if board_id in self.board_connections:
            self.board_connections[board_id].pop(user_id, None)
            self.cursors.get(board_id, {}).pop(user_id, None)
            self.presence.get(board_id, {}).pop(user_id, None)
            if not self.board_connections[board_id]:
                del self.board_connections[board_id]
                self.cursors.pop(board_id, None)
                self.presence.pop(board_id, None)

    async def disconnect_all(self):
        for board_id in list(self.board_connections.keys()):
            for user_id, ws in list(self.board_connections.get(board_id, {}).items()):
                try:
                    await ws.close()
                except Exception:
                    pass
        self.board_connections.clear()
        self.cursors.clear()
        self.presence.clear()

    async def broadcast_to_board(self, board_id: uuid.UUID, message: dict, exclude_user: Optional[uuid.UUID] = None):
        if board_id not in self.board_connections:
            return
        import json
        data = json.dumps(message, default=str)
        dead = []
        for uid, ws in self.board_connections[board_id].items():
            if uid == exclude_user:
                continue
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(uid)
        for uid in dead:
            await self.disconnect(board_id, uid)

    def get_board_presence(self, board_id: uuid.UUID) -> list[dict]:
        if board_id not in self.presence:
            return []
        return [
            {"user_id": str(uid), **info}
            for uid, info in self.presence[board_id].items()
        ]

    def update_cursor(self, board_id: uuid.UUID, user_id: uuid.UUID, x: float, y: float):
        if board_id in self.cursors:
            user_info = self.presence.get(board_id, {}).get(user_id, {})
            self.cursors[board_id][user_id] = {
                "x": x, "y": y,
                "name": user_info.get("name", "Anonymous"),
                "color": user_info.get("color", "#4a90e2"),
                "last_update": time.time(),
            }

    def _user_color(self, user_id: uuid.UUID) -> str:
        colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#e67e22", "#34495e"]
        return colors[hash(str(user_id)) % len(colors)]


# Global singleton
manager = ConnectionManager()
