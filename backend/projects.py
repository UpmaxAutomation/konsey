"""Project management for LLM Council.

Projects provide scoped contexts for conversations, similar to Claude Projects.
Each project can have:
- Custom system prompts/instructions
- Knowledge base (uploaded files/context)
- Project-specific memory (facts, decisions, preferences)
- Custom council configuration
- Associated conversations
"""

import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Base directory for project data
PROJECTS_DIR = Path(__file__).parent / "data" / "projects"
PROJECTS_INDEX = PROJECTS_DIR / "index.json"


def _ensure_projects_dir():
    """Ensure the projects directory structure exists."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_INDEX.exists():
        PROJECTS_INDEX.write_text(json.dumps([], indent=2))


def create_project(
    name: str,
    description: str = "",
    system_prompt: str = "",
    council_models: Optional[List[str]] = None,
    chairman_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new project.

    Args:
        name: Project name
        description: Project description
        system_prompt: Custom instructions for all conversations in this project
        council_models: Optional custom council models for this project
        chairman_model: Optional custom chairman model for this project

    Returns:
        The created project dict
    """
    _ensure_projects_dir()

    project_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    project = {
        "id": project_id,
        "name": name,
        "description": description,
        "created_at": timestamp,
        "updated_at": timestamp,
        "system_prompt": system_prompt,
        "knowledge_base": [],
        "memory": {
            "facts": [],
            "decisions": [],
            "preferences": {}
        },
        "council_config": {
            "council_models": council_models,
            "chairman_model": chairman_model
        },
        "conversations": []
    }

    # Create project directory
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(exist_ok=True)

    # Create knowledge base directory
    kb_dir = project_dir / "knowledge_base"
    kb_dir.mkdir(exist_ok=True)

    # Save project file
    project_file = project_dir / "project.json"
    project_file.write_text(json.dumps(project, indent=2))

    # Add to index
    index = json.loads(PROJECTS_INDEX.read_text())
    index.append({
        "id": project_id,
        "name": name,
        "created_at": timestamp,
        "updated_at": timestamp
    })
    PROJECTS_INDEX.write_text(json.dumps(index, indent=2))

    return project


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a project by ID.

    Args:
        project_id: The project ID

    Returns:
        The project dict or None if not found
    """
    _ensure_projects_dir()

    project_file = PROJECTS_DIR / project_id / "project.json"
    if not project_file.exists():
        return None

    return json.loads(project_file.read_text())


def list_projects() -> List[Dict[str, Any]]:
    """
    List all projects (metadata only).

    Returns:
        List of project metadata dicts
    """
    _ensure_projects_dir()

    if not PROJECTS_INDEX.exists():
        return []

    return json.loads(PROJECTS_INDEX.read_text())


def update_project(project_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update a project.

    Args:
        project_id: The project ID
        updates: Dict of fields to update (name, description, system_prompt, council_config)

    Returns:
        The updated project dict or None if not found
    """
    _ensure_projects_dir()

    project = get_project(project_id)
    if project is None:
        return None

    # Update allowed fields
    allowed_fields = ["name", "description", "system_prompt", "council_config"]
    for field in allowed_fields:
        if field in updates:
            project[field] = updates[field]

    project["updated_at"] = datetime.utcnow().isoformat()

    # Save project file
    project_file = PROJECTS_DIR / project_id / "project.json"
    project_file.write_text(json.dumps(project, indent=2))

    # Update index
    index = json.loads(PROJECTS_INDEX.read_text())
    for item in index:
        if item["id"] == project_id:
            item["name"] = project["name"]
            item["updated_at"] = project["updated_at"]
            break
    PROJECTS_INDEX.write_text(json.dumps(index, indent=2))

    return project


def delete_project(project_id: str) -> bool:
    """
    Delete a project and all its data.

    Args:
        project_id: The project ID

    Returns:
        True if deleted, False if not found
    """
    _ensure_projects_dir()

    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return False

    # Remove from index
    index = json.loads(PROJECTS_INDEX.read_text())
    index = [p for p in index if p["id"] != project_id]
    PROJECTS_INDEX.write_text(json.dumps(index, indent=2))

    # Delete project directory and all contents
    import shutil
    shutil.rmtree(project_dir)

    return True


