"""Workflow execution engine for multi-step AI pipelines on canvas.

Executes workflow steps sequentially as an async generator, yielding SSE events
for real-time progress updates. Supports council_query, ai_transform, combine,
and human_review step types.
"""

import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-4o"

# Card layout constants
STEP_VERTICAL_SPACING = 300
CARD_HORIZONTAL_SPACING = 280
DEFAULT_CARD_WIDTH = 280.0
DEFAULT_CARD_HEIGHT = 200.0
SYNTHESIS_CARD_HEIGHT = 250.0
CENTERED_X = 400.0
BASE_Y_DEFAULT = 100.0
BASE_Y_GAP = 400.0


def _serialize_card(card) -> Dict[str, Any]:
    """Serialize a Card ORM object into a JSON-safe dictionary."""
    return {
        "id": str(card.id),
        "board_id": str(card.board_id),
        "card_type": card.card_type,
        "title": card.title,
        "content": card.content,
        "position_x": card.position_x,
        "position_y": card.position_y,
        "width": card.width,
        "height": card.height,
        "color": card.color,
        "extra": card.extra or {},
    }


def _compute_base_y(existing_cards: List) -> float:
    """Compute the starting Y position below all existing cards."""
    if not existing_cards:
        return BASE_Y_DEFAULT
    max_y = max(c.position_y for c in existing_cards)
    return max_y + BASE_Y_GAP


def _resolve_input_text(
    step_index: int,
    initial_input: str,
    context_card_contents: List[str],
    previous_output: Optional[str],
) -> str:
    """Determine the input text for a workflow step.

    First step uses initial_input or context card contents.
    Subsequent steps use the output from the previous step.
    """
    if step_index == 0:
        if initial_input:
            return initial_input
        if context_card_contents:
            return "\n\n---\n\n".join(context_card_contents)
        return ""
    return previous_output or ""


def _build_prompt(template: Optional[str], input_text: str) -> str:
    """Replace {{input}} placeholder in template with actual input text."""
    if not template:
        return input_text
    return template.replace("{{input}}", input_text)


async def _gather_context_card_contents(
    db,
    board_id: uuid.UUID,
    card_ids: Optional[List],
) -> List[str]:
    """Fetch content from specified context cards."""
    from ..database.crud import boards as boards_crud

    if not card_ids:
        return []
    contents = []
    for cid in card_ids:
        try:
            card_uuid = uuid.UUID(str(cid))
        except (ValueError, TypeError):
            logger.warning("Invalid context card ID: %s", cid)
            continue
        card = await boards_crud.get_card_by_id(db, card_uuid, board_id)
        if card and card.content:
            contents.append(card.content)
        else:
            logger.warning(
                "Context card %s not found or empty on board %s", cid, board_id
            )
    return contents


