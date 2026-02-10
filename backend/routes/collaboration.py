"""Real-time collaboration WebSocket routes."""

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from ..auth.jwt_handler import decode_access_token
from ..collaboration.manager import manager
from ..database.connection import get_db_context
from ..database import crud

logger = logging.getLogger(__name__)

router = APIRouter(tags=["collaboration"])


@router.websocket("/ws/boards/{board_id}")
async def board_websocket(
    websocket: WebSocket,
    board_id: str,
    token: str = Query(default=None),
):
    """WebSocket endpoint for real-time board collaboration."""
    # Auth via query param token
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id_str = payload.get("sub")
    if not user_id_str:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    try:
        user_id = uuid.UUID(user_id_str)
        bid = uuid.UUID(board_id)
    except ValueError:
        await websocket.close(code=4002, reason="Invalid ID format")
        return

    # Get user info
    user_name = "Anonymous"
    avatar_url = None
    try:
        async with get_db_context() as db:
            user = await crud.users.get_by_id(db, user_id)
            if user:
                user_name = user.name or user.email.split("@")[0]
                avatar_url = user.avatar_url
    except Exception as e:
        logger.warning(f"Failed to fetch user info: {e}")

    # Connect
    await manager.connect(bid, user_id, websocket, user_name, avatar_url)

    # Broadcast join
    await manager.broadcast_to_board(bid, {
        "type": "user_joined",
        "user_id": str(user_id),
        "name": user_name,
        "color": manager.presence.get(bid, {}).get(user_id, {}).get("color", "#4a90e2"),
        "users": manager.get_board_presence(bid),
    }, exclude_user=user_id)

    # Send current presence to the connecting user
    try:
        await websocket.send_text(json.dumps({
            "type": "presence_sync",
            "users": manager.get_board_presence(bid),
        }, default=str))
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type")

            if msg_type == "cursor_move":
                x = message.get("x", 0)
                y = message.get("y", 0)
                manager.update_cursor(bid, user_id, x, y)
                await manager.broadcast_to_board(bid, {
                    "type": "cursor_move",
                    "user_id": str(user_id),
                    "name": user_name,
                    "color": manager.presence.get(bid, {}).get(user_id, {}).get("color", "#4a90e2"),
                    "x": x,
                    "y": y,
                }, exclude_user=user_id)

            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif msg_type in ("card_created", "card_updated", "card_deleted",
                              "edge_created", "edge_deleted", "section_updated",
                              "board_changed"):
                # Relay mutation events from client to other clients
                await manager.broadcast_to_board(bid, {
                    **message,
                    "user_id": str(user_id),
                    "user_name": user_name,
                }, exclude_user=user_id)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket error for user {user_id} on board {board_id}: {e}")
    finally:
        await manager.disconnect(bid, user_id)
        await manager.broadcast_to_board(bid, {
            "type": "user_left",
            "user_id": str(user_id),
            "name": user_name,
            "users": manager.get_board_presence(bid),
        })
