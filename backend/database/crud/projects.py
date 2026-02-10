"""CRUD operations for projects."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Project, Conversation


# Project operations

async def get_by_id(db: AsyncSession, project_id: uuid.UUID) -> Optional[Project]:
    """Get project by ID (no user check - use for internal operations only)."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    return result.scalar_one_or_none()


async def get_by_id_for_user(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Project]:
    """Get project by ID with user ownership check."""
    result = await db.execute(
        select(Project)
        .where(
            Project.id == project_id,
            Project.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def get_with_conversations(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Project]:
    """Get project with conversations loaded."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.conversations))
        .where(
            Project.id == project_id,
            Project.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def list_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100
) -> List[Project]:
    """List all projects for a user."""
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    system_prompt: Optional[str] = None,
    council_config: Optional[dict] = None
) -> Project:
    """Create a new project."""
    project = Project(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        description=description,
        system_prompt=system_prompt,
        council_config=council_config,
        knowledge_base=[],
        memory={"facts": [], "decisions": [], "preferences": {}}
    )
    db.add(project)
    await db.flush()
    return project


async def update_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    **kwargs
) -> Optional[Project]:
    """Update project fields (with user ownership check)."""
    # Filter allowed fields
    allowed_fields = {"name", "description", "system_prompt", "council_config", "knowledge_base", "memory"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not update_data:
        return await get_by_id_for_user(db, project_id, user_id)

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.execute(
        update(Project)
        .where(
            Project.id == project_id,
            Project.user_id == user_id
        )
        .values(**update_data)
    )
    return await get_by_id_for_user(db, project_id, user_id)


async def delete_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID
) -> bool:
    """Delete project (with user ownership check). Conversations are unlinked (SET NULL)."""
    result = await db.execute(
        delete(Project)
        .where(
            Project.id == project_id,
            Project.user_id == user_id
        )
    )
    return result.rowcount > 0


# Knowledge base operations

async def add_to_knowledge_base(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    file_id: str,
    filename: str,
    content: str,
    file_type: str = "text"
) -> Optional[Project]:
    """Add a file to the project's knowledge base."""
    project = await get_by_id_for_user(db, project_id, user_id)
    if not project:
        return None

    kb = list(project.knowledge_base) if project.knowledge_base else []

    # Check if file already exists
    for item in kb:
        if item.get("id") == file_id:
            # Update existing
            item["content"] = content
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            break
    else:
        # Add new
        kb.append({
            "id": file_id,
            "filename": filename,
            "file_type": file_type,
            "content": content,
            "size": len(content),
            "added_at": datetime.now(timezone.utc).isoformat()
        })

    return await update_project(db, project_id, user_id, knowledge_base=kb)


async def remove_from_knowledge_base(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    file_id: str
) -> Optional[Project]:
    """Remove a file from the project's knowledge base."""
    project = await get_by_id_for_user(db, project_id, user_id)
    if not project:
        return None

    kb = list(project.knowledge_base) if project.knowledge_base else []
    kb = [item for item in kb if item.get("id") != file_id]

    return await update_project(db, project_id, user_id, knowledge_base=kb)


async def get_knowledge_base_file(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    file_id: str
) -> Optional[Dict[str, Any]]:
    """Get a specific file from the knowledge base."""
    project = await get_by_id_for_user(db, project_id, user_id)
    if not project or not project.knowledge_base:
        return None

    for item in project.knowledge_base:
        if item.get("id") == file_id:
            return item
    return None


# Memory operations

async def add_fact(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    fact: str,
    max_facts: int = 100
) -> Optional[Project]:
    """Add a fact to project memory."""
    project = await get_by_id_for_user(db, project_id, user_id)
    if not project:
        return None

    memory = dict(project.memory) if project.memory else {"facts": [], "decisions": [], "preferences": {}}
    facts = list(memory.get("facts", []))

    facts.append({
        "content": fact,
        "added_at": datetime.now(timezone.utc).isoformat()
    })

    # Limit facts
    if len(facts) > max_facts:
        facts = facts[-max_facts:]

    memory["facts"] = facts
    return await update_project(db, project_id, user_id, memory=memory)


async def add_decision(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    decision: str,
    context: Optional[str] = None,
    max_decisions: int = 50
) -> Optional[Project]:
    """Add a decision to project memory."""
    project = await get_by_id_for_user(db, project_id, user_id)
    if not project:
        return None

    memory = dict(project.memory) if project.memory else {"facts": [], "decisions": [], "preferences": {}}
    decisions = list(memory.get("decisions", []))

    decisions.append({
        "content": decision,
        "context": context,
        "added_at": datetime.now(timezone.utc).isoformat()
    })

    # Limit decisions
    if len(decisions) > max_decisions:
        decisions = decisions[-max_decisions:]

    memory["decisions"] = decisions
    return await update_project(db, project_id, user_id, memory=memory)


async def set_preference(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    key: str,
    value: Any
) -> Optional[Project]:
    """Set a preference in project memory."""
    project = await get_by_id_for_user(db, project_id, user_id)
    if not project:
        return None

    memory = dict(project.memory) if project.memory else {"facts": [], "decisions": [], "preferences": {}}
    preferences = dict(memory.get("preferences", {}))
    preferences[key] = value
    memory["preferences"] = preferences

    return await update_project(db, project_id, user_id, memory=memory)


async def clear_memory(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Project]:
    """Clear all project memory."""
    return await update_project(
        db, project_id, user_id,
        memory={"facts": [], "decisions": [], "preferences": {}}
    )


async def get_memory_stats(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Dict[str, int]]:
    """Get memory statistics."""
    project = await get_by_id_for_user(db, project_id, user_id)
    if not project:
        return None

    memory = project.memory or {}
    return {
        "facts": len(memory.get("facts", [])),
        "decisions": len(memory.get("decisions", [])),
        "preferences": len(memory.get("preferences", {}))
    }


# Context generation

def get_project_context(project: Project) -> str:
    """Generate context string from project for LLM injection.

    This formats the project's system prompt, knowledge base, and memory
    into a string suitable for prepending to user queries.
    """
    sections = []

    # System prompt
    if project.system_prompt:
        sections.append(f"**Project Instructions:**\n{project.system_prompt}")

    # Knowledge base
    if project.knowledge_base:
        kb_content = []
        for item in project.knowledge_base:
            filename = item.get("filename", "unknown")
            content = item.get("content", "")
            if content:
                kb_content.append(f"### {filename}\n{content}")

        if kb_content:
            sections.append(f"**Project Knowledge Base:**\n" + "\n\n".join(kb_content))

    # Memory
    memory = project.memory or {}
    memory_parts = []

    facts = memory.get("facts", [])
    if facts:
        fact_list = "\n".join(f"- {f.get('content', f)}" for f in facts[-10:])  # Last 10 facts
        memory_parts.append(f"**Facts:**\n{fact_list}")

    decisions = memory.get("decisions", [])
    if decisions:
        decision_list = "\n".join(f"- {d.get('content', d)}" for d in decisions[-5:])  # Last 5 decisions
        memory_parts.append(f"**Decisions:**\n{decision_list}")

    preferences = memory.get("preferences", {})
    if preferences:
        pref_list = "\n".join(f"- {k}: {v}" for k, v in preferences.items())
        memory_parts.append(f"**Preferences:**\n{pref_list}")

    if memory_parts:
        sections.append("**Project Memory:**\n" + "\n\n".join(memory_parts))

    if not sections:
        return ""

    return "\n\n---\n\n".join(sections)


# Conversation linkage

async def get_conversations(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 100
) -> List[Conversation]:
    """Get all conversations in a project."""
    # First verify project ownership
    project = await get_by_id_for_user(db, project_id, user_id)
    if not project:
        return []

    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.project_id == project_id,
            Conversation.user_id == user_id
        )
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_conversations(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID
) -> int:
    """Count conversations in a project."""
    project = await get_by_id_for_user(db, project_id, user_id)
    if not project:
        return 0

    result = await db.execute(
        select(func.count(Conversation.id))
        .where(
            Conversation.project_id == project_id,
            Conversation.user_id == user_id
        )
    )
    return result.scalar() or 0
