"""CRUD operations for user memory."""

import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserMemory


async def add_fact(
    db: AsyncSession,
    user_id: uuid.UUID,
    fact: str,
    category: str = "general"
) -> UserMemory:
    """Store a fact in user's memory."""
    memory = UserMemory(
        user_id=user_id,
        memory_type="fact",
        category=category,
        content=fact
    )
    db.add(memory)
    await db.flush()

    # Keep only last 100 facts per user
    await _prune_memories(db, user_id, "fact", max_count=100)

    return memory


async def add_decision(
    db: AsyncSession,
    user_id: uuid.UUID,
    question: str,
    decision: str,
    reasoning: str = ""
) -> UserMemory:
    """Store a council decision in user's memory."""
    content = json.dumps({
        "question": question[:500],
        "decision": decision[:2000],
        "reasoning": reasoning[:1000]
    })
    memory = UserMemory(
        user_id=user_id,
        memory_type="decision",
        category="council",
        content=content
    )
    db.add(memory)
    await db.flush()

    # Keep only last 50 decisions per user
    await _prune_memories(db, user_id, "decision", max_count=50)

    return memory


async def set_preference(
    db: AsyncSession,
    user_id: uuid.UUID,
    key: str,
    value: Any
) -> UserMemory:
    """Set a user preference (upsert by key)."""
    # Delete existing preference with same key
    await db.execute(
        delete(UserMemory)
        .where(UserMemory.user_id == user_id)
        .where(UserMemory.memory_type == "preference")
        .where(UserMemory.category == key)
    )

    content = json.dumps({"value": value})
    memory = UserMemory(
        user_id=user_id,
        memory_type="preference",
        category=key,
        content=content
    )
    db.add(memory)
    await db.flush()
    return memory


async def get_facts(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 10,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get user's facts."""
    query = (
        select(UserMemory)
        .where(UserMemory.user_id == user_id)
        .where(UserMemory.memory_type == "fact")
        .order_by(UserMemory.created_at.desc())
        .limit(limit)
    )
    if category:
        query = query.where(UserMemory.category == category)

    result = await db.execute(query)
    return [
        {
            "content": m.content,
            "category": m.category,
            "timestamp": m.created_at.isoformat()
        }
        for m in result.scalars().all()
    ]


async def get_decisions(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Get user's decisions."""
    result = await db.execute(
        select(UserMemory)
        .where(UserMemory.user_id == user_id)
        .where(UserMemory.memory_type == "decision")
        .order_by(UserMemory.created_at.desc())
        .limit(limit)
    )

    decisions = []
    for m in result.scalars().all():
        try:
            data = json.loads(m.content)
            data["timestamp"] = m.created_at.isoformat()
            decisions.append(data)
        except json.JSONDecodeError:
            continue
    return decisions


async def get_preferences(
    db: AsyncSession,
    user_id: uuid.UUID
) -> Dict[str, Any]:
    """Get all user preferences."""
    result = await db.execute(
        select(UserMemory)
        .where(UserMemory.user_id == user_id)
        .where(UserMemory.memory_type == "preference")
    )

    preferences = {}
    for m in result.scalars().all():
        try:
            data = json.loads(m.content)
            preferences[m.category] = {
                "value": data.get("value"),
                "updated_at": m.created_at.isoformat()
            }
        except json.JSONDecodeError:
            continue
    return preferences


async def get_memory_context(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 10
) -> str:
    """Get formatted memory context for a user."""
    context_parts = []

    # Get recent facts
    facts = await get_facts(db, user_id, limit=limit)
    if facts:
        context_parts.append("**Remembered Facts:**")
        for fact in facts:
            context_parts.append(f"- [{fact.get('category', 'general')}] {fact['content']}")

    # Get recent decisions
    decisions = await get_decisions(db, user_id, limit=5)
    if decisions:
        context_parts.append("\n**Past Decisions:**")
        for dec in decisions:
            context_parts.append(f"- Q: {dec.get('question', '')[:100]}...")
            context_parts.append(f"  A: {dec.get('decision', '')[:200]}...")

    # Get preferences
    preferences = await get_preferences(db, user_id)
    if preferences:
        context_parts.append("\n**User Preferences:**")
        for key, pref in preferences.items():
            context_parts.append(f"- {key}: {pref.get('value')}")

    return "\n".join(context_parts) if context_parts else ""


async def clear_memories(
    db: AsyncSession,
    user_id: uuid.UUID,
    memory_type: Optional[str] = None
) -> int:
    """Clear user's memories."""
    query = delete(UserMemory).where(UserMemory.user_id == user_id)
    if memory_type:
        query = query.where(UserMemory.memory_type == memory_type)

    result = await db.execute(query)
    return result.rowcount


async def _prune_memories(
    db: AsyncSession,
    user_id: uuid.UUID,
    memory_type: str,
    max_count: int
) -> int:
    """Remove oldest memories if over limit."""
    # Get IDs to keep
    result = await db.execute(
        select(UserMemory.id)
        .where(UserMemory.user_id == user_id)
        .where(UserMemory.memory_type == memory_type)
        .order_by(UserMemory.created_at.desc())
        .limit(max_count)
    )
    keep_ids = [row[0] for row in result.all()]

    if not keep_ids:
        return 0

    # Delete any not in keep list
    delete_result = await db.execute(
        delete(UserMemory)
        .where(UserMemory.user_id == user_id)
        .where(UserMemory.memory_type == memory_type)
        .where(UserMemory.id.notin_(keep_ids))
    )
    return delete_result.rowcount
