"""Routes for user-created flow templates."""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database.connection import get_db
from ..database.models import User
from ..database.crud import flow_templates as templates_crud
from ..database.crud import workflows as workflows_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flow-templates", tags=["flow-templates"])


class CreateFlowTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    icon: str = "zap"
    category: str = "custom"
    steps: list = Field(..., min_length=1)
    config: Optional[dict] = None
    project_id: Optional[str] = None


class UpdateFlowTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    steps: Optional[list] = None
    config: Optional[dict] = None
    is_public: Optional[bool] = None


def _serialize_template(t) -> dict:
    return {
        "id": str(t.id),
        "user_id": str(t.user_id),
        "project_id": str(t.project_id) if t.project_id else None,
        "name": t.name,
        "description": t.description,
        "icon": t.icon,
        "category": t.category,
        "steps": t.steps,
        "config": t.config,
        "is_public": t.is_public,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_template(
    request: CreateFlowTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project_id = uuid.UUID(request.project_id) if request.project_id else None
    template = await templates_crud.create_template(
        db,
        user_id=current_user.id,
        name=request.name,
        steps=request.steps,
        project_id=project_id,
        description=request.description,
        icon=request.icon,
        category=request.category,
        config=request.config,
    )
    await db.commit()
    return _serialize_template(template)


@router.get("")
async def list_templates(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pid = uuid.UUID(project_id) if project_id else None
    templates = await templates_crud.list_templates(db, current_user.id, pid)
    return {"templates": [_serialize_template(t) for t in templates]}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template_id")
    template = await templates_crud.get_template(db, tid)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _serialize_template(template)


@router.patch("/{template_id}")
async def update_template(
    template_id: str,
    request: UpdateFlowTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template_id")
    updates = request.model_dump(exclude_unset=True)
    template = await templates_crud.update_template(db, tid, current_user.id, **updates)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.commit()
    return _serialize_template(template)


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template_id")
    deleted = await templates_crud.delete_template(db, tid, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.commit()
    return {"ok": True}


@router.post("/from-user-template/{template_id}/boards/{board_id}", status_code=status.HTTP_201_CREATED)
async def create_workflow_from_user_template_legacy(
    template_id: str,
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a workflow on a board from a user-created template (legacy URL)."""
    return await _create_workflow_from_template(template_id, board_id, current_user, db)


@router.post("/{template_id}/create-workflow/{board_id}", status_code=status.HTTP_201_CREATED)
async def create_workflow_from_user_template(
    template_id: str,
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a workflow on a board from a user-created template."""
    return await _create_workflow_from_template(template_id, board_id, current_user, db)


async def _create_workflow_from_template(
    template_id: str,
    board_id: str,
    current_user: User,
    db: AsyncSession,
):
    """Shared logic for creating a workflow from a user template."""
    try:
        tid = uuid.UUID(template_id)
        bid = uuid.UUID(board_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    template = await templates_crud.get_template(db, tid)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    from ..database.crud import boards as boards_crud
    board = await boards_crud.get_board_by_id(db, bid, current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    workflow = await workflows_crud.create_workflow(
        db,
        board_id=bid,
        user_id=current_user.id,
        name=template.name,
        description=template.description,
        steps=template.steps,
    )
    await db.commit()

    workflow = await workflows_crud.get_workflow_by_id(db, workflow.id, bid)
    return {
        "id": str(workflow.id),
        "board_id": str(workflow.board_id),
        "name": workflow.name,
        "description": workflow.description,
        "status": workflow.status,
        "steps": [
            {
                "id": str(s.id),
                "step_index": s.step_index,
                "step_type": s.step_type,
                "name": s.name,
                "prompt_template": s.prompt_template,
                "config": s.config,
                "status": s.status,
            }
            for s in (workflow.steps or [])
        ],
    }
