"""Storage adapter that switches between JSON and database backends.

Usage:
    Set USE_DATABASE=true in environment to use PostgreSQL.
    Default is JSON file storage for backward compatibility.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .config import USE_DATABASE, ANONYMOUS_USER_ID

# Import both backends
from . import storage as json_storage

if USE_DATABASE:
    from .database.connection import get_db_context
from .database.crud import conversations as db_conversations
from .database.crud import folders as db_folders


def _get_user_id() -> uuid.UUID:
    """Get current user ID. Returns anonymous ID when auth is not available."""
    # TODO: Integrate with auth system to get real user ID
    return uuid.UUID(ANONYMOUS_USER_ID)


# ============ CONVERSATION OPERATIONS ============

async def create_conversation(conversation_id: str, user_id: Optional[uuid.UUID] = None, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """Create a new conversation."""
    if USE_DATABASE:
        if db:
            # Use provided database session
            actual_user_id = user_id or _get_user_id()
            conv = await db_conversations.create(
                db,
                conversation_id=uuid.UUID(conversation_id),
                user_id=actual_user_id,
                title="New Conversation"
            )
            await db.flush()
            result = {
                "id": conversation_id,  # Keep string ID for compatibility
                "created_at": conv.created_at.isoformat(),
                "title": conv.title,
                "messages": [],
                "folder_id": conv.folder_id,
                "tags": conv.tags or []
            }
            return result
        else:
            # Create new session
            async with get_db_context() as db_session:
                actual_user_id = user_id or _get_user_id()
                conv = await db_conversations.create(
                    db_session,
                    conversation_id=uuid.UUID(conversation_id),
                    user_id=actual_user_id,
                    title="New Conversation"
                )
                await db_session.commit()
                result = {
                    "id": conversation_id,
                    "created_at": conv.created_at.isoformat(),
                    "title": conv.title,
                    "messages": [],
                    "folder_id": conv.folder_id,
                    "tags": conv.tags or []
                }
                return result
    else:
        return json_storage.create_conversation(conversation_id)


async def get_conversation(conversation_id: str, user_id: Optional[uuid.UUID] = None, db: Optional[AsyncSession] = None) -> Optional[Dict[str, Any]]:
    """Load a conversation from storage - user-scoped if user_id provided."""
    if USE_DATABASE:
        conv = None
        if db:
            # Use provided database session
            actual_user_id = user_id or _get_user_id()
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                return None
            conv = await db_conversations.get_by_id_with_messages(db, conv_uuid, actual_user_id)
        else:
            # Create new session
            async with get_db_context() as db_session:
                actual_user_id = user_id or _get_user_id()
                try:
                    conv_uuid = uuid.UUID(conversation_id)
                except ValueError:
                    return None
                conv = await db_conversations.get_by_id_with_messages(db_session, conv_uuid, actual_user_id)
        
        if not conv:
            return None

        # Convert to JSON-compatible format
        messages = []
        for msg in conv.messages:
            # Common fields for all messages
            timestamp = msg.created_at.isoformat() if msg.created_at else None

            if msg.role == "user":
                messages.append({
                    "role": "user",
                    "content": msg.content,
                    "attached_files": msg.attached_files or [],
                    "timestamp": timestamp
                })
            else:
                msg_data = {"role": "assistant", "type": msg.message_type, "timestamp": timestamp}
                if msg.message_type == "council":
                    msg_data["stage1"] = msg.stage1 or []
                    msg_data["stage2"] = msg.stage2 or []
                    msg_data["stage3"] = msg.stage3 or {}
                elif msg.message_type == "quick":
                    msg_data["content"] = msg.content
                    msg_data["model"] = msg.model
                    if msg.thinking:
                        msg_data["thinking"] = msg.thinking
                    if msg.usage_info:
                        msg_data["usage"] = msg.usage_info
                elif msg.message_type == "debate":
                    msg_data["debate"] = msg.stage1  # Stored in debates
                messages.append(msg_data)

        return {
            "id": conversation_id,
            "created_at": conv.created_at.isoformat(),
            "title": conv.title,
            "messages": messages,
            "folder_id": conv.folder_id,
            "tags": conv.tags or []
        }
    else:
        return json_storage.get_conversation(conversation_id)


async def save_conversation(conversation: Dict[str, Any]):
    """Save a conversation to storage."""
    if USE_DATABASE:
        # In DB mode, we save incrementally via add_*_message functions
        # This is mainly for compatibility - full save not typically needed
        pass
    else:
        json_storage.save_conversation(conversation)


async def list_conversations(user_id: Optional[uuid.UUID] = None, db: Optional[AsyncSession] = None) -> List[Dict[str, Any]]:
    """List all conversations (metadata only) - user-specific if user_id provided."""
    if USE_DATABASE:
        if db:
            # Use provided database session
            actual_user_id = user_id or _get_user_id()
            if actual_user_id is None:
                # Return empty list for anonymous users in database mode
                return []
            convs = await db_conversations.list_by_user(db, actual_user_id)
            return [
                {
                    "id": str(conv.id),
                    "created_at": conv.created_at.isoformat(),
                    "title": conv.title,
                    # Note: message_count not available in list view for performance
                    # Messages are not eagerly loaded to avoid N+1 queries
                    "message_count": 0,
                    "folder_id": conv.folder_id,
                    "tags": conv.tags or []
                }
                for conv in convs
            ]
        else:
            # Create new session
            async with get_db_context() as db_session:
                actual_user_id = user_id or _get_user_id()
                if actual_user_id is None:
                    # Return empty list for anonymous users in database mode
                    return []
                convs = await db_conversations.list_by_user(db_session, actual_user_id)
                return [
                    {
                        "id": str(conv.id),
                        "created_at": conv.created_at.isoformat(),
                        "title": conv.title,
                        # Note: message_count not available in list view for performance
                        "message_count": 0,
                        "folder_id": conv.folder_id,
                        "tags": conv.tags or []
                    }
                    for conv in convs
                ]
    else:
        return json_storage.list_conversations()


async def add_user_message(
    conversation_id: str,
    content: str,
    attached_files: Optional[List[str]] = None,
    db: Optional[AsyncSession] = None
):
    """Add a user message to a conversation."""
    if USE_DATABASE:
        if db:
            # Use provided database session
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                raise ValueError(f"Invalid conversation ID: {conversation_id}")

            await db_conversations.add_message(
                db,
                conversation_id=conv_uuid,
                role="user",
                content=content,
                message_type="user",
                attached_files=attached_files
            )
            await db.flush()  # Flush to ensure message is saved
        else:
            # Create new session if none provided
            async with get_db_context() as db_session:
                try:
                    conv_uuid = uuid.UUID(conversation_id)
                except ValueError:
                    raise ValueError(f"Invalid conversation ID: {conversation_id}")

                await db_conversations.add_message(
                    db_session,
                    conversation_id=conv_uuid,
                    role="user",
                    content=content,
                    message_type="user",
                    attached_files=attached_files
                )
    else:
        json_storage.add_user_message(conversation_id, content, attached_files)


async def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    db: Optional[AsyncSession] = None
):
    """Add an assistant message with all 3 stages to a conversation."""
    if USE_DATABASE:
        if db:
            # Use provided database session
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                raise ValueError(f"Invalid conversation ID: {conversation_id}")

            await db_conversations.add_message(
                db,
                conversation_id=conv_uuid,
                role="assistant",
                message_type="council",
                stage1=stage1,
                stage2=stage2,
                stage3=stage3
            )
            await db.flush()  # Flush to ensure message is saved
        else:
            # Create new session if none provided
            async with get_db_context() as db_session:
                try:
                    conv_uuid = uuid.UUID(conversation_id)
                except ValueError:
                    raise ValueError(f"Invalid conversation ID: {conversation_id}")

                await db_conversations.add_message(
                    db_session,
                    conversation_id=conv_uuid,
                    role="assistant",
                    message_type="council",
                    stage1=stage1,
                    stage2=stage2,
                    stage3=stage3
                )
    else:
        json_storage.add_assistant_message(conversation_id, stage1, stage2, stage3)


async def add_quick_message(
    conversation_id: str,
    content: str,
    model: str,
    thinking: Optional[str] = None,
    usage: Optional[Dict[str, Any]] = None,
    db: Optional[AsyncSession] = None
):
    """Add a quick mode assistant message."""
    if USE_DATABASE:
        if db:
            # Use provided database session
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                raise ValueError(f"Invalid conversation ID: {conversation_id}")

            await db_conversations.add_message(
                db,
                conversation_id=conv_uuid,
                role="assistant",
                content=content,
                message_type="quick",
                model=model,
                thinking=thinking,
                usage_info=usage
            )
            await db.flush()  # Flush to ensure message is saved
        else:
            # Create new session if none provided
            async with get_db_context() as db_session:
                try:
                    conv_uuid = uuid.UUID(conversation_id)
                except ValueError:
                    raise ValueError(f"Invalid conversation ID: {conversation_id}")

                await db_conversations.add_message(
                    db_session,
                    conversation_id=conv_uuid,
                    role="assistant",
                    content=content,
                    message_type="quick",
                    model=model,
                    thinking=thinking,
                    usage_info=usage
                )
    else:
        json_storage.add_quick_message(conversation_id, content, model, thinking, usage)


async def update_conversation_title(conversation_id: str, title: str, user_id: Optional[uuid.UUID] = None, db: Optional[AsyncSession] = None):
    """Update the title of a conversation."""
    if USE_DATABASE:
        if db:
            # Use provided database session
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                raise ValueError(f"Invalid conversation ID: {conversation_id}")

            actual_user_id = user_id or _get_user_id()
            await db_conversations.update_conversation(
                db, conv_uuid, actual_user_id, title=title
            )
            await db.flush()  # Flush to ensure update is saved
        else:
            # Create new session if none provided
            async with get_db_context() as db_session:
                actual_user_id = user_id or _get_user_id()
                try:
                    conv_uuid = uuid.UUID(conversation_id)
                except ValueError:
                    raise ValueError(f"Invalid conversation ID: {conversation_id}")

                await db_conversations.update_conversation(
                    db_session, conv_uuid, actual_user_id, title=title
                )
    else:
        json_storage.update_conversation_title(conversation_id, title)


async def delete_conversation(
    conversation_id: str,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Delete a conversation (user-scoped if user_id provided)."""
    # Clean up uploaded files before deleting conversation
    from . import files as file_manager
    deleted_files = file_manager.delete_all_files(conversation_id)
    if deleted_files > 0:
        logger.info(f"Deleted {deleted_files} files for conversation {conversation_id}")

    if USE_DATABASE:
        actual_user_id = user_id or _get_user_id()
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError:
            return False

        if db:
            return await db_conversations.delete_conversation(
                db, conv_uuid, actual_user_id
            )

        async with get_db_context() as db_session:
            return await db_conversations.delete_conversation(
                db_session, conv_uuid, actual_user_id
            )
    else:
        return json_storage.delete_conversation(conversation_id)


