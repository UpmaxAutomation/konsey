"""Workflow routes for LLM Council canvas boards."""

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
from ..workflows.templates import list_templates, get_template
from ..database.crud import workflows as workflows_crud
from ..database.crud import workflow_runs as runs_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/boards/{board_id}/workflows", tags=["workflows"])
templates_router = APIRouter(prefix="/api", tags=["workflow-templates"])


# ──────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────

class CreateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    steps: list[dict] = Field(
        default_factory=list,
        description="List of step definitions: [{step_index, step_type, name, prompt_template, config}]",
    )


class RunWorkflowRequest(BaseModel):
    initial_input: str = ""
    context_card_ids: list[str] = Field(default_factory=list)


# ──────────────────────────────────────────────
# Serialization helpers
# ──────────────────────────────────────────────

def _serialize_workflow(workflow) -> dict:
    return {
        "id": str(workflow.id),
        "board_id": str(workflow.board_id),
        "name": workflow.name,
        "description": workflow.description,
        "status": workflow.status,
        "template_id": workflow.template_id,
        "config": workflow.config,
        "current_step_index": workflow.current_step_index,
        "error": workflow.error,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
        "steps": [_serialize_step(s) for s in (workflow.steps or [])],
    }


def _serialize_step(step) -> dict:
    return {
        "id": str(step.id),
        "step_index": step.step_index,
        "step_type": step.step_type,
        "name": step.name,
        "prompt_template": step.prompt_template,
        "config": step.config,
        "status": step.status,
        "input_card_ids": step.input_card_ids,
        "output_card_ids": step.output_card_ids,
        "error": step.error,
        "model": getattr(step, 'model', None),
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
# Workflow CRUD endpoints
# ──────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    board_id: str,
    request: CreateWorkflowRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow on a board."""
    board = await _get_board(board_id, current_user.id, db)

    workflow = await db_crud.workflows.create_workflow(
        db,
        board_id=board.id,
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        steps=request.steps if request.steps else None,
    )
    await db.commit()

    # Re-fetch to get steps loaded after commit
    workflow = await db_crud.workflows.get_workflow_by_id(db, workflow.id, board.id)
    return _serialize_workflow(workflow)


@router.get("")
async def list_workflows(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all workflows for a board."""
    board = await _get_board(board_id, current_user.id, db)
    workflows = await db_crud.workflows.list_workflows(db, board.id)
    return {"workflows": [_serialize_workflow(w) for w in workflows]}


@router.get("/{workflow_id}")
async def get_workflow(
    board_id: str,
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single workflow with all its steps."""
    board = await _get_board(board_id, current_user.id, db)

    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow_id format")

    workflow = await db_crud.workflows.get_workflow_by_id(db, wid, board.id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _serialize_workflow(workflow)


@router.delete("/{workflow_id}")
async def delete_workflow(
    board_id: str,
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a workflow and all its steps."""
    board = await _get_board(board_id, current_user.id, db)

    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow_id format")

    deleted = await db_crud.workflows.delete_workflow(db, wid, board.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────
# Workflow execution endpoints
# ──────────────────────────────────────────────

def _json_sse(data: Any) -> str:
    """Serialize data to a JSON SSE data line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/{workflow_id}/run")
async def run_workflow(
    board_id: str,
    workflow_id: str,
    request: RunWorkflowRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a workflow as a server-sent events stream.

    Each step emits progress events. The stream completes when all
    steps finish or an error / cancellation occurs.
    """
    board = await _get_board(board_id, current_user.id, db)

    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow_id format")

    workflow = await db_crud.workflows.get_workflow_by_id(db, wid, board.id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    from ..workflows.engine import execute_workflow

    async def event_generator():
        try:
            async for event in execute_workflow(
                workflow_id=wid,
                board_id=board.id,
                user_id=current_user.id,
                initial_input=request.initial_input,
                context_card_ids=request.context_card_ids,
                db=db,
            ):
                yield _json_sse(event)
        except Exception as exc:
            logger.exception("Workflow execution failed: workflow_id=%s", workflow_id)
            yield _json_sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/{workflow_id}/approve")
async def approve_workflow_step(
    board_id: str,
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve the current human_review step so the workflow continues."""
    board = await _get_board(board_id, current_user.id, db)

    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow_id format")

    workflow = await db_crud.workflows.get_workflow_by_id(db, wid, board.id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    from ..workflows.engine import approve_workflow_step as _approve

    workflow = await _approve(
        workflow_id=wid,
        board_id=board.id,
        db=db,
    )
    await db.commit()
    return _serialize_workflow(workflow)


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    board_id: str,
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running or paused workflow."""
    board = await _get_board(board_id, current_user.id, db)

    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow_id format")

    workflow = await db_crud.workflows.get_workflow_by_id(db, wid, board.id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow.status not in ("running", "paused", "draft"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel workflow in '{workflow.status}' status",
        )

    workflow = await db_crud.workflows.update_workflow(
        db, wid, board.id, status="cancelled"
    )
    await db.commit()
    return _serialize_workflow(workflow)


# ──────────────────────────────────────────────
# Workflow run history endpoints
# ──────────────────────────────────────────────

@router.get("/{workflow_id}/runs")
async def list_workflow_runs(
    board_id: str,
    workflow_id: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List execution history for a workflow."""
    board = await _get_board(board_id, current_user.id, db)
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow_id format")

    workflow = await db_crud.workflows.get_workflow_by_id(db, wid, board.id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    runs = await runs_crud.list_runs(db, wid, limit=min(limit, 100))
    return {
        "runs": [
            {
                "id": str(r.id),
                "workflow_id": str(r.workflow_id),
                "status": r.status,
                "initial_input": r.initial_input,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "duration_seconds": r.duration_seconds,
                "step_count": r.step_count,
                "output_card_ids": r.output_card_ids,
                "error": r.error,
            }
            for r in runs
        ]
    }


# ──────────────────────────────────────────────
# Workflow template endpoints
# ──────────────────────────────────────────────

@templates_router.get("/workflow-templates")
async def get_workflow_templates(
    current_user: User = Depends(get_current_user),
):
    """Return all available workflow templates."""
    return list_templates()


class CreateFromTemplateRequest(BaseModel):
    template_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=200)


@router.post("/from-template", status_code=status.HTTP_201_CREATED)
async def create_workflow_from_template(
    board_id: str,
    request: CreateFromTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow on a board from a predefined template."""
    board = await _get_board(board_id, current_user.id, db)

    template = get_template(request.template_id)
    if template is None:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{request.template_id}' not found",
        )

    workflow = await workflows_crud.create_workflow(
        db,
        board_id=board.id,
        user_id=current_user.id,
        name=request.name,
        description=template.get("description"),
        template_id=template["id"],
        steps=template["steps"],
    )
    await db.commit()

    # Re-fetch to get steps loaded after commit
    workflow = await workflows_crud.get_workflow_by_id(db, workflow.id, board.id)
    return _serialize_workflow(workflow)
