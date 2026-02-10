"""CRUD operations for agent runs."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AgentRun


async def get_agent_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    board_id: uuid.UUID
) -> Optional[AgentRun]:
    """Get an agent run by ID within a board."""
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.board_id == board_id
        )
    )
    return result.scalar_one_or_none()


async def get_active_run(
    db: AsyncSession,
    board_id: uuid.UUID
) -> Optional[AgentRun]:
    """Get a running or paused agent run for a board.

    Used to enforce a single active run per board (409 conflict check).
    """
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.board_id == board_id,
            AgentRun.status.in_(["running", "paused"])
        )
    )
    return result.scalar_one_or_none()


async def list_runs(
    db: AsyncSession,
    board_id: uuid.UUID,
    limit: int = 20
) -> List[AgentRun]:
    """List agent runs for a board, ordered by most recent first."""
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.board_id == board_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_run(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    goal: str,
    model: str,
    max_iterations: int = 20
) -> AgentRun:
    """Create a new agent run on a board."""
    run = AgentRun(
        id=uuid.uuid4(),
        board_id=board_id,
        user_id=user_id,
        goal=goal,
        model=model,
        status="running",
        iteration_count=0,
        max_iterations=max_iterations,
        thoughts_log=[],
        created_card_ids=[],
    )
    db.add(run)
    await db.flush()
    return run


async def update_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    board_id: uuid.UUID,
    **kwargs: Any
) -> Optional[AgentRun]:
    """Update agent run fields.

    Allowed fields: status, iteration_count, thoughts_log,
    created_card_ids, error.
    """
    allowed_fields = {
        "status", "iteration_count", "thoughts_log",
        "created_card_ids", "error"
    }
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        return await get_agent_run(db, run_id, board_id)

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.execute(
        update(AgentRun)
        .where(AgentRun.id == run_id, AgentRun.board_id == board_id)
        .values(**update_data)
    )
    return await get_agent_run(db, run_id, board_id)


async def append_thought(
    db: AsyncSession,
    run_id: uuid.UUID,
    board_id: uuid.UUID,
    thought: Dict[str, Any]
) -> Optional[AgentRun]:
    """Append a thought dict to the agent run's thoughts_log.

    Fetches the current list, appends the new thought, then persists.
    """
    run = await get_agent_run(db, run_id, board_id)
    if not run:
        return None

    current_thoughts = list(run.thoughts_log) if run.thoughts_log else []
    current_thoughts.append(thought)

    return await update_run(db, run_id, board_id, thoughts_log=current_thoughts)


async def append_created_card(
    db: AsyncSession,
    run_id: uuid.UUID,
    board_id: uuid.UUID,
    card_id: str
) -> Optional[AgentRun]:
    """Append a card ID to the agent run's created_card_ids.

    Fetches the current list, appends the new card ID, then persists.
    """
    run = await get_agent_run(db, run_id, board_id)
    if not run:
        return None

    current_card_ids = list(run.created_card_ids) if run.created_card_ids else []
    current_card_ids.append(card_id)

    return await update_run(db, run_id, board_id, created_card_ids=current_card_ids)
