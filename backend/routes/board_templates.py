"""Board template and marketplace API routes."""

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db, USE_DATABASE, ANONYMOUS_USER_ID
from ..database.crud import board_templates as bt_crud
from ..database.crud import template_ratings as tr_crud
from ..database.crud import flow_templates as ft_crud

router = APIRouter(prefix="/api", tags=["templates"])


class BoardTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "general"
    icon: str = "layout"
    template_data: dict
    preview_data: Optional[dict] = None
    is_public: bool = False


class RateTemplateBody(BaseModel):
    rating: int = Field(ge=1, le=5)
    review: Optional[str] = None


def _template_to_dict(tmpl) -> dict:
    return {
        "id": str(tmpl.id),
        "user_id": str(tmpl.user_id),
        "project_id": str(tmpl.project_id) if tmpl.project_id else None,
        "name": tmpl.name,
        "description": tmpl.description,
        "category": tmpl.category,
        "icon": tmpl.icon,
        "preview_data": tmpl.preview_data or {},
        "template_data": tmpl.template_data,
        "is_public": tmpl.is_public,
        "use_count": tmpl.use_count,
        "avg_rating": tmpl.avg_rating,
        "rating_count": tmpl.rating_count,
        "created_at": tmpl.created_at.isoformat() if tmpl.created_at else None,
        "updated_at": tmpl.updated_at.isoformat() if tmpl.updated_at else None,
    }


def _rating_to_dict(r) -> dict:
    return {
        "id": str(r.id),
        "user_id": str(r.user_id),
        "template_type": r.template_type,
        "template_id": str(r.template_id),
        "rating": r.rating,
        "review": r.review,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.post("/board-templates")
async def create_board_template(
    body: BoardTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a board as a template."""
    if not USE_DATABASE:
        raise HTTPException(400, "Database not enabled")
    user_id = uuid.UUID(ANONYMOUS_USER_ID)
    tmpl = await bt_crud.create_template(
        db, user_id,
        name=body.name,
        description=body.description,
        category=body.category,
        icon=body.icon,
        template_data=body.template_data,
        preview_data=body.preview_data or {},
        is_public=body.is_public,
    )
    return _template_to_dict(tmpl)


@router.get("/board-templates")
async def list_board_templates(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    public_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List board templates (user's own + public)."""
    if not USE_DATABASE:
        return []
    user_id = uuid.UUID(ANONYMOUS_USER_ID)
    templates = await bt_crud.list_templates(
        db, user_id=user_id, category=category, search=search,
        public_only=public_only, limit=limit, offset=offset,
    )
    return [_template_to_dict(t) for t in templates]


@router.get("/board-templates/{template_id}")
async def get_board_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single board template."""
    if not USE_DATABASE:
        raise HTTPException(404, "Database not enabled")
    tmpl = await bt_crud.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(404, "Template not found")
    return _template_to_dict(tmpl)


@router.post("/board-templates/{template_id}/apply/{board_id}")
async def apply_board_template(
    template_id: uuid.UUID,
    board_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Apply a board template to a board."""
    if not USE_DATABASE:
        raise HTTPException(400, "Database not enabled")
    user_id = uuid.UUID(ANONYMOUS_USER_ID)
    result = await bt_crud.apply_template(db, board_id, template_id, user_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.delete("/board-templates/{template_id}")
async def delete_board_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a board template."""
    if not USE_DATABASE:
        raise HTTPException(400, "Database not enabled")
    user_id = uuid.UUID(ANONYMOUS_USER_ID)
    deleted = await bt_crud.delete_template(db, template_id, user_id)
    if not deleted:
        raise HTTPException(404, "Template not found or not owned")
    return {"status": "deleted"}


@router.post("/templates/{template_type}/{template_id}/rate")
async def rate_template(
    template_type: str,
    template_id: uuid.UUID,
    body: RateTemplateBody,
    db: AsyncSession = Depends(get_db),
):
    """Rate any template type (board, workflow, prompt)."""
    if not USE_DATABASE:
        raise HTTPException(400, "Database not enabled")
    if template_type not in ("board", "workflow", "prompt"):
        raise HTTPException(400, "Invalid template type")
    user_id = uuid.UUID(ANONYMOUS_USER_ID)
    rating = await tr_crud.rate_template(
        db, user_id, template_type, template_id, body.rating, body.review,
    )
    return _rating_to_dict(rating)


@router.get("/templates/{template_type}/{template_id}/ratings")
async def get_template_ratings(
    template_type: str,
    template_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get ratings for a template."""
    if not USE_DATABASE:
        return []
    ratings = await tr_crud.get_ratings(db, template_type, template_id, limit=limit)
    return [_rating_to_dict(r) for r in ratings]


@router.get("/marketplace")
async def marketplace(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    template_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Unified marketplace: browse all public templates."""
    if not USE_DATABASE:
        return {"board_templates": [], "workflow_templates": []}

    results = {}

    if not template_type or template_type == "board":
        board_tmpls = await bt_crud.list_templates(
            db, public_only=True, category=category, search=search, limit=limit, offset=offset,
        )
        results["board_templates"] = [_template_to_dict(t) for t in board_tmpls]

    if not template_type or template_type == "workflow":
        # Reuse flow_templates listing for public workflows
        try:
            from ..database.crud.flow_templates import list_templates as list_flow
            flow_tmpls = await list_flow(db, public_only=True, search=search, limit=limit, offset=offset)
            results["workflow_templates"] = [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "description": t.description,
                    "icon": t.icon,
                    "category": t.category,
                    "is_public": t.is_public,
                    "use_count": getattr(t, "use_count", 0),
                    "avg_rating": getattr(t, "avg_rating", 0),
                    "rating_count": getattr(t, "rating_count", 0),
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in flow_tmpls
            ]
        except Exception:
            results["workflow_templates"] = []

    return results