async def add_debate_message(conversation_id: str, debate_result: Dict[str, Any], db: Optional[AsyncSession] = None):
    """Add a debate message to a conversation."""
    if USE_DATABASE:
        if db:
            # Use provided database session
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                raise ValueError(f"Invalid conversation ID: {conversation_id}")

            await db_conversations.add_message(
                db,
                conversation_id=conv_uuid,
                role="assistant",
                message_type="debate",
                stage1=debate_result  # Store debate in stage1 field
            )
            await db.flush()  # Flush to ensure message is saved
        else:
            # Create new session if none provided
            async with get_db_context() as db_session:
                try:
                    conv_uuid = uuid.UUID(conversation_id)
                except ValueError:
                    raise ValueError(f"Invalid conversation ID: {conversation_id}")

                await db_conversations.add_message(
                    db_session,
                    conversation_id=conv_uuid,
                    role="assistant",
                    message_type="debate",
                    stage1=debate_result  # Store debate in stage1 field
                )
    else:
        json_storage.add_debate_message(conversation_id, debate_result)


async def get_conversation_context(
    conversation_id: str,
    limit: int = 3,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None
) -> Optional[str]:
    """Get summarized context from recent conversation history."""
    if USE_DATABASE:
        if db:
            # Use provided database session
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                return None

            context = await db_conversations.get_context(db, conv_uuid, limit)
            if not context:
                return None

            # Format context as readable summary (matching JSON format)
            context_lines = ["Previous conversation context:"]
            for i, exchange in enumerate(context, 1):
                if exchange["role"] == "user":
                    question = exchange["content"][:300] if exchange["content"] else ""
                    context_lines.append(f"\nExchange {i}:")
                    context_lines.append(f"Q: {question}")
                elif exchange["role"] == "assistant":
                    answer = exchange["content"][:500] if exchange["content"] else ""
                    context_lines.append(f"A: {answer}...")

            return "\n".join(context_lines)
        else:
            # Create new session if none provided
            async with get_db_context() as db_session:
                try:
                    conv_uuid = uuid.UUID(conversation_id)
                except ValueError:
                    return None

                context = await db_conversations.get_context(db_session, conv_uuid, limit)
                if not context:
                    return None

                # Format context as readable summary (matching JSON format)
                context_lines = ["Previous conversation context:"]
                for i, exchange in enumerate(context, 1):
                    if exchange["role"] == "user":
                        question = exchange["content"][:300] if exchange["content"] else ""
                        context_lines.append(f"\nExchange {i}:")
                        context_lines.append(f"Q: {question}")
                    elif exchange["role"] == "assistant":
                        answer = exchange["content"][:500] if exchange["content"] else ""
                        context_lines.append(f"A: {answer}...")

                return "\n".join(context_lines)
    else:
        return json_storage.get_conversation_context(conversation_id, limit)


