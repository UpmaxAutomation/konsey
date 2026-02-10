"""JSON-based storage for conversations."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR


def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_conversation_path(conversation_id: str) -> str:
    """Get the file path for a conversation."""
    return os.path.join(DATA_DIR, f"{conversation_id}.json")


def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        New conversation dict
    """
    ensure_data_dir()

    conversation = {
        "id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "messages": [],
        "folder_id": None,
        "tags": []
    }

    # Save to file
    path = get_conversation_path(conversation_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Args:
        conversation: Conversation dict to save
    """
    ensure_data_dir()

    path = get_conversation_path(conversation['id'])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(conversation, f, indent=2)


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Returns:
        List of conversation metadata dicts
    """
    ensure_data_dir()

    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json') and not filename == 'folders.json':
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Return metadata only
                conversations.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "title": data.get("title", "New Conversation"),
                    "message_count": len(data["messages"]),
                    "folder_id": data.get("folder_id"),
                    "tags": data.get("tags", [])
                })

    # Sort by creation time, newest first
    conversations.sort(key=lambda x: x["created_at"], reverse=True)

    return conversations


def add_user_message(conversation_id: str, content: str, attached_files: Optional[List[str]] = None):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
        attached_files: Optional list of filenames attached to this message
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    message = {
        "role": "user",
        "content": content
    }

    # Add attached files if provided
    if attached_files:
        message["attached_files"] = attached_files

    conversation["messages"].append(message)

    save_conversation(conversation)


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
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "assistant",
        "type": "council",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3
    })

    save_conversation(conversation)


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
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    message = {
        "role": "assistant",
        "type": "quick",
        "content": content,
        "model": model
    }

    if thinking:
        message["thinking"] = thinking

    if usage:
        message["usage"] = usage

    conversation["messages"].append(message)
    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["title"] = title
    save_conversation(conversation)


