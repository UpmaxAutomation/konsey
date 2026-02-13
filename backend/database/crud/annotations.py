"""CRUD operations for PDF annotations."""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CardAttachment


async def get_annotations(db: AsyncSession, attachment_id: uuid.UUID) -> List[Dict]:
    """Get all annotations for an attachment."""
    result = await db.execute(
        select(CardAttachment).where(CardAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        return []
    meta = attachment.metadata_json or {}
    return meta.get("annotations", [])


async def add_annotation(
    db: AsyncSession,
    attachment_id: uuid.UUID,
    page: int,
    type: str,
    content: str,
    rects: List[Dict],
    color: str = "#FFEB3B",
) -> Dict:
    """Add annotation to attachment."""
    result = await db.execute(
        select(CardAttachment).where(CardAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise ValueError("Attachment not found")

    meta = dict(attachment.metadata_json or {})
    annotations = list(meta.get("annotations", []))

    annot = {
        "id": str(uuid.uuid4()),
        "page": page,
        "type": type,
        "content": content,
        "rects": rects,
        "color": color,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    annotations.append(annot)
    meta["annotations"] = annotations

    await db.execute(
        update(CardAttachment)
        .where(CardAttachment.id == attachment_id)
        .values(metadata_json=meta)
    )
    return annot


async def update_annotation(
    db: AsyncSession,
    attachment_id: uuid.UUID,
    annotation_id: str,
    content: Optional[str] = None,
    color: Optional[str] = None,
) -> Optional[Dict]:
    """Update a specific annotation by id. Returns updated annotation or None if not found."""
    result = await db.execute(
        select(CardAttachment).where(CardAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        return None

    meta = dict(attachment.metadata_json or {})
    annotations = list(meta.get("annotations", []))

    updated = None
    for i, annot in enumerate(annotations):
        if annot.get("id") == annotation_id:
            if content is not None:
                annotations[i] = {**annot, "content": content}
            if color is not None:
                annotations[i] = {**annotations[i], "color": color}
            updated = annotations[i]
            break

    if updated is None:
        return None

    meta["annotations"] = annotations
    await db.execute(
        update(CardAttachment)
        .where(CardAttachment.id == attachment_id)
        .values(metadata_json=meta)
    )
    return updated


async def delete_annotation(
    db: AsyncSession,
    attachment_id: uuid.UUID,
    annotation_id: str,
) -> bool:
    """Delete a specific annotation by id. Returns True if deleted."""
    result = await db.execute(
        select(CardAttachment).where(CardAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        return False

    meta = dict(attachment.metadata_json or {})
    annotations = list(meta.get("annotations", []))

    original_len = len(annotations)
    annotations = [a for a in annotations if a.get("id") != annotation_id]

    if len(annotations) == original_len:
        return False

    meta["annotations"] = annotations
    await db.execute(
        update(CardAttachment)
        .where(CardAttachment.id == attachment_id)
        .values(metadata_json=meta)
    )
    return True
