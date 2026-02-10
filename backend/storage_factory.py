"""Storage factory that switches between JSON and Supabase storage."""

import os
from typing import List, Dict, Any, Optional

# Check which storage backend to use
USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"

if USE_DATABASE:
    from . import supabase_storage as storage_impl
else:
    from . import storage as storage_impl


# ============ CONVERSATION MANAGEMENT ============

def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """Create a new conversation."""
    return storage_impl.create_conversation(conversation_id)


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Load a conversation from storage."""
    return storage_impl.get_conversation(conversation_id)


def save_conversation(conversation: Dict[str, Any]):
    """Save a conversation to storage."""
    return storage_impl.save_conversation(conversation)


def list_conversations() -> List[Dict[str, Any]]:
    """List all conversations (metadata only)."""
    return storage_impl.list_conversations()


def add_user_message(
    conversation_id: str,
    content: str,
    attached_files: Optional[List[str]] = None
):
    """Add a user message to a conversation."""
    return storage_impl.add_user_message(conversation_id, content, attached_files)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any]
):
    """Add an assistant message with all 3 stages to a conversation."""
    return storage_impl.add_assistant_message(conversation_id, stage1, stage2, stage3)


def add_quick_message(
    conversation_id: str,
    content: str,
    model: str,
    thinking: Optional[str] = None,
    usage: Optional[Dict[str, Any]] = None
):
    """Add a quick mode assistant message."""
    return storage_impl.add_quick_message(conversation_id, content, model, thinking, usage)


def add_debate_message(conversation_id: str, debate_result: Dict[str, Any]):
    """Add a debate message to a conversation."""
    return storage_impl.add_debate_message(conversation_id, debate_result)


def update_conversation_title(conversation_id: str, title: str):
    """Update the title of a conversation."""
    return storage_impl.update_conversation_title(conversation_id, title)


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation."""
    return storage_impl.delete_conversation(conversation_id)


def get_conversation_context(conversation_id: str, limit: int = 3) -> Optional[str]:
    """Get summarized context from recent conversation history."""
    return storage_impl.get_conversation_context(conversation_id, limit)


# ============ FOLDER MANAGEMENT ============

def list_folders() -> List[Dict[str, Any]]:
    """List all folders."""
    return storage_impl.list_folders()


def create_folder(
    name: str, color: str = "#4a90e2", icon: str = "folder"
) -> Dict[str, Any]:
    """Create a new folder."""
    return storage_impl.create_folder(name, color, icon)


def delete_folder(folder_id: str) -> bool:
    """Delete a folder."""
    return storage_impl.delete_folder(folder_id)


def move_conversation_to_folder(
    conversation_id: str, folder_id: Optional[str]
) -> bool:
    """Move a conversation to a folder."""
    return storage_impl.move_conversation_to_folder(conversation_id, folder_id)


# ============ TAG MANAGEMENT ============

def add_tag(conversation_id: str, tag: str) -> bool:
    """Add a tag to a conversation."""
    return storage_impl.add_tag(conversation_id, tag)


def remove_tag(conversation_id: str, tag: str) -> bool:
    """Remove a tag from a conversation."""
    return storage_impl.remove_tag(conversation_id, tag)


def update_tags(conversation_id: str, tags: List[str]) -> bool:
    """Update all tags for a conversation."""
    return storage_impl.update_tags(conversation_id, tags)


def list_all_tags() -> List[str]:
    """List all unique tags across all conversations."""
    return storage_impl.list_all_tags()
