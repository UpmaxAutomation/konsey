"""Agent routes for LLM Council canvas boards."""

import json
import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database.connection import get_db
from ..database.models import User
from ..database import crud as db_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agents"])


# ──────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    model: str = "openai/gpt-4o"
    max_iterations: int = Field(default=20, ge=1, le=100)


# ──────────────────────────────────────────────
# Serialization helpers
# ──────────────────────────────────────────────

def _serialize_run(run) -> dict:
    return {
        "id": str(run.id),
        "board_id": str(run.board_id),
        "user_id": str(run.user_id),
        "goal": run.goal,
        "model": run.model,
        "status": run.status,
        "iteration_count": run.iteration_count,
        "max_iterations": run.max_iterations,
        "thoughts_log": run.thoughts_log,
        "created_card_ids": run.created_card_ids,
        "error": run.error,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
    }


# ──────────────────────────────────────────────
# Board ownership helper
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
# SSE streaming helper
# ──────────────────────────────────────────────

def _json_sse(data: Any) -> str:
    """Serialize data to a JSON SSE data line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ──────────────────────────────────────────────
# Agent run endpoints
# ──────────────────────────────────────────────

@router.post("/boards/{board_id}/agent/run")
async def start_agent_run(
    board_id: str,
    request: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new agent run on a board.

    Checks for an active run first and returns 409 if one exists.
    Streams progress events as server-sent events.
    """
    board = await _get_board(board_id, current_user.id, db)

    # Check for active run (enforce one active run per board)
    active_run = await db_crud.agent_runs.get_active_run(db, board.id)
    if active_run:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An agent run is already active on this board",
        )

    from ..workflows.agent import run_canvas_agent

    async def event_generator():
        try:
            async for event in run_canvas_agent(
                board_id=board.id,
                user_id=current_user.id,
                goal=request.goal,
                model=request.model,
                max_iterations=request.max_iterations,
                db=db,
            ):
                yield _json_sse(event)
        except Exception as exc:
            logger.exception("Agent run failed: board_id=%s", board_id)
            yield _json_sse({"type": "agent_error", "error": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/boards/{board_id}/agent/{run_id}/pause")
async def pause_agent_run(
    board_id: str,
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause an active agent run."""
    board = await _get_board(board_id, current_user.id, db)

    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")

    run = await db_crud.agent_runs.get_agent_run(db, rid, board.id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    if run.status != "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot pause agent run in '{run.status}' status",
        )

    run = await db_crud.agent_runs.update_run(db, rid, board.id, status="paused")
    await db.commit()
    return {"status": "paused"}


@router.post("/boards/{board_id}/agent/{run_id}/resume")
async def resume_agent_run(
    board_id: str,
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused agent run.

    Sets the run status back to running and streams remaining events as SSE.
    """
    board = await _get_board(board_id, current_user.id, db)

    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")

    run = await db_crud.agent_runs.get_agent_run(db, rid, board.id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    if run.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot resume agent run in '{run.status}' status",
        )

    # Set status back to running before re-entering the agent loop
    await db_crud.agent_runs.update_run(db, rid, board.id, status="running")
    await db.commit()

    from ..workflows.agent import run_canvas_agent

    async def event_generator():
        try:
            async for event in run_canvas_agent(
                board_id=board.id,
                user_id=current_user.id,
                goal=run.goal,
                model=run.model,
                max_iterations=run.max_iterations,
                db=db,
                run_id=rid,
            ):
                yield _json_sse(event)
        except Exception as exc:
            logger.exception("Agent resume failed: run_id=%s", run_id)
            yield _json_sse({"type": "agent_error", "error": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/boards/{board_id}/agent/{run_id}/cancel")
async def cancel_agent_run(
    board_id: str,
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running or paused agent run."""
    board = await _get_board(board_id, current_user.id, db)

    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")

    run = await db_crud.agent_runs.get_agent_run(db, rid, board.id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    if run.status not in ("running", "paused"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel agent run in '{run.status}' status",
        )

    await db_crud.agent_runs.update_run(db, rid, board.id, status="cancelled")
    await db.commit()
    return {"status": "cancelled"}


@router.get("/boards/{board_id}/agent/runs")
async def list_agent_runs(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all agent runs for a board, ordered by most recent first."""
    board = await _get_board(board_id, current_user.id, db)
    runs = await db_crud.agent_runs.list_runs(db, board.id)
    return {"runs": [_serialize_run(r) for r in runs]}
