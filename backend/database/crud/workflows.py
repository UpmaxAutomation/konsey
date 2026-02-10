"""CRUD operations for workflows and workflow steps."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Workflow, WorkflowStep


# ──────────────────────────────────────────────
# Workflow operations
# ──────────────────────────────────────────────

async def get_workflow_by_id(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    board_id: uuid.UUID
) -> Optional[Workflow]:
    """Get workflow by ID within a board, with steps eager-loaded."""
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(
            Workflow.id == workflow_id,
            Workflow.board_id == board_id
        )
    )
    return result.scalar_one_or_none()


async def list_workflows(
    db: AsyncSession,
    board_id: uuid.UUID
) -> List[Workflow]:
    """List all workflows for a board, ordered by updated_at desc."""
    result = await db.execute(
        select(Workflow)
        .where(Workflow.board_id == board_id)
        .order_by(Workflow.updated_at.desc())
    )
    return list(result.scalars().all())


async def create_workflow(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    template_id: Optional[str] = None,
    config: Optional[dict] = None,
    steps: Optional[List[Dict[str, Any]]] = None
) -> Workflow:
    """Create a new workflow with optional steps.

    Args:
        db: Database session.
        board_id: The board this workflow belongs to.
        user_id: The owner of the workflow.
        name: Workflow name.
        description: Optional description.
        template_id: Optional template identifier.
        config: Optional JSON configuration.
        steps: Optional list of step dicts with keys:
            step_index, step_type, name, prompt_template, config.
    """
    workflow_id = uuid.uuid4()
    workflow = Workflow(
        id=workflow_id,
        board_id=board_id,
        user_id=user_id,
        name=name,
        description=description,
        template_id=template_id,
        config=config or {},
    )
    db.add(workflow)
    await db.flush()

    if steps:
        for step_data in steps:
            step = WorkflowStep(
                id=uuid.uuid4(),
                workflow_id=workflow_id,
                step_index=step_data.get("step_index", 0),
                step_type=step_data.get("step_type", "council_query"),
                name=step_data.get("name", ""),
                prompt_template=step_data.get("prompt_template"),
                config=step_data.get("config") or {},
            )
            db.add(step)
        await db.flush()

    return await get_workflow_by_id(db, workflow_id, board_id)


async def update_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    board_id: uuid.UUID,
    **kwargs
) -> Optional[Workflow]:
    """Update workflow fields.

    Allowed fields: name, description, status, config,
    current_step_index, error.
    """
    allowed_fields = {
        "name", "description", "status", "config",
        "current_step_index", "error"
    }
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        return await get_workflow_by_id(db, workflow_id, board_id)

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.execute(
        update(Workflow)
        .where(Workflow.id == workflow_id, Workflow.board_id == board_id)
        .values(**update_data)
    )
    return await get_workflow_by_id(db, workflow_id, board_id)


async def delete_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    board_id: uuid.UUID
) -> bool:
    """Delete a workflow (cascades to steps)."""
    result = await db.execute(
        delete(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.board_id == board_id
        )
    )
    return result.rowcount > 0


# ──────────────────────────────────────────────
# WorkflowStep operations
# ──────────────────────────────────────────────

async def get_step(
    db: AsyncSession,
    step_id: uuid.UUID,
    workflow_id: uuid.UUID
) -> Optional[WorkflowStep]:
    """Get a single workflow step by ID within a workflow."""
    result = await db.execute(
        select(WorkflowStep).where(
            WorkflowStep.id == step_id,
            WorkflowStep.workflow_id == workflow_id
        )
    )
    return result.scalar_one_or_none()


async def update_step(
    db: AsyncSession,
    step_id: uuid.UUID,
    workflow_id: uuid.UUID,
    **kwargs
) -> Optional[WorkflowStep]:
    """Update workflow step fields.

    Allowed fields: status, input_card_ids, output_card_ids, error, config.
    """
    allowed_fields = {
        "status", "input_card_ids", "output_card_ids", "error", "config"
    }
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        return await get_step(db, step_id, workflow_id)

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.execute(
        update(WorkflowStep)
        .where(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id)
        .values(**update_data)
    )
    return await get_step(db, step_id, workflow_id)


async def add_step_output_card(
    db: AsyncSession,
    step_id: uuid.UUID,
    workflow_id: uuid.UUID,
    card_id: uuid.UUID
) -> Optional[WorkflowStep]:
    """Append a card_id to a step's output_card_ids list."""
    step = await get_step(db, step_id, workflow_id)
    if not step:
        return None

    current_ids = list(step.output_card_ids or [])
    card_id_str = str(card_id)
    if card_id_str not in current_ids:
        current_ids.append(card_id_str)

    await db.execute(
        update(WorkflowStep)
        .where(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id)
        .values(
            output_card_ids=current_ids,
            updated_at=datetime.now(timezone.utc)
        )
    )
    return await get_step(db, step_id, workflow_id)