async def _execute_council_query(
    step,
    input_text: str,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    db,
    base_y: float,
    step_offset_y: float,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute a council_query step: run the full 3-stage council deliberation.

    Creates a query card, per-model response cards, and a synthesis card.
    Yields step_progress and step_card_created events.

    Returns the synthesis text as the last yielded dict with key 'output_text'.
    """
    from ..council.orchestration import run_full_council
    from ..database.crud import boards as boards_crud

    prompt = _build_prompt(step.prompt_template, input_text)
    step_y = base_y + step_offset_y

    # Create the query card (centered)
    query_card = await boards_crud.create_card(
        db,
        board_id,
        card_type="query",
        title=f"Query: {step.name}",
        content=prompt[:2000],
        position_x=CENTERED_X,
        position_y=step_y,
        width=DEFAULT_CARD_WIDTH,
        height=DEFAULT_CARD_HEIGHT,
        color="#e3f2fd",
        extra={"workflow_step": step.name, "step_type": "council_query"},
    )
    yield {"event": "step_card_created", "card": _serialize_card(query_card)}

    yield {"event": "step_progress", "message": "Running council deliberation..."}

    # Run the full council (non-streaming)
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        prompt,
        user_id=user_id,
        db=db,
    )

    # Create response cards (one per model), fanned out horizontally
    response_cards = []
    num_models = len(stage1_results)
    if num_models > 0:
        total_width = (num_models - 1) * CARD_HORIZONTAL_SPACING
        start_x = CENTERED_X - total_width / 2
    else:
        start_x = CENTERED_X

    response_y = step_y + STEP_VERTICAL_SPACING * 0.4

    for idx, result in enumerate(stage1_results):
        model_name = result.get("model", f"model_{idx}")
        response_text = result.get("response", "")
        card_x = start_x + idx * CARD_HORIZONTAL_SPACING

        response_card = await boards_crud.create_card(
            db,
            board_id,
            card_type="council_response",
            title=f"Response: {model_name}",
            content=response_text[:5000],
            position_x=card_x,
            position_y=response_y,
            width=DEFAULT_CARD_WIDTH,
            height=DEFAULT_CARD_HEIGHT,
            color="#fff3e0",
            extra={
                "model": model_name,
                "workflow_step": step.name,
                "step_type": "council_query",
            },
        )
        response_cards.append(response_card)

        # Edge: query -> response (derived_from)
        await boards_crud.create_edge(
            db, board_id, query_card.id, response_card.id,
            edge_type="derived_from", label="queried",
        )

        yield {"event": "step_card_created", "card": _serialize_card(response_card)}

    # Create synthesis card (centered below responses)
    synthesis_text = stage3_result.get("response", "") if stage3_result else ""
    synthesis_model = stage3_result.get("model", "chairman") if stage3_result else "unknown"
    synthesis_y = response_y + STEP_VERTICAL_SPACING * 0.5

    synthesis_card = await boards_crud.create_card(
        db,
        board_id,
        card_type="council_synthesis",
        title=f"Synthesis: {step.name}",
        content=synthesis_text[:5000],
        position_x=CENTERED_X,
        position_y=synthesis_y,
        width=DEFAULT_CARD_WIDTH,
        height=SYNTHESIS_CARD_HEIGHT,
        color="#e8f5e9",
        extra={
            "model": synthesis_model,
            "workflow_step": step.name,
            "step_type": "council_query",
            "aggregate_rankings": metadata.get("aggregate_rankings", []),
        },
    )

    # Edges: each response -> synthesis (synthesizes)
    for rc in response_cards:
        await boards_crud.create_edge(
            db, board_id, rc.id, synthesis_card.id,
            edge_type="synthesizes", label="synthesizes",
        )

    yield {"event": "step_card_created", "card": _serialize_card(synthesis_card)}

    # Return all output card IDs and the output text
    all_output_ids = [str(query_card.id)] + [str(rc.id) for rc in response_cards] + [str(synthesis_card.id)]
    yield {
        "event": "done",
        "output_text": synthesis_text,
        "output_card_ids": all_output_ids,
    }


async def _execute_ai_transform(
    step,
    input_text: str,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    db,
    base_y: float,
    step_offset_y: float,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute an ai_transform step: single model call with prompt template.

    Creates one output card with the result.
    """
    from ..llm.client import query_model
    from ..database.crud import boards as boards_crud

    prompt = _build_prompt(step.prompt_template, input_text)
    model = (step.config or {}).get("model", DEFAULT_MODEL)

    yield {"event": "step_progress", "message": f"Running AI transform with {model}..."}

    messages = [{"role": "user", "content": prompt}]
    result = await query_model(model, messages, user_id=user_id, db=db)

    if result is None:
        raise RuntimeError(
            f"AI transform failed: model {model} returned no response. "
            "Check API keys in Settings."
        )

    output_text = result.get("content", "")

    step_y = base_y + step_offset_y
    output_card = await boards_crud.create_card(
        db,
        board_id,
        card_type="note",
        title=f"Transform: {step.name}",
        content=output_text[:5000],
        position_x=CENTERED_X,
        position_y=step_y,
        width=DEFAULT_CARD_WIDTH,
        height=DEFAULT_CARD_HEIGHT,
        color="#f3e5f5",
        extra={
            "model": model,
            "workflow_step": step.name,
            "step_type": "ai_transform",
            "workflow_output": True,
            "usage": result.get("usage", {}),
        },
    )
    yield {"event": "step_card_created", "card": _serialize_card(output_card)}
    yield {
        "event": "done",
        "output_text": output_text,
        "output_card_ids": [str(output_card.id)],
    }


async def _execute_combine(
    step,
    input_text: str,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    db,
    base_y: float,
    step_offset_y: float,
    all_previous_output_card_ids: List[str],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute a combine step: gather all input card contents and merge with LLM.

    Creates one output card with the combined result.
    """
    from ..llm.client import query_model
    from ..database.crud import boards as boards_crud

    yield {"event": "step_progress", "message": "Gathering inputs for combine step..."}

    # Gather content from all previous output cards
    card_contents = []
    for cid_str in all_previous_output_card_ids:
        try:
            cid = uuid.UUID(cid_str)
        except (ValueError, TypeError):
            continue
        card = await boards_crud.get_card_by_id(db, cid, board_id)
        if card and card.content:
            card_contents.append(card.content)

    # Also include the chained input_text as a fallback
    if not card_contents and input_text:
        card_contents = [input_text]

    combined_input = "\n\n---\n\n".join(card_contents)
    prompt = _build_prompt(step.prompt_template, combined_input)
    model = (step.config or {}).get("model", DEFAULT_MODEL)

    yield {"event": "step_progress", "message": f"Combining with {model}..."}

    messages = [{"role": "user", "content": prompt}]
    result = await query_model(model, messages, user_id=user_id, db=db)

    if result is None:
        raise RuntimeError(
            f"Combine step failed: model {model} returned no response. "
            "Check API keys in Settings."
        )

    output_text = result.get("content", "")

    step_y = base_y + step_offset_y
    output_card = await boards_crud.create_card(
        db,
        board_id,
        card_type="note",
        title=f"Combined: {step.name}",
        content=output_text[:5000],
        position_x=CENTERED_X,
        position_y=step_y,
        width=DEFAULT_CARD_WIDTH,
        height=DEFAULT_CARD_HEIGHT,
        color="#e0f7fa",
        extra={
            "model": model,
            "workflow_step": step.name,
            "step_type": "combine",
            "workflow_output": True,
            "usage": result.get("usage", {}),
        },
    )
    yield {"event": "step_card_created", "card": _serialize_card(output_card)}
    yield {
        "event": "done",
        "output_text": output_text,
        "output_card_ids": [str(output_card.id)],
    }


async def execute_workflow(
    workflow_id: uuid.UUID,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    initial_input: str = "",
    context_card_ids: Optional[List] = None,
    db=None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute a workflow's steps sequentially, yielding SSE events.

    This is the primary entry point for workflow execution. It loads the
    workflow from the database, iterates through its steps starting from
    the current_step_index, and executes each one according to its type.

    Args:
        workflow_id: UUID of the workflow to execute.
        board_id: UUID of the board the workflow belongs to.
        user_id: UUID of the user running the workflow.
        initial_input: User-provided input text for the first step.
        context_card_ids: Optional list of card IDs to gather context from.
        db: AsyncSession for database operations.

    Yields:
        Dicts representing SSE events (workflow_start, step_start,
        step_progress, step_card_created, step_complete,
        step_waiting_review, workflow_complete, workflow_error).
    """
    from ..database.crud import boards as boards_crud
    from ..database.crud import workflows as workflows_crud

    # ------------------------------------------------------------------
    # 1. Load workflow with steps
    # ------------------------------------------------------------------
    workflow = await workflows_crud.get_workflow_by_id(db, workflow_id, board_id)
    if workflow is None:
        yield {
            "type": "workflow_error",
            "workflow_id": str(workflow_id),
            "error": "Workflow not found",
        }
        return

    steps = sorted(workflow.steps, key=lambda s: s.step_index)
    if not steps:
        yield {
            "type": "workflow_error",
            "workflow_id": str(workflow_id),
            "error": "Workflow has no steps",
        }
        return

    # ------------------------------------------------------------------
    # 2. Update workflow status to 'running'
    # ------------------------------------------------------------------
    await workflows_crud.update_workflow(
        db, workflow_id, board_id, status="running"
    )
    await db.commit()

    logger.info(
        "Starting workflow %s on board %s (%d steps)",
        workflow_id, board_id, len(steps),
    )

    # 3. Yield workflow_start
    yield {"type": "workflow_start", "workflow_id": str(workflow_id)}

    # ------------------------------------------------------------------
    # 4. Compute layout base_y from existing cards
    # ------------------------------------------------------------------
    existing_cards = await boards_crud.list_cards(db, board_id)
    base_y = _compute_base_y(existing_cards)

    # ------------------------------------------------------------------
    # 5. Gather initial context card contents (for first step)
    # ------------------------------------------------------------------
    context_card_contents = await _gather_context_card_contents(
        db, board_id, context_card_ids
    )

    # ------------------------------------------------------------------
    # 6. Step execution loop
    # ------------------------------------------------------------------
    previous_output: Optional[str] = None
    all_output_card_ids: List[str] = []
    start_index = workflow.current_step_index or 0

    for i, step in enumerate(steps):
        if step.step_index < start_index:
            continue

        step_offset_y = i * STEP_VERTICAL_SPACING

        try:
            # Update step status to 'running'
            await workflows_crud.update_step(
                db, step.id, workflow_id, status="running"
            )
            await db.commit()

            # Yield step_start
            yield {
                "type": "step_start",
                "step_index": i,
                "step_name": step.name,
                "step_type": step.step_type,
            }

            # Determine input text for this step
            input_text = _resolve_input_text(
                step_index=i,
                initial_input=initial_input,
                context_card_contents=context_card_contents,
                previous_output=previous_output,
            )

            # ----------------------------------------------------------
            # Dispatch by step type
            # ----------------------------------------------------------
            step_output_text = ""
            step_output_card_ids: List[str] = []

            if step.step_type == "council_query":
                async for event in _execute_council_query(
                    step, input_text, board_id, user_id, db,
                    base_y, step_offset_y,
                ):
                    if event.get("event") == "step_card_created":
                        yield {
                            "type": "step_card_created",
                            "step_index": i,
                            "card": event["card"],
                        }
                    elif event.get("event") == "step_progress":
                        yield {
                            "type": "step_progress",
                            "step_index": i,
                            "message": event["message"],
                        }
                    elif event.get("event") == "done":
                        step_output_text = event["output_text"]
                        step_output_card_ids = event["output_card_ids"]

            elif step.step_type == "ai_transform":
                async for event in _execute_ai_transform(
                    step, input_text, board_id, user_id, db,
                    base_y, step_offset_y,
                ):
                    if event.get("event") == "step_card_created":
                        yield {
                            "type": "step_card_created",
                            "step_index": i,
                            "card": event["card"],
                        }
                    elif event.get("event") == "step_progress":
                        yield {
                            "type": "step_progress",
                            "step_index": i,
                            "message": event["message"],
                        }
                    elif event.get("event") == "done":
                        step_output_text = event["output_text"]
                        step_output_card_ids = event["output_card_ids"]

            elif step.step_type == "combine":
                async for event in _execute_combine(
                    step, input_text, board_id, user_id, db,
                    base_y, step_offset_y, all_output_card_ids,
                ):
                    if event.get("event") == "step_card_created":
                        yield {
                            "type": "step_card_created",
                            "step_index": i,
                            "card": event["card"],
                        }
                    elif event.get("event") == "step_progress":
                        yield {
                            "type": "step_progress",
                            "step_index": i,
                            "message": event["message"],
                        }
                    elif event.get("event") == "done":
                        step_output_text = event["output_text"]
                        step_output_card_ids = event["output_card_ids"]

            elif step.step_type == "human_review":
                await workflows_crud.update_step(
                    db, step.id, workflow_id, status="waiting_review"
                )
                await workflows_crud.update_workflow(
                    db, workflow_id, board_id,
                    status="paused",
                    current_step_index=step.step_index,
                )
                await db.commit()

                yield {
                    "type": "step_waiting_review",
                    "step_index": i,
                    "step_name": step.name,
                }
                logger.info(
                    "Workflow %s paused at step %d (%s) for human review",
                    workflow_id, i, step.name,
                )
                return

            else:
                raise ValueError(f"Unknown step type: {step.step_type}")

            # ----------------------------------------------------------
            # Post-step bookkeeping
            # ----------------------------------------------------------
            previous_output = step_output_text
            all_output_card_ids.extend(step_output_card_ids)

            # Update step with output card IDs and mark completed
            await workflows_crud.update_step(
                db, step.id, workflow_id,
                status="completed",
                output_card_ids=step_output_card_ids,
            )
            await workflows_crud.update_workflow(
                db, workflow_id, board_id,
                current_step_index=step.step_index + 1,
            )
            await db.commit()

            yield {
                "type": "step_complete",
                "step_index": i,
                "output_text": step_output_text[:500],
            }

            logger.info(
                "Workflow %s step %d (%s) completed, %d output cards",
                workflow_id, i, step.name, len(step_output_card_ids),
            )

        except Exception as exc:
            logger.exception(
                "Workflow %s failed at step %d (%s): %s",
                workflow_id, i, step.name, exc,
            )

            # Mark step and workflow as failed
            await workflows_crud.update_step(
                db, step.id, workflow_id,
                status="failed",
                error=str(exc)[:2000],
            )
            await workflows_crud.update_workflow(
                db, workflow_id, board_id,
                status="failed",
                error=f"Step {i} ({step.name}) failed: {exc}"[:2000],
            )
            await db.commit()

            yield {
                "type": "workflow_error",
                "workflow_id": str(workflow_id),
                "error": str(exc),
            }
            return

    # ------------------------------------------------------------------
    # 7. All steps completed successfully
    # ------------------------------------------------------------------
    await workflows_crud.update_workflow(
        db, workflow_id, board_id, status="completed"
    )
    await db.commit()

    yield {"type": "workflow_complete", "workflow_id": str(workflow_id)}

    logger.info("Workflow %s completed successfully", workflow_id)


async def approve_workflow_step(
    workflow_id: uuid.UUID,
    board_id: uuid.UUID,
    db,
) -> Optional[Any]:
    """Approve the currently waiting human_review step and advance the workflow.

    Finds the step with status='waiting_review', marks it 'completed',
    and advances the workflow's current_step_index so the next call to
    execute_workflow resumes from the following step.

    Args:
        workflow_id: UUID of the workflow.
        board_id: UUID of the board.
        db: AsyncSession for database operations.

    Returns:
        The updated Workflow object, or None if the workflow or step
        was not found in the expected state.
    """
    from ..database.crud import workflows as workflows_crud

    workflow = await workflows_crud.get_workflow_by_id(db, workflow_id, board_id)
    if workflow is None:
        logger.warning("approve_workflow_step: workflow %s not found", workflow_id)
        return None

    if workflow.status != "paused":
        logger.warning(
            "approve_workflow_step: workflow %s status is '%s', expected 'paused'",
            workflow_id, workflow.status,
        )
        return None

    # Find the step that is waiting for review
    waiting_step = None
    for step in sorted(workflow.steps, key=lambda s: s.step_index):
        if step.status == "waiting_review":
            waiting_step = step
            break

    if waiting_step is None:
        logger.warning(
            "approve_workflow_step: no step with status 'waiting_review' "
            "in workflow %s",
            workflow_id,
        )
        return None

    # Mark the step as completed
    await workflows_crud.update_step(
        db, waiting_step.id, workflow_id, status="completed"
    )

    # Advance the workflow to the next step and set status back to draft
    # so execute_workflow can resume it
    next_index = waiting_step.step_index + 1
    updated_workflow = await workflows_crud.update_workflow(
        db, workflow_id, board_id,
        status="draft",
        current_step_index=next_index,
    )
    await db.commit()

    logger.info(
        "Workflow %s step %d (%s) approved, advancing to step %d",
        workflow_id, waiting_step.step_index, waiting_step.name, next_index,
    )

    return updated_workflow
