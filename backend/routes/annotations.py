"""API routes for PDF annotations."""

import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from ..database import crud as db_crud
from ..auth.dependencies import get_current_user
from ..utils import parse_uuid

router = APIRouter(prefix="/api", tags=["annotations"])


# ---- Pydantic models ----

class RectModel(BaseModel):
    x: float
    y: float
    width: float
    height: float


class AddAnnotationRequest(BaseModel):
    page: int = Field(..., ge=0)
    type: str = Field(default="highlight")
    content: str = Field(default="")
    rects: List[RectModel] = Field(default_factory=list)
    color: str = Field(default="#FFEB3B")


class UpdateAnnotationRequest(BaseModel):
    content: Optional[str] = None
    color: Optional[str] = None


class AnnotationResponse(BaseModel):
    id: str
    page: int
    type: str
    content: str
    rects: List[Dict[str, Any]]
    color: str
    created_at: str

    class Config:
        from_attributes = True


# ---- Endpoints ----

@router.get(
    "/attachments/{attachment_id}/annotations",
    response_model=List[AnnotationResponse],
)
async def list_annotations(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all annotations for an attachment."""
    annotations = await db_crud.annotations.get_annotations(
        db, parse_uuid(attachment_id, "attachment_id")
    )
    return annotations


@router.post(
    "/attachments/{attachment_id}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation(
    attachment_id: str,
    request: AddAnnotationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new annotation to an attachment."""
    try:
        annot = await db_crud.annotations.add_annotation(
            db,
            attachment_id=parse_uuid(attachment_id, "attachment_id"),
            page=request.page,
            type=request.type,
            content=request.content,
            rects=[r.model_dump() for r in request.rects],
            color=request.color,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return annot


@router.patch(
    "/attachments/{attachment_id}/annotations/{annotation_id}",
    response_model=AnnotationResponse,
)
async def update_annotation(
    attachment_id: str,
    annotation_id: str,
    request: UpdateAnnotationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing annotation."""
    updated = await db_crud.annotations.update_annotation(
        db,
        attachment_id=parse_uuid(attachment_id, "attachment_id"),
        annotation_id=annotation_id,
        content=request.content,
        color=request.color,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    await db.commit()
    return updated


@router.delete(
    "/attachments/{attachment_id}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_annotation(
    attachment_id: str,
    annotation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an annotation."""
    deleted = await db_crud.annotations.delete_annotation(
        db,
        attachment_id=parse_uuid(attachment_id, "attachment_id"),
        annotation_id=annotation_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Annotation not found")
    await db.commit()
