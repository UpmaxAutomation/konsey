"""Conversation CRUD routes for LLM Council."""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_optional
from ..database.connection import get_db
from ..database.models import User
from .. import storage_adapter as storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["conversations"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class ImportConversationRequest(BaseModel):
    """Request to import a conversation from exported JSON."""
    title: Optional[str] = None
    messages: List[Dict[str, Any]]
    created_at: Optional[str] = None
    folder_id: Optional[str] = None
    tags: Optional[List[str]] = None


class ForkConversationRequest(BaseModel):
    """Request to fork a conversation from a specific message."""
    message_index: int  # Include messages up to and including this index


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]
    folder_id: Optional[str] = None
    tags: Optional[List[str]] = None


# ──────────────────────────────────────────────
# Conversation CRUD endpoints
# ──────────────────────────────────────────────

@router.get(
    "/conversations",
    summary="List All Conversations",
    response_model=List[ConversationMetadata],
    response_description="List of conversation metadata",
)
async def list_conversations(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    List all conversations (metadata only) - user-specific if authenticated.

    Returns a list of conversations with basic metadata including
    ID, title, creation date, and message count. Does not include
    full message content for performance.

    Args:
        current_user: Authenticated user (optional - if None, returns all for anonymous)

    Returns:
        List[ConversationMetadata]: List of conversation summaries
    """
    try:
        user_id = current_user.id if current_user else None
        result = await storage.list_conversations(user_id=user_id, db=db)
        return result
    except Exception as e:
        logger.exception("list_conversations_error", error=str(e))
        raise


@router.post(
    "/conversations",
    summary="Create New Conversation",
    response_model=Conversation,
    response_description="Created conversation object",
    status_code=201,
)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new conversation (user-specific if authenticated).

    Initializes a new empty conversation that can receive messages.
    The conversation will be assigned a unique UUID and associated with the user.

    Args:
        request: CreateConversationRequest (can be empty)
        current_user: Authenticated user (optional - if None, uses anonymous user)

    Returns:
        Conversation: The created conversation with id and metadata
    """
    conversation_id = str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    try:
        conversation = await storage.create_conversation(
            conversation_id,
            user_id=user_id,
            db=db,
        )
        return conversation
    except Exception as exc:
        logger.exception(
            "create_conversation_error",
            conversation_id=conversation_id,
            user_id=str(user_id) if user_id else None,
            error=str(exc),
        )
        raise


@router.get(
    "/conversations/{conversation_id}",
    summary="Get Conversation",
    response_model=Conversation,
    response_description="Full conversation with all messages",
)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific conversation with all its messages (user-scoped if authenticated).

    Returns the complete conversation including all user messages
    and assistant responses with their Stage 1, 2, and 3 results.

    Args:
        conversation_id: The unique conversation identifier
        current_user: Authenticated user (optional - verifies ownership if provided)
        db: Database session

    Returns:
        Conversation: Full conversation with all messages

    Raises:
        HTTPException 404: If conversation not found or user doesn't have access
    """
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None and current_user:
        # Fallback to anonymous conversation (created before login)
        conversation = await storage.get_conversation(conversation_id, user_id=None, db=db)
    if conversation is None:
        # If conversation is missing, attempt to create it to avoid upload race
        try:
            conversation = await storage.create_conversation(
                conversation_id,
                user_id=user_id,
                db=db,
            )
        except Exception:
            conversation = None
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete(
    "/conversations/{conversation_id}",
    summary="Delete Conversation",
    response_description="Confirmation of deletion",
)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a conversation.

    Permanently removes a conversation and all its messages.
    This action cannot be undone.

    Args:
        conversation_id: The unique conversation identifier

    Returns:
        dict: Confirmation with status and message

    Raises:
        HTTPException 404: If conversation not found
    """
    user_id = current_user.id if current_user else None
    deleted = await storage.delete_conversation(
        conversation_id,
        user_id=user_id,
        db=db,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "message": f"Conversation {conversation_id} deleted"}


@router.post(
    "/conversations/import",
    summary="Import Conversation",
    response_model=Conversation,
    response_description="Imported conversation object",
    status_code=201,
)
async def import_conversation(request: ImportConversationRequest):
    """
    Import a conversation from exported JSON data.

    Creates a new conversation with the provided messages and metadata.
    Useful for restoring backups or migrating conversations.

    Args:
        request: ImportConversationRequest with:
            - messages: List of message objects (required)
            - title: Optional conversation title
            - created_at: Optional creation timestamp
            - folder_id: Optional folder to place conversation in
            - tags: Optional list of tags

    Returns:
        Conversation: The imported conversation with new ID
    """
    conversation_id = str(uuid.uuid4())

    # Create conversation with provided or default values
    conversation = {
        "id": conversation_id,
        "created_at": request.created_at or datetime.utcnow().isoformat(),
        "title": request.title or "Imported Conversation",
        "messages": request.messages,
        "folder_id": request.folder_id,
        "tags": request.tags or [],
    }

    # Save to storage
    await storage.save_conversation(conversation)

    logger.info(
        "conversation_imported",
        conversation_id=conversation_id,
        message_count=len(request.messages),
    )

    return conversation


@router.post(
    "/conversations/{conversation_id}/fork",
    summary="Fork Conversation",
    response_model=Conversation,
    response_description="Forked conversation object",
    status_code=201,
)
async def fork_conversation(conversation_id: str, request: ForkConversationRequest):
    """
    Fork a conversation from a specific message.

    Creates a new conversation containing all messages up to and including
    the specified message index. Useful for exploring alternative paths
    in a conversation.

    Args:
        conversation_id: The source conversation to fork from
        request: ForkConversationRequest with:
            - message_index: Include messages up to this index (0-based)

    Returns:
        Conversation: The new forked conversation

    Raises:
        HTTPException 404: If source conversation not found
        HTTPException 400: If message_index is invalid
    """
    # Get the source conversation
    source = await storage.get_conversation(conversation_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Validate message index
    if request.message_index < 0 or request.message_index >= len(source["messages"]):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid message_index: {request.message_index}. Must be 0-{len(source['messages'])-1}",
        )

    # Create new conversation with messages up to and including the index
    new_id = str(uuid.uuid4())
    forked_messages = source["messages"][: request.message_index + 1]

    forked_conversation = {
        "id": new_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": f"{source['title']} (Fork)",
        "messages": forked_messages,
        "folder_id": source.get("folder_id"),
        "tags": source.get("tags", []),
    }

    # Save to storage
    await storage.save_conversation(forked_conversation)

    logger.info(
        "conversation_forked",
        source_id=conversation_id,
        fork_id=new_id,
        message_count=len(forked_messages),
    )

    return forked_conversation