def add_to_knowledge_base(
    project_id: str,
    filename: str,
    content: str,
    file_type: str = "text"
) -> Optional[Dict[str, Any]]:
    """
    Add a file to the project's knowledge base.

    Args:
        project_id: The project ID
        filename: Original filename
        content: File content
        file_type: File type (text, markdown, code, etc.)

    Returns:
        The knowledge base entry dict or None if project not found
    """
    _ensure_projects_dir()

    project = get_project(project_id)
    if project is None:
        return None

    file_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    # Save file content
    kb_dir = PROJECTS_DIR / project_id / "knowledge_base"
    kb_file = kb_dir / f"{file_id}.txt"
    kb_file.write_text(content)

    # Create knowledge base entry
    kb_entry = {
        "id": file_id,
        "filename": filename,
        "file_type": file_type,
        "size": len(content),
        "added_at": timestamp
    }

    project["knowledge_base"].append(kb_entry)
    project["updated_at"] = timestamp

    # Save updated project
    project_file = PROJECTS_DIR / project_id / "project.json"
    project_file.write_text(json.dumps(project, indent=2))

    return kb_entry


def remove_from_knowledge_base(project_id: str, file_id: str) -> bool:
    """
    Remove a file from the project's knowledge base.

    Args:
        project_id: The project ID
        file_id: The file ID to remove

    Returns:
        True if removed, False if not found
    """
    _ensure_projects_dir()

    project = get_project(project_id)
    if project is None:
        return False

    # Find and remove from knowledge base list
    original_length = len(project["knowledge_base"])
    project["knowledge_base"] = [
        kb for kb in project["knowledge_base"] if kb["id"] != file_id
    ]

    if len(project["knowledge_base"]) == original_length:
        return False  # File not found

    # Delete the actual file
    kb_file = PROJECTS_DIR / project_id / "knowledge_base" / f"{file_id}.txt"
    if kb_file.exists():
        kb_file.unlink()

    project["updated_at"] = datetime.utcnow().isoformat()

    # Save updated project
    project_file = PROJECTS_DIR / project_id / "project.json"
    project_file.write_text(json.dumps(project, indent=2))

    return True


def get_knowledge_base_content(project_id: str, file_id: str) -> Optional[str]:
    """
    Get the content of a knowledge base file.

    Args:
        project_id: The project ID
        file_id: The file ID

    Returns:
        The file content or None if not found
    """
    _ensure_projects_dir()

    kb_file = PROJECTS_DIR / project_id / "knowledge_base" / f"{file_id}.txt"
    if not kb_file.exists():
        return None

    return kb_file.read_text()


def get_project_context(project_id: str) -> str:
    """
    Get the complete context for a project (system prompt + knowledge base + memory).

    Args:
        project_id: The project ID

    Returns:
        Formatted context string to prepend to queries
    """
    project = get_project(project_id)
    if project is None:
        return ""

    context_parts = []

    # Add system prompt if exists
    if project.get("system_prompt"):
        context_parts.append(f"**Project Instructions:**\n{project['system_prompt']}")

    # Add knowledge base if exists
    if project.get("knowledge_base"):
        kb_summary = f"**Project Knowledge Base ({len(project['knowledge_base'])} files):**"
        context_parts.append(kb_summary)

        # Include content from all knowledge base files
        for kb_entry in project["knowledge_base"]:
            content = get_knowledge_base_content(project_id, kb_entry["id"])
            if content:
                context_parts.append(
                    f"\n--- {kb_entry['filename']} ---\n{content}\n"
                )

    # Add project memory if exists
    memory_context = get_project_memory_context(project_id)
    if memory_context:
        context_parts.append(f"**Project Memory:**\n{memory_context}")

    return "\n\n".join(context_parts) if context_parts else ""


def add_conversation_to_project(project_id: str, conversation_id: str) -> bool:
    """
    Link a conversation to a project.

    Args:
        project_id: The project ID
        conversation_id: The conversation ID to add

    Returns:
        True if added, False if project not found
    """
    _ensure_projects_dir()

    project = get_project(project_id)
    if project is None:
        return False

    if conversation_id not in project["conversations"]:
        project["conversations"].append(conversation_id)
        project["updated_at"] = datetime.utcnow().isoformat()

        # Save updated project
        project_file = PROJECTS_DIR / project_id / "project.json"
        project_file.write_text(json.dumps(project, indent=2))

    return True


def remove_conversation_from_project(project_id: str, conversation_id: str) -> bool:
    """
    Remove a conversation from a project.

    Args:
        project_id: The project ID
        conversation_id: The conversation ID to remove

    Returns:
        True if removed, False if project or conversation not found
    """
    _ensure_projects_dir()

    project = get_project(project_id)
    if project is None:
        return False

    if conversation_id in project["conversations"]:
        project["conversations"].remove(conversation_id)
        project["updated_at"] = datetime.utcnow().isoformat()

        # Save updated project
        project_file = PROJECTS_DIR / project_id / "project.json"
        project_file.write_text(json.dumps(project, indent=2))
        return True

    return False


# ============ PROJECT MEMORY ============