def delete_conversation(conversation_id: str) -> bool:
    """
    Delete a conversation.

    Args:
        conversation_id: Conversation identifier

    Returns:
        True if deleted, False if conversation not found
    """
    filepath = get_conversation_path(conversation_id)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def add_debate_message(conversation_id: str, debate_result: Dict[str, Any]):
    """
    Add a debate message to a conversation.

    Args:
        conversation_id: Conversation identifier
        debate_result: Complete debate results with rounds and synthesis
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "assistant",
        "type": "debate",
        "debate": debate_result
    })

    save_conversation(conversation)


def get_conversation_context(conversation_id: str, limit: int = 3) -> Optional[str]:
    """
    Get summarized context from recent conversation history for follow-ups.

    Args:
        conversation_id: Conversation identifier
        limit: Maximum number of recent exchanges to include (default: 3)

    Returns:
        Summarized context string or None if no history exists
    """
    conversation = get_conversation(conversation_id)
    if conversation is None or not conversation["messages"]:
        return None

    messages = conversation["messages"]

    # Get the last N user-assistant pairs
    context_parts = []

    # Process messages in forward order, pairing user with following assistant
    i = 0
    while i < len(messages):
        # Look for user message followed by assistant message
        if (i < len(messages) - 1 and
            messages[i]["role"] == "user" and
            messages[i + 1]["role"] == "assistant"):

            user_msg = messages[i]["content"]
            stage3 = messages[i + 1].get("stage3", {})
            assistant_response = stage3.get("response", "")

            # Add this exchange
            context_parts.append({
                "question": user_msg,
                "answer": assistant_response
            })

            i += 2  # Skip both user and assistant messages
        else:
            i += 1

    # Keep only the last N exchanges
    context_parts = context_parts[-limit:]

    if not context_parts:
        return None

    # Format context as a readable summary
    context_lines = ["Previous conversation context:"]
    for i, exchange in enumerate(context_parts, 1):
        # Truncate long responses to keep context manageable
        question = exchange["question"][:300]
        answer = exchange["answer"][:500]

        context_lines.append(f"\nExchange {i}:")
        context_lines.append(f"Q: {question}")
        context_lines.append(f"A: {answer}...")

    return "\n".join(context_lines)


# ============ FOLDER MANAGEMENT ============

def get_folders_path() -> str:
    """Get the file path for folders storage."""
    return os.path.join(DATA_DIR, "folders.json")


def ensure_folders_file():
    """Ensure folders.json exists with default folders."""
    ensure_data_dir()
    folders_path = get_folders_path()

    if not os.path.exists(folders_path):
        default_folders = {
            "folders": [
                {
                    "id": "clients",
                    "name": "Clients",
                    "color": "#4a90e2",
                    "icon": "briefcase",
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "id": "internal",
                    "name": "Internal",
                    "color": "#9b59b6",
                    "icon": "users",
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "id": "archive",
                    "name": "Archive",
                    "color": "#95a5a6",
                    "icon": "archive",
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "id": "favorites",
                    "name": "Favorites",
                    "color": "#f39c12",
                    "icon": "star",
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
        }
        with open(folders_path, 'w', encoding='utf-8') as f:
            json.dump(default_folders, f, indent=2)


def list_folders() -> List[Dict[str, Any]]:
    """
    List all folders.

    Returns:
        List of folder dicts
    """
    ensure_folders_file()
    folders_path = get_folders_path()

    with open(folders_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("folders", [])


def create_folder(name: str, color: str = "#4a90e2", icon: str = "folder") -> Dict[str, Any]:
    """
    Create a new folder.

    Args:
        name: Folder name
        color: Hex color code
        icon: Icon name

    Returns:
        New folder dict
    """
    ensure_folders_file()
    folders_path = get_folders_path()

    with open(folders_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Generate ID from name
    folder_id = name.lower().replace(" ", "_")

    # Check if ID already exists
    existing_ids = {f["id"] for f in data["folders"]}
    if folder_id in existing_ids:
        # Append number to make unique
        counter = 1
        while f"{folder_id}_{counter}" in existing_ids:
            counter += 1
        folder_id = f"{folder_id}_{counter}"

    new_folder = {
        "id": folder_id,
        "name": name,
        "color": color,
        "icon": icon,
        "created_at": datetime.utcnow().isoformat()
    }

    data["folders"].append(new_folder)

    with open(folders_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return new_folder


def delete_folder(folder_id: str) -> bool:
    """
    Delete a folder and remove folder_id from all conversations.

    Args:
        folder_id: Folder identifier

    Returns:
        True if deleted, False if not found
    """
    ensure_folders_file()
    folders_path = get_folders_path()

    with open(folders_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Find and remove folder
    folders = data["folders"]
    initial_count = len(folders)
    data["folders"] = [f for f in folders if f["id"] != folder_id]

    if len(data["folders"]) == initial_count:
        return False

    # Save updated folders
    with open(folders_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    # Remove folder_id from all conversations
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json') and filename != 'folders.json':
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r', encoding='utf-8') as f:
                conversation = json.load(f)

            if conversation.get("folder_id") == folder_id:
                conversation["folder_id"] = None
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(conversation, f, indent=2)

    return True


def move_conversation_to_folder(conversation_id: str, folder_id: Optional[str]) -> bool:
    """
    Move a conversation to a folder.

    Args:
        conversation_id: Conversation identifier
        folder_id: Folder identifier (None to remove from folder)

    Returns:
        True if successful, False if conversation not found
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        return False

    conversation["folder_id"] = folder_id
    save_conversation(conversation)
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
    conversation = get_conversation(conversation_id)
    if conversation is None:
        return False

    if "tags" not in conversation:
        conversation["tags"] = []

    # Add tag if not already present
    if tag not in conversation["tags"]:
        conversation["tags"].append(tag)
        save_conversation(conversation)

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
    conversation = get_conversation(conversation_id)
    if conversation is None:
        return False

    if "tags" in conversation and tag in conversation["tags"]:
        conversation["tags"].remove(tag)
        save_conversation(conversation)

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
    conversation = get_conversation(conversation_id)
    if conversation is None:
        return False

    conversation["tags"] = tags
    save_conversation(conversation)
    return True


def list_all_tags() -> List[str]:
    """
    List all unique tags across all conversations.

    Returns:
        Sorted list of unique tags
    """
    ensure_data_dir()
    all_tags = set()

    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json') and filename != 'folders.json':
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                tags = data.get("tags", [])
                all_tags.update(tags)

    return sorted(list(all_tags))
