"""Pipeline execution routes for visual DAG pipelines on canvas boards."""

import json
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database.connection import get_db
from ..database.models import User
from ..database import crud as db_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["pipeline"])


def _json_sse(data) -> str:
    """Serialize data to a JSON SSE data line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _get_board(board_id: str, user_id: uuid.UUID, db: AsyncSession):
    """Verify board exists and belongs to the current user."""
    try:
        bid = uuid.UUID(board_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid board_id format")

    board = await db_crud.boards.get_board_by_id(db, bid, user_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


@router.post("/boards/{board_id}/pipeline/execute")
async def execute_pipeline_route(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a visual pipeline (DAG of pl_* cards) as a server-sent events stream.

    Loads all pipeline nodes and edges from the board, topologically sorts them,
    and executes each node in order, streaming progress events back to the client.
    """
    board = await _get_board(board_id, current_user.id, db)

    from ..workflows.pipeline_engine import execute_pipeline

    async def event_generator():
        try:
            async for line in execute_pipeline(str(board.id), db, user_id=current_user.id):
                yield line
        except Exception as exc:
            logger.exception("Pipeline execution failed: board_id=%s", board_id)
            yield _json_sse({"type": "pipeline_error", "error": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
