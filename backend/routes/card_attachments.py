"""API routes for card attachments."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from ..database import crud as db_crud
from ..auth.dependencies import get_current_user
from ..utils import parse_uuid

router = APIRouter(prefix="/api", tags=["attachments"])


class EmbedRequest(BaseModel):
    url: str
    title: Optional[str] = None
    file_type: str = "embed"


class AttachmentResponse(BaseModel):
    id: str
    card_id: str
    filename: str
    file_type: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    url: Optional[str] = None
    embed_url: Optional[str] = None
    content_text: Optional[str] = None
    rag_indexed: bool = False
    created_at: str

    class Config:
        from_attributes = True


def _serialize(att) -> dict:
    return {
        "id": str(att.id),
        "card_id": str(att.card_id),
        "filename": att.filename,
        "file_type": att.file_type,
        "mime_type": att.mime_type,
        "file_size": att.file_size,
        "url": att.url,
        "embed_url": att.embed_url,
        "content_text": att.content_text[:200] if att.content_text else None,
        "rag_indexed": att.rag_indexed,
        "metadata_json": att.metadata_json or {},
        "created_at": att.created_at.isoformat() if att.created_at else None,
    }


@router.post("/cards/{card_id}/attachments/upload", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    card_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    file_size = len(content)

    # Determine file type
    mime = file.content_type or ""
    if mime.startswith("image/"):
        file_type = "image"
    elif mime == "application/pdf":
        file_type = "pdf"
    elif mime.startswith("video/"):
        file_type = "video"
    elif mime.startswith("audio/"):
        file_type = "audio"
    else:
        file_type = "file"

    # For now store as data URL (in production, use object storage)
    import base64
    data_url = f"data:{mime};base64,{base64.b64encode(content).decode()}"

    # Extract text from PDF if applicable
    content_text = None
    if file_type == "pdf":
        try:
            from ..files import extract_pdf_text
            content_text = extract_pdf_text(content)
        except Exception:
            pass

    attachment = await db_crud.card_attachments.create_attachment(
        db,
        card_id=parse_uuid(card_id, "card_id"),
        user_id=current_user.id,
        filename=file.filename or "untitled",
        file_type=file_type,
        mime_type=mime,
        file_size=file_size,
        url=data_url,
        content_text=content_text,
    )
    await db.commit()
    return _serialize(attachment)


@router.post("/cards/{card_id}/attachments/embed", status_code=status.HTTP_201_CREATED)
async def add_embed(
    card_id: str,
    request: EmbedRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attachment = await db_crud.card_attachments.create_attachment(
        db,
        card_id=parse_uuid(card_id, "card_id"),
        user_id=current_user.id,
        filename=request.title or request.url,
        file_type=request.file_type,
        embed_url=request.url,
    )
    await db.commit()
    return _serialize(attachment)


@router.get("/cards/{card_id}/attachments")
async def list_card_attachments(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attachments = await db_crud.card_attachments.list_attachments(db, parse_uuid(card_id, "card_id"))
    return {"attachments": [_serialize(a) for a in attachments]}


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await db_crud.card_attachments.delete_attachment(
        db, parse_uuid(attachment_id, "attachment_id"), current_user.id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Attachment not found")
    await db.commit()
