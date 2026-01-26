"""CRUD operations for conversations and messages."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Conversation, Message


# Conversation operations

async def get_by_id(db: AsyncSession, conversation_id: uuid.UUID) -> Optional[Conversation]:
    """Get conversation by ID."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def get_by_id_with_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Conversation]:
    """Get conversation with messages, ensuring user ownership."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def list_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    folder_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    skip: int = 0,
    limit: int = 100,
    include_messages: bool = False
) -> List[Conversation]:
    """List conversations for a user with optional filters.

    Args:
        include_messages: If True, eagerly load messages (expensive for lists).
                         Default False for performance - use get_by_id_with_messages
                         when you need the full conversation.
    """
    query = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )

    # Only load messages if explicitly requested (for detail views)
    if include_messages:
        query = query.options(selectinload(Conversation.messages))

    if folder_id is not None:
        query = query.where(Conversation.folder_id == folder_id)

    if tags:
        # Match conversations that have any of the specified tags
        query = query.where(Conversation.tags.overlap(tags))

    result = await db.execute(query)
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str = "New Conversation",
    folder_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[uuid.UUID] = None
) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
        id=conversation_id,
        user_id=user_id,
        title=title,
        folder_id=folder_id,
        tags=tags or [],
        project_id=project_id,
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def update_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    **kwargs
) -> Optional[Conversation]:
    """Update conversation fields (with user ownership check)."""
    kwargs["updated_at"] = datetime.now(timezone.utc)
    await db.execute(
        update(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        .values(**kwargs)
    )
    return await get_by_id(db, conversation_id)


async def delete_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID
) -> bool:
    """Delete conversation (with user ownership check)."""
    result = await db.execute(
        delete(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    return result.rowcount > 0


async def move_to_folder(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    folder_id: Optional[str]
) -> Optional[Conversation]:
    """Move conversation to folder."""
    return await update_conversation(db, conversation_id, user_id, folder_id=folder_id)


async def move_to_project(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID]
) -> Optional[Conversation]:
    """Move conversation to project."""
    return await update_conversation(db, conversation_id, user_id, project_id=project_id)


async def update_tags(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    tags: List[str]
) -> Optional[Conversation]:
    """Update conversation tags."""
    return await update_conversation(db, conversation_id, user_id, tags=tags)


async def search(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    folder_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50
) -> List[Conversation]:
    """Search conversations by title or content."""
    search_query = (
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.title.ilike(f"%{query}%")
        )
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )

    if folder_id:
        search_query = search_query.where(Conversation.folder_id == folder_id)

    if tags:
        search_query = search_query.where(Conversation.tags.overlap(tags))

    result = await db.execute(search_query)
    return list(result.scalars().all())


async def get_all_tags(db: AsyncSession, user_id: uuid.UUID) -> List[str]:
    """Get all unique tags used by a user."""
    result = await db.execute(
        select(func.unnest(Conversation.tags).label("tag"))
        .where(Conversation.user_id == user_id)
        .distinct()
    )
    return [row[0] for row in result.fetchall()]


# Admin operations

async def list_all(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    user_filter: Optional[uuid.UUID] = None,
    include_messages: bool = False
) -> List[Conversation]:
    """List all conversations (admin only). Optionally filter by user.

    Args:
        include_messages: If True, eagerly load messages. Default False for performance.
    """
    query = (
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if include_messages:
        query = query.options(selectinload(Conversation.messages))

    if user_filter:
        query = query.where(Conversation.user_id == user_filter)

    result = await db.execute(query)
    return list(result.scalars().all())


async def count_all(db: AsyncSession, user_filter: Optional[uuid.UUID] = None) -> int:
    """Count all conversations (admin only)."""
    query = select(func.count(Conversation.id))
    if user_filter:
        query = query.where(Conversation.user_id == user_filter)
    result = await db.execute(query)
    return result.scalar() or 0


async def admin_get_by_id(
    db: AsyncSession,
    conversation_id: uuid.UUID
) -> Optional[Conversation]:
    """Get any conversation by ID (admin only, no user check)."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


# Message operations

async def add_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: Optional[str] = None,
    message_type: str = "council",
    stage1: Optional[dict] = None,
    stage2: Optional[dict] = None,
    stage3: Optional[dict] = None,
    metadata: Optional[dict] = None,
    thinking: Optional[str] = None,
    model: Optional[str] = None,
    usage_info: Optional[dict] = None,
    attached_files: Optional[List[str]] = None
) -> Message:
    """Add a message to a conversation."""
    # Get next message index (lock conversation to avoid concurrent increments)
    await db.execute(
        select(Conversation.id)
        .where(Conversation.id == conversation_id)
        .with_for_update()
    )
    result = await db.execute(
        select(func.max(Message.message_index))
        .where(Message.conversation_id == conversation_id)
    )
    max_index = result.scalar() or -1

    message = Message(
        conversation_id=conversation_id,
        message_index=max_index + 1,
        role=role,
        content=content,
        message_type=message_type,
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        metadata=metadata,
        thinking=thinking,
        model=model,
        usage_info=usage_info,
        attached_files=attached_files or [],
    )
    db.add(message)

    # Update conversation timestamp
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=datetime.now(timezone.utc))
    )

    await db.flush()
    return message


async def get_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    limit: Optional[int] = None
) -> List[Message]:
    """Get messages for a conversation."""
    query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.message_index)
    )

    if limit:
        query = query.limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_context(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    last_n: int = 5
) -> List[dict]:
    """Get last N messages for context (for follow-up queries)."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.message_index.desc())
        .limit(last_n * 2)  # Get more to ensure we have pairs
    )
    messages = list(result.scalars().all())
    messages.reverse()  # Put in chronological order

    context = []
    for msg in messages:
        if msg.role == "user":
            context.append({"role": "user", "content": msg.content})
        elif msg.role == "assistant" and msg.stage3:
            # Use the final synthesized response for context
            response = msg.stage3.get("response", "") if isinstance(msg.stage3, dict) else str(msg.stage3)
            context.append({"role": "assistant", "content": response})

    return context[-last_n * 2:]  # Return last N exchanges