def _ensure_project_memory(project: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure project has memory structure."""
    if "memory" not in project:
        project["memory"] = {
            "facts": [],
            "decisions": [],
            "preferences": {}
        }
    return project


def add_project_fact(project_id: str, fact: str, category: str = "general") -> bool:
    """
    Add a fact to the project's memory.

    Args:
        project_id: The project ID
        fact: The fact to remember
        category: Category for organization

    Returns:
        True if successful, False if project not found
    """
    project = get_project(project_id)
    if project is None:
        return False

    project = _ensure_project_memory(project)
    project["memory"]["facts"].append({
        "content": fact,
        "category": category,
        "timestamp": datetime.utcnow().isoformat()
    })
    # Keep only last 100 facts
    project["memory"]["facts"] = project["memory"]["facts"][-100:]
    project["updated_at"] = datetime.utcnow().isoformat()

    project_file = PROJECTS_DIR / project_id / "project.json"
    project_file.write_text(json.dumps(project, indent=2))
    return True


def add_project_decision(project_id: str, question: str, decision: str, reasoning: str = "") -> bool:
    """
    Add a council decision to the project's memory.

    Args:
        project_id: The project ID
        question: The original question
        decision: The council's decision/answer
        reasoning: Optional reasoning behind the decision

    Returns:
        True if successful, False if project not found
    """
    project = get_project(project_id)
    if project is None:
        return False

    project = _ensure_project_memory(project)
    project["memory"]["decisions"].append({
        "question": question[:500],
        "decision": decision[:2000],
        "reasoning": reasoning[:1000],
        "timestamp": datetime.utcnow().isoformat()
    })
    # Keep only last 50 decisions
    project["memory"]["decisions"] = project["memory"]["decisions"][-50:]
    project["updated_at"] = datetime.utcnow().isoformat()

    project_file = PROJECTS_DIR / project_id / "project.json"
    project_file.write_text(json.dumps(project, indent=2))
    return True


def set_project_preference(project_id: str, key: str, value: Any) -> bool:
    """
    Set a preference in the project's memory.

    Args:
        project_id: The project ID
        key: Preference key
        value: Preference value

    Returns:
        True if successful, False if project not found
    """
    project = get_project(project_id)
    if project is None:
        return False

    project = _ensure_project_memory(project)
    project["memory"]["preferences"][key] = {
        "value": value,
        "updated_at": datetime.utcnow().isoformat()
    }
    project["updated_at"] = datetime.utcnow().isoformat()

    project_file = PROJECTS_DIR / project_id / "project.json"
    project_file.write_text(json.dumps(project, indent=2))
    return True


def get_project_memory_context(project_id: str, limit: int = 10) -> str:
    """
    Get the memory context for a project.

    Args:
        project_id: The project ID
        limit: Maximum items to return

    Returns:
        Formatted string of project memories
    """
    project = get_project(project_id)
    if project is None:
        return ""

    project = _ensure_project_memory(project)
    memory = project["memory"]
    context_parts = []

    # Add recent facts
    if memory.get("facts"):
        recent_facts = memory["facts"][-limit:]
        if recent_facts:
            context_parts.append("**Project Facts:**")
            for fact in recent_facts:
                context_parts.append(f"- [{fact.get('category', 'general')}] {fact['content']}")

    # Add recent decisions
    if memory.get("decisions"):
        recent_decisions = memory["decisions"][-5:]
        if recent_decisions:
            context_parts.append("\n**Project Decisions:**")
            for dec in recent_decisions:
                context_parts.append(f"- Q: {dec['question'][:100]}...")
                context_parts.append(f"  A: {dec['decision'][:200]}...")

    # Add preferences
    if memory.get("preferences"):
        context_parts.append("\n**Project Preferences:**")
        for key, pref in memory["preferences"].items():
            context_parts.append(f"- {key}: {pref['value']}")

    return "\n".join(context_parts) if context_parts else ""


def clear_project_memory(project_id: str) -> bool:
    """
    Clear all memory for a project.

    Args:
        project_id: The project ID

    Returns:
        True if successful, False if project not found
    """
    project = get_project(project_id)
    if project is None:
        return False

    project["memory"] = {
        "facts": [],
        "decisions": [],
        "preferences": {}
    }
    project["updated_at"] = datetime.utcnow().isoformat()

    project_file = PROJECTS_DIR / project_id / "project.json"
    project_file.write_text(json.dumps(project, indent=2))
    return True


def get_project_memory_stats(project_id: str) -> Optional[Dict[str, Any]]:
    """
    Get memory statistics for a project.

    Args:
        project_id: The project ID

    Returns:
        Memory stats dict or None if project not found
    """
    project = get_project(project_id)
    if project is None:
        return None

    project = _ensure_project_memory(project)
    memory = project["memory"]

    return {
        "facts_count": len(memory.get("facts", [])),
        "decisions_count": len(memory.get("decisions", [])),
        "preferences_count": len(memory.get("preferences", {}))
    }
