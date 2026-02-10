"""Supabase-based storage for conversations."""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

_supabase: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create Supabase client."""
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required"
            )
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


# Default anonymous user ID
ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"


# ============ CONVERSATION MANAGEMENT ============


def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        New conversation dict
    """
    supabase = get_supabase()

    conversation = {
        "id": conversation_id,
        "user_id": ANONYMOUS_USER_ID,
        "title": "New Conversation",
        "folder_id": None,
        "tags": [],
    }

    result = supabase.table("conversations").insert(conversation).execute()

    if result.data:
        return {
            "id": result.data[0]["id"],
            "created_at": result.data[0]["created_at"],
            "title": result.data[0]["title"],
            "messages": [],
            "folder_id": result.data[0]["folder_id"],
            "tags": result.data[0]["tags"] or [],
        }

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    supabase = get_supabase()

    # Get conversation
    conv_result = (
        supabase.table("conversations")
        .select("*")
        .eq("id", conversation_id)
        .execute()
    )

    if not conv_result.data:
        return None

    conv = conv_result.data[0]

    # Get messages for this conversation
    msg_result = (
        supabase.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )

    messages = []
    for msg in msg_result.data or []:
        message = {"role": msg["role"]}

        if msg["role"] == "user":
            message["content"] = msg["content"]
            if msg.get("attached_files"):
                message["attached_files"] = msg["attached_files"]
        else:
            # Assistant message
            if msg.get("type"):
                message["type"] = msg["type"]

            if msg["type"] == "council":
                message["stage1"] = msg["stage1"] or []
                message["stage2"] = msg["stage2"] or []
                message["stage3"] = msg["stage3"] or {}
            elif msg["type"] == "quick":
                message["content"] = msg["content"]
                message["model"] = msg["model"]
                if msg.get("thinking"):
                    message["thinking"] = msg["thinking"]
                if msg.get("usage"):
                    message["usage"] = msg["usage"]
            elif msg["type"] == "debate":
                message["debate"] = msg["debate"] or {}

        messages.append(message)

    return {
        "id": conv["id"],
        "created_at": conv["created_at"],
        "title": conv["title"],
        "messages": messages,
        "folder_id": conv["folder_id"],
        "tags": conv["tags"] or [],
    }


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage (update metadata only, messages handled separately).

    Args:
        conversation: Conversation dict to save
    """
    supabase = get_supabase()

    supabase.table("conversations").update({
        "title": conversation.get("title", "New Conversation"),
        "folder_id": conversation.get("folder_id"),
        "tags": conversation.get("tags", []),
    }).eq("id", conversation["id"]).execute()


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Returns:
        List of conversation metadata dicts
    """
    supabase = get_supabase()

    result = (
        supabase.table("conversations")
        .select("id, created_at, title, folder_id, tags")
        .order("created_at", desc=True)
        .execute()
    )

    conversations = []
    for conv in result.data or []:
        # Get message count
        count_result = (
            supabase.table("messages")
            .select("id", count="exact")
            .eq("conversation_id", conv["id"])
            .execute()
        )

        conversations.append({
            "id": conv["id"],
            "created_at": conv["created_at"],
            "title": conv["title"],
            "message_count": count_result.count or 0,
            "folder_id": conv["folder_id"],
            "tags": conv["tags"] or [],
        })

    return conversations


