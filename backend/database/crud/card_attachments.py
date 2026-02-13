"""CRUD operations for card attachments."""

import uuid
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import CardAttachment


async def create_attachment(
    db: AsyncSession,
    card_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    file_type: str = "file",
    mime_type: Optional[str] = None,
    file_size: Optional[int] = None,
    url: Optional[str] = None,
    embed_url: Optional[str] = None,
    content_text: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> CardAttachment:
    attachment = CardAttachment(
        card_id=card_id,
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        mime_type=mime_type,
        file_size=file_size,
        url=url,
        embed_url=embed_url,
        content_text=content_text,
        metadata_json=metadata or {},
    )
    db.add(attachment)
    await db.flush()
    return attachment


async def list_attachments(db: AsyncSession, card_id: uuid.UUID) -> List[CardAttachment]:
    result = await db.execute(
        select(CardAttachment)
        .where(CardAttachment.card_id == card_id)
        .order_by(CardAttachment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_attachment(db: AsyncSession, attachment_id: uuid.UUID) -> Optional[CardAttachment]:
    result = await db.execute(
        select(CardAttachment).where(CardAttachment.id == attachment_id)
    )
    return result.scalar_one_or_none()


async def delete_attachment(db: AsyncSession, attachment_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(CardAttachment).where(
            CardAttachment.id == attachment_id,
            CardAttachment.user_id == user_id,
        )
    )
    return result.rowcount > 0
