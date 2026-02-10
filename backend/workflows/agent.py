"""Autonomous canvas agent planning loop.

Implements an LLM-driven agent that iteratively uses tools to populate a
canvas board toward a stated goal.  The ``run_canvas_agent`` async generator
yields Server-Sent Event dicts so the caller can stream progress to the
frontend in real time.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict

from ..llm.client import query_model
from ..database.crud import boards as boards_crud
from ..database.crud import agent_runs as agent_runs_crud
from .agent_tools import AGENT_TOOLS, execute_tool

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """You are an AI agent that populates a visual canvas board. Given a goal, you use tools to create cards, run council deliberations, search existing content, and organize information.

Available tools:
{tools_json}

Current board state:
{board_state}

IMPORTANT:
- Think step by step before each action
- Use create_card to add information to the board
- Use run_council for complex questions that benefit from multiple perspectives
- Use create_edge to connect related cards
- Use create_section to organize cards visually
- Call "done" when you've accomplished the goal
- Respond in JSON format: {{"thought": "your reasoning", "tool": "tool_name", "parameters": {{...}}}}
"""


async def get_board_state_summary(db, board_id: str, max_cards: int = 50) -> str:
    """Build a compact text summary of the current board state.

    Args:
        db: Async database session.
        board_id: UUID string of the board.
        max_cards: Maximum number of cards to include in the summary.

    Returns:
        A human-readable string describing the cards on the board.
    """
    import uuid as _uuid

    bid = _uuid.UUID(board_id) if isinstance(board_id, str) else board_id
    cards = await boards_crud.list_cards(db, bid)
    cards = cards[:max_cards]
    if not cards:
        return "Board is empty."
    lines = []
    for c in cards:
        content_preview = (c.content or "")[:100]
        lines.append(f"- [{c.card_type}] {c.title or 'Untitled'}: {content_preview}")
    return f"{len(cards)} cards on board:\n" + "\n".join(lines)


async def run_canvas_agent(
    board_id: str,
    goal: str,
    model: str,
    max_iterations: int,
    user_id: str,
    db,
    run_id=None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Run the autonomous canvas agent loop.

    This is an async generator that yields SSE event dicts describing the
    agent's progress.  Each event has a ``type`` key:

    * ``agent_start`` -- emitted once at the beginning with the run ID and goal.
    * ``agent_iteration`` -- emitted per iteration with the agent's thought,
      chosen tool, and parameters.
    * ``agent_tool_result`` -- the result dict returned by the tool.
    * ``agent_card_created`` -- emitted when a ``create_card`` tool succeeds,
      carrying the serialised card data.
    * ``agent_paused`` -- the run was externally paused.
    * ``agent_complete`` -- the agent finished (by calling ``done``, being
      cancelled, or reaching max iterations).
    * ``agent_error`` -- an unrecoverable error occurred.

    Args:
        board_id: UUID string of the target board.
        goal: Natural-language description of what the agent should accomplish.
        model: OpenRouter model identifier to drive the agent.
        max_iterations: Upper bound on planning iterations.
        user_id: UUID string of the user who launched the agent.
        db: Async database session.
    """
    import uuid as _uuid

    bid = _uuid.UUID(board_id) if isinstance(board_id, str) else board_id
    uid = _uuid.UUID(user_id) if isinstance(user_id, str) else user_id

    # Reuse existing run (resume) or create a new one
    if run_id is not None:
        rid = _uuid.UUID(run_id) if isinstance(run_id, str) else run_id
        run = await agent_runs_crud.get_agent_run(db, rid, bid)
        if not run:
            yield {"type": "agent_error", "error": "Agent run not found"}
            return
    else:
        run = await agent_runs_crud.create_run(db, bid, uid, goal, model, max_iterations)
        await db.commit()

    yield {"type": "agent_start", "run_id": str(run.id), "goal": goal}

    tools_json = json.dumps(
        [
            {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            }
            for t in AGENT_TOOLS
        ],
        indent=2,
    )

    messages = []

    try:
        for iteration in range(1, max_iterations + 1):
            # Check if cancelled/paused
            await db.refresh(run)
            if run.status == "cancelled":
                yield {"type": "agent_complete", "reason": "cancelled"}
                return
            if run.status == "paused":
                yield {"type": "agent_paused"}
                return

            # Get current board state
            board_state = await get_board_state_summary(db, board_id)

            # Build system prompt
            system = AGENT_SYSTEM_PROMPT.format(
                tools_json=tools_json,
                board_state=board_state,
            )

            # First message includes the goal
            if not messages:
                messages.append({
                    "role": "user",
                    "content": (
                        f"Goal: {goal}\n\n"
                        "Begin working on this goal. Respond with your first action in JSON format."
                    ),
                })

            # Query LLM
            result = await query_model(
                model=model,
                messages=[{"role": "system", "content": system}] + messages,
                timeout=60.0,
                user_id=uid,
                db=db,
            )

            if not result or not result.get("content"):
                yield {"type": "agent_error", "error": "No response from model"}
                break

            response_text = result["content"]
            messages.append({"role": "assistant", "content": response_text})

            # Parse the response -- extract the first JSON object
            try:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    parsed = json.loads(response_text[json_start:json_end])
                else:
                    raise ValueError("No JSON found in response")

                thought = parsed.get("thought", "")
                tool_name = parsed.get("tool", "")
                tool_params = parsed.get("parameters", {})
            except (json.JSONDecodeError, ValueError) as e:
                yield {
                    "type": "agent_error",
                    "error": f"Failed to parse agent response: {str(e)}",
                }
                break

            # Yield iteration event
            yield {
                "type": "agent_iteration",
                "iteration": iteration,
                "thought": thought,
                "tool": tool_name,
                "tool_params": tool_params,
            }

            # Update run with the new thought
            await agent_runs_crud.append_thought(db, run.id, bid, {
                "iteration": iteration,
                "thought": thought,
                "tool": tool_name,
                "params": tool_params,
            })
            run.iteration_count = iteration
            await db.commit()

            # Check for done
            if tool_name == "done":
                tool_result = await execute_tool("done", tool_params, board_id, user_id, db)
                yield {"type": "agent_tool_result", "result": tool_result}
                run.status = "completed"
                await db.commit()
                yield {
                    "type": "agent_complete",
                    "reason": "done",
                    "summary": tool_params.get("summary", ""),
                }
                return

            # Execute tool
            try:
                tool_result = await execute_tool(
                    tool_name, tool_params, board_id, user_id, db,
                )
                await db.commit()

                yield {"type": "agent_tool_result", "result": tool_result}

                # If a card was created, emit a dedicated event
                if tool_name == "create_card" and "card" in tool_result:
                    card_data = tool_result["card"]
                    await agent_runs_crud.append_created_card(
                        db, run.id, bid, tool_result["card_id"],
                    )
                    await db.commit()
                    yield {"type": "agent_card_created", "card": card_data}

                # Feed tool result back into the conversation
                messages.append({
                    "role": "user",
                    "content": f"Tool result: {json.dumps(tool_result)}",
                })

            except Exception as e:
                error_msg = f"Tool '{tool_name}' failed: {str(e)}"
                logger.error(error_msg)
                messages.append({
                    "role": "user",
                    "content": (
                        f"Error: {error_msg}\n"
                        "Please try a different approach."
                    ),
                })
                yield {"type": "agent_tool_result", "result": {"error": error_msg}}

            # Summarize conversation after 10 iterations to manage context window
            if iteration == 10 and len(messages) > 15:
                summary = "Previous actions summary: " + "; ".join(
                    m["content"][:100]
                    for m in messages[-6:]
                    if m["role"] == "assistant"
                )
                messages = messages[:2] + [{"role": "user", "content": summary}] + messages[-4:]

        # Max iterations reached
        run.status = "completed"
        run.error = "Max iterations reached"
        await db.commit()
        yield {"type": "agent_complete", "reason": "max_iterations"}

    except Exception as e:
        logger.error(f"Agent error: {e}")
        run.status = "failed"
        run.error = str(e)
        await db.commit()
        yield {"type": "agent_error", "error": str(e)}