def add_user_message(
    conversation_id: str,
    content: str,
    attached_files: Optional[List[str]] = None
):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
        attached_files: Optional list of filenames attached to this message
    """
    supabase = get_supabase()

    message = {
        "conversation_id": conversation_id,
        "role": "user",
        "content": content,
        "attached_files": attached_files or [],
    }

    supabase.table("messages").insert(message).execute()


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any]
):
    """
    Add an assistant message with all 3 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
    """
    supabase = get_supabase()

    message = {
        "conversation_id": conversation_id,
        "role": "assistant",
        "type": "council",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
    }

    supabase.table("messages").insert(message).execute()


def add_quick_message(
    conversation_id: str,
    content: str,
    model: str,
    thinking: Optional[str] = None,
    usage: Optional[Dict[str, Any]] = None
):
    """
    Add a quick mode assistant message (single model, no council deliberation).

    Args:
        conversation_id: Conversation identifier
        content: Model response content
        model: Model identifier that generated the response
        thinking: Optional thinking/reasoning content for reasoning models
        usage: Optional token usage information
    """
    supabase = get_supabase()

    message = {
        "conversation_id": conversation_id,
        "role": "assistant",
        "type": "quick",
        "content": content,
        "model": model,
        "thinking": thinking,
        "usage": usage,
    }

    supabase.table("messages").insert(message).execute()


def add_debate_message(conversation_id: str, debate_result: Dict[str, Any]):
    """
    Add a debate message to a conversation.

    Args:
        conversation_id: Conversation identifier
        debate_result: Complete debate results with rounds and synthesis
    """
    supabase = get_supabase()

    message = {
        "conversation_id": conversation_id,
        "role": "assistant",
        "type": "debate",
        "debate": debate_result,
    }

    supabase.table("messages").insert(message).execute()


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    supabase = get_supabase()

    supabase.table("conversations").update({
        "title": title
    }).eq("id", conversation_id).execute()


def delete_conversation(conversation_id: str) -> bool:
    """
    Delete a conversation.

    Args:
        conversation_id: Conversation identifier

    Returns:
        True if deleted, False if conversation not found
    """
    supabase = get_supabase()

    # Check if exists first
    result = (
        supabase.table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .execute()
    )

    if not result.data:
        return False

    # Messages will be cascade deleted due to ON DELETE CASCADE
    supabase.table("conversations").delete().eq("id", conversation_id).execute()
    return True


def get_conversation_context(conversation_id: str, limit: int = 3) -> Optional[str]:
    """
    Get summarized context from recent conversation history for follow-ups.

    Args:
        conversation_id: Conversation identifier
        limit: Maximum number of recent exchanges to include (default: 3)

    Returns:
        Summarized context string or None if no history exists
    """
    supabase = get_supabase()

    # Get recent messages
    result = (
        supabase.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )

    if not result.data:
        return None

    messages = result.data
    context_parts = []

    # Process messages in pairs (user + assistant)
    i = 0
    while i < len(messages) - 1:
        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
            user_msg = messages[i]["content"]
            assistant_msg = messages[i + 1]

            # Get assistant response based on type
            if assistant_msg.get("type") == "council":
                stage3 = assistant_msg.get("stage3") or {}
                response = stage3.get("response", "")
            elif assistant_msg.get("type") == "quick":
                response = assistant_msg.get("content", "")
            else:
                response = ""

            context_parts.append({
                "question": user_msg,
                "answer": response
            })
            i += 2
        else:
            i += 1

    # Keep only the last N exchanges
    context_parts = context_parts[-limit:]

    if not context_parts:
        return None

    # Format context as a readable summary
    context_lines = ["Previous conversation context:"]
    for idx, exchange in enumerate(context_parts, 1):
        question = (exchange["question"] or "")[:300]
        answer = (exchange["answer"] or "")[:500]

        context_lines.append(f"\nExchange {idx}:")
        context_lines.append(f"Q: {question}")
        context_lines.append(f"A: {answer}...")

    return "\n".join(context_lines)


# ============ FOLDER MANAGEMENT ============


def list_folders() -> List[Dict[str, Any]]:
    """
    List all folders.

    Returns:
        List of folder dicts
    """
    supabase = get_supabase()

    result = supabase.table("folders").select("*").execute()
    return result.data or []


def create_folder(
    name: str, color: str = "#4a90e2", icon: str = "folder"
) -> Dict[str, Any]:
    """
    Create a new folder.

    Args:
        name: Folder name
        color: Hex color code
        icon: Icon name

    Returns:
        New folder dict
    """
    supabase = get_supabase()

    # Generate ID from name
    folder_id = name.lower().replace(" ", "_")

    # Check if ID already exists
    existing = supabase.table("folders").select("id").execute()
    existing_ids = {f["id"] for f in existing.data or []}

    if folder_id in existing_ids:
        counter = 1
        while f"{folder_id}_{counter}" in existing_ids:
            counter += 1
        folder_id = f"{folder_id}_{counter}"

    new_folder = {
        "id": folder_id,
        "user_id": ANONYMOUS_USER_ID,
        "name": name,
        "color": color,
        "icon": icon,
    }

    result = supabase.table("folders").insert(new_folder).execute()
    return result.data[0] if result.data else new_folder


def delete_folder(folder_id: str) -> bool:
    """
    Delete a folder and remove folder_id from all conversations.

    Args:
        folder_id: Folder identifier

    Returns:
        True if deleted, False if not found
    """
    supabase = get_supabase()

    # Check if exists
    result = (
        supabase.table("folders")
        .select("id")
        .eq("id", folder_id)
        .execute()
    )

    if not result.data:
        return False

    # Remove folder_id from conversations
    supabase.table("conversations").update({
        "folder_id": None
    }).eq("folder_id", folder_id).execute()

    # Delete folder
    supabase.table("folders").delete().eq("id", folder_id).execute()
    return True


def move_conversation_to_folder(
    conversation_id: str, folder_id: Optional[str]
) -> bool:
    """
    Move a conversation to a folder.

    Args:
        conversation_id: Conversation identifier
        folder_id: Folder identifier (None to remove from folder)

    Returns:
        True if successful, False if conversation not found
    """
    supabase = get_supabase()

    # Check if conversation exists
    result = (
        supabase.table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .execute()
    )

    if not result.data:
        return False

    supabase.table("conversations").update({
        "folder_id": folder_id
    }).eq("id", conversation_id).execute()

    return True


# ============ TAG MANAGEMENT ============


def add_tag(conversation_id: str, tag: str) -> bool:
    """
    Add a tag to a conversation.

    Args:
        conversation_id: Conversation identifier
        tag: Tag to add

    Returns:
        True if successful, False if conversation not found
    """
    supabase = get_supabase()

    # Get current tags
    result = (
        supabase.table("conversations")
        .select("tags")
        .eq("id", conversation_id)
        .execute()
    )

    if not result.data:
        return False

    tags = result.data[0].get("tags") or []
    if tag not in tags:
        tags.append(tag)
        supabase.table("conversations").update({
            "tags": tags
        }).eq("id", conversation_id).execute()

    return True


def remove_tag(conversation_id: str, tag: str) -> bool:
    """
    Remove a tag from a conversation.

    Args:
        conversation_id: Conversation identifier
        tag: Tag to remove

    Returns:
        True if successful, False if conversation not found
    """
    supabase = get_supabase()

    # Get current tags
    result = (
        supabase.table("conversations")
        .select("tags")
        .eq("id", conversation_id)
        .execute()
    )

    if not result.data:
        return False

    tags = result.data[0].get("tags") or []
    if tag in tags:
        tags.remove(tag)
        supabase.table("conversations").update({
            "tags": tags
        }).eq("id", conversation_id).execute()

    return True


def update_tags(conversation_id: str, tags: List[str]) -> bool:
    """
    Update all tags for a conversation.

    Args:
        conversation_id: Conversation identifier
        tags: List of tags

    Returns:
        True if successful, False if conversation not found
    """
    supabase = get_supabase()

    # Check if exists
    result = (
        supabase.table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .execute()
    )

    if not result.data:
        return False

    supabase.table("conversations").update({
        "tags": tags
    }).eq("id", conversation_id).execute()

    return True


def list_all_tags() -> List[str]:
    """
    List all unique tags across all conversations.

    Returns:
        Sorted list of unique tags
    """
    supabase = get_supabase()

    result = supabase.table("conversations").select("tags").execute()

    all_tags = set()
    for conv in result.data or []:
        tags = conv.get("tags") or []
        all_tags.update(tags)

    return sorted(list(all_tags))
