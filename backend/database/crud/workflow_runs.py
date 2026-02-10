"""CRUD operations for workflow execution run history."""

import uuid
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkflowRun

logger = logging.getLogger(__name__)


async def create_run(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    initial_input: Optional[str] = None,
) -> WorkflowRun:
    run = WorkflowRun(
        workflow_id=workflow_id,
        board_id=board_id,
        user_id=user_id,
        initial_input=initial_input,
        status="running",
    )
    db.add(run)
    await db.flush()
    return run


async def update_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    status: Optional[str] = None,
    completed_at: Optional[datetime] = None,
    duration_seconds: Optional[int] = None,
    step_count: Optional[int] = None,
    output_card_ids: Optional[list] = None,
    error: Optional[str] = None,
) -> Optional[WorkflowRun]:
    result = await db.execute(
        select(WorkflowRun).where(WorkflowRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        return None
    if status is not None:
        run.status = status
    if completed_at is not None:
        run.completed_at = completed_at
    if duration_seconds is not None:
        run.duration_seconds = duration_seconds
    if step_count is not None:
        run.step_count = step_count
    if output_card_ids is not None:
        run.output_card_ids = output_card_ids
    if error is not None:
        run.error = error
    await db.flush()
    return run


async def list_runs(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    limit: int = 20,
) -> list[WorkflowRun]:
    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == workflow_id)
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_run(
    db: AsyncSession,
    run_id: uuid.UUID,
) -> Optional[WorkflowRun]:
    result = await db.execute(
        select(WorkflowRun).where(WorkflowRun.id == run_id)
    )
    return result.scalar_one_or_none()