# ============ FOLDER OPERATIONS ============

async def list_folders(
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> List[Dict[str, Any]]:
    """List all folders."""
    if USE_DATABASE:
        actual_user_id = user_id or _get_user_id()
        if db:
            folders = await db_folders.list_by_user(db, actual_user_id)
        else:
            async with get_db_context() as db_session:
                folders = await db_folders.list_by_user(
                    db_session,
                    actual_user_id,
                )
        return [
            {
                "id": folder.id,
                "name": folder.name,
                "color": folder.color,
                "icon": folder.icon,
                "created_at": folder.created_at.isoformat(),
            }
            for folder in folders
        ]
    else:
        return json_storage.list_folders()


async def create_folder(
    name: str,
    color: str = "#4a90e2",
    icon: str = "folder",
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Create a new folder."""
    if USE_DATABASE:
        actual_user_id = user_id or _get_user_id()
        folder_id = str(uuid.uuid4())
        if db:
            folder = await db_folders.create(
                db,
                folder_id=folder_id,
                user_id=actual_user_id,
                name=name,
                color=color,
                icon=icon,
            )
        else:
            async with get_db_context() as db_session:
                folder = await db_folders.create(
                    db_session,
                    folder_id=folder_id,
                    user_id=actual_user_id,
                    name=name,
                    color=color,
                    icon=icon,
                )
        return {
            "id": folder.id,
            "name": folder.name,
            "color": folder.color,
            "icon": folder.icon,
            "created_at": folder.created_at.isoformat(),
        }
    else:
        return json_storage.create_folder(name, color, icon)


async def delete_folder(
    folder_id: str,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Delete a folder."""
    if USE_DATABASE:
        actual_user_id = user_id or _get_user_id()
        if db:
            return await db_folders.delete_by_id(
                db,
                folder_id=folder_id,
                user_id=actual_user_id,
            )
        async with get_db_context() as db_session:
            return await db_folders.delete_by_id(
                db_session,
                folder_id=folder_id,
                user_id=actual_user_id,
            )
    else:
        return json_storage.delete_folder(folder_id)


async def move_conversation_to_folder(
    conversation_id: str,
    folder_id: Optional[str],
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Move a conversation to a folder."""
    if USE_DATABASE:
        actual_user_id = user_id or _get_user_id()
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError:
            return False

        if db:
            result = await db_conversations.move_to_folder(
                db, conv_uuid, actual_user_id, folder_id
            )
            return result is not None

        async with get_db_context() as db_session:
            result = await db_conversations.move_to_folder(
                db_session, conv_uuid, actual_user_id, folder_id
            )
            return result is not None
    else:
        return json_storage.move_conversation_to_folder(conversation_id, folder_id)


async def move_conversation_to_project(
    conversation_id: str,
    project_id: Optional[str],
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Move a conversation to a project."""
    if USE_DATABASE:
        actual_user_id = user_id or _get_user_id()
        try:
            conv_uuid = uuid.UUID(conversation_id)
            proj_uuid = uuid.UUID(project_id) if project_id else None
        except ValueError:
            return False

        if db:
            result = await db_conversations.move_to_project(
                db, conv_uuid, actual_user_id, proj_uuid
            )
            return result is not None

        async with get_db_context() as db_session:
            result = await db_conversations.move_to_project(
                db_session, conv_uuid, actual_user_id, proj_uuid
            )
            return result is not None
    else:
        # For JSON storage, we need to update the conversation's project_id
        conv = json_storage.get_conversation(conversation_id)
        if not conv:
            return False
        conv["project_id"] = project_id
        json_storage.save_conversation(conv)
        return True


# ============ TAG OPERATIONS ============

async def add_tag(
    conversation_id: str,
    tag: str,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Add a tag to a conversation."""
    if USE_DATABASE:
        conv = await get_conversation(conversation_id, user_id=user_id, db=db)
        if not conv:
            return False
        tags = conv.get("tags", [])
        if tag not in tags:
            tags.append(tag)
            await update_tags(conversation_id, tags, user_id=user_id, db=db)
        return True
    else:
        return json_storage.add_tag(conversation_id, tag)


async def remove_tag(
    conversation_id: str,
    tag: str,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Remove a tag from a conversation."""
    if USE_DATABASE:
        conv = await get_conversation(conversation_id, user_id=user_id, db=db)
        if not conv:
            return False
        tags = conv.get("tags", [])
        if tag in tags:
            tags.remove(tag)
            await update_tags(conversation_id, tags, user_id=user_id, db=db)
        return True
    else:
        return json_storage.remove_tag(conversation_id, tag)


async def update_tags(
    conversation_id: str,
    tags: List[str],
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Update all tags for a conversation."""
    if USE_DATABASE:
        actual_user_id = user_id or _get_user_id()
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError:
            return False

        if db:
            result = await db_conversations.update_tags(
                db, conv_uuid, actual_user_id, tags
            )
            return result is not None

        async with get_db_context() as db_session:
            result = await db_conversations.update_tags(
                db_session, conv_uuid, actual_user_id, tags
            )
            return result is not None
    else:
        return json_storage.update_tags(conversation_id, tags)


async def list_all_tags(
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> List[str]:
    """List all unique tags across all conversations."""
    if USE_DATABASE:
        actual_user_id = user_id or _get_user_id()
        if db:
            return await db_conversations.get_all_tags(db, actual_user_id)
        async with get_db_context() as db_session:
            return await db_conversations.get_all_tags(
                db_session,
                actual_user_id,
            )
    else:
        return json_storage.list_all_tags()


# ============ SYNC WRAPPERS FOR BACKWARD COMPATIBILITY ============
# These allow gradual migration - existing sync code can still work

def create_conversation_sync(conversation_id: str) -> Dict[str, Any]:
    """Sync wrapper for create_conversation."""
    if USE_DATABASE:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            create_conversation(conversation_id)
        )
    return json_storage.create_conversation(conversation_id)


def get_conversation_sync(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Sync wrapper for get_conversation."""
    if USE_DATABASE:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            get_conversation(conversation_id)
        )
    return json_storage.get_conversation(conversation_id)


def list_conversations_sync() -> List[Dict[str, Any]]:
    """Sync wrapper for list_conversations."""
    if USE_DATABASE:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(list_conversations())
    return json_storage.list_conversations()
