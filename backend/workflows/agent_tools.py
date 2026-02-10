"""Tool definitions and dispatcher for the autonomous canvas agent.

Defines 8 tools the agent can invoke during a planning loop, plus an
``execute_tool`` dispatcher that translates tool calls into database and
LLM operations on a canvas board.
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Card
from ..database.crud import boards as boards_crud
from ..database.crud import sections as sections_crud

logger = logging.getLogger(__name__)

# Maximum character length for any single field returned in a tool result.
_MAX_RESULT_CONTENT_LENGTH = 2000

# ──────────────────────────────────────────────
# Tool definitions
# ──────────────────────────────────────────────

AGENT_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "create_card",
        "description": "Create a new card on the board.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Card title.",
                },
                "content": {
                    "type": "string",
                    "description": "Card body content (Markdown supported).",
                },
                "card_type": {
                    "type": "string",
                    "description": "Card type. Defaults to 'note'.",
                    "default": "note",
                },
                "color": {
                    "type": "string",
                    "description": "Optional hex color for the card (e.g. '#e3f2fd').",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "run_council",
        "description": "Run a full 3-stage council deliberation (parallel queries, peer review, chairman synthesis) and return a summary of the result.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question or prompt to deliberate on.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_cards",
        "description": "Search existing cards on the board by keyword (title or content).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keyword.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Defaults to 10.",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_card",
        "description": "Read a specific card's full content by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "UUID of the card to read.",
                },
            },
            "required": ["card_id"],
        },
    },
    {
        "name": "update_card",
        "description": "Update the title or content of an existing card.",
        "parameters": {
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "UUID of the card to update.",
                },
                "title": {
                    "type": "string",
                    "description": "New title (optional).",
                },
                "content": {
                    "type": "string",
                    "description": "New body content (optional).",
                },
            },
            "required": ["card_id"],
        },
    },
    {
        "name": "create_edge",
        "description": "Create a connection (edge) between two cards on the board.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_card_id": {
                    "type": "string",
                    "description": "UUID of the source card.",
                },
                "to_card_id": {
                    "type": "string",
                    "description": "UUID of the target card.",
                },
                "edge_type": {
                    "type": "string",
                    "description": "Type of relationship. Defaults to 'related'.",
                    "default": "related",
                },
                "label": {
                    "type": "string",
                    "description": "Optional label displayed on the edge.",
                },
            },
            "required": ["from_card_id", "to_card_id"],
        },
    },
    {
        "name": "create_section",
        "description": "Create a visual section/group on the board to organize cards.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Section heading.",
                },
                "color": {
                    "type": "string",
                    "description": "Section background color name. Defaults to 'gray'.",
                    "default": "gray",
                },
                "x": {
                    "type": "number",
                    "description": "X position on the canvas. Defaults to 0.",
                    "default": 0,
                },
                "y": {
                    "type": "number",
                    "description": "Y position on the canvas. Defaults to 0.",
                    "default": 0,
                },
                "width": {
                    "type": "number",
                    "description": "Width of the section. Defaults to 400.",
                    "default": 400,
                },
                "height": {
                    "type": "number",
                    "description": "Height of the section. Defaults to 300.",
                    "default": 300,
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "done",
        "description": "Signal that the agent has finished its goal. Call this when you have accomplished the objective.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A brief summary of what was accomplished.",
                },
            },
            "required": ["summary"],
        },
    },
]


def _truncate(value: str, max_len: int = _MAX_RESULT_CONTENT_LENGTH) -> str:
    """Truncate a string to *max_len* characters, appending an ellipsis if cut."""
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _serialize_card(card: Card) -> Dict[str, Any]:
    """Serialize a Card ORM object into a JSON-safe dictionary."""
    return {
        "id": str(card.id),
        "card_type": card.card_type,
        "title": card.title,
        "content": _truncate(card.content or ""),
        "position_x": card.position_x,
        "position_y": card.position_y,
        "width": card.width,
        "color": card.color,
    }


# ──────────────────────────────────────────────
# Tool execution handlers
# ──────────────────────────────────────────────

async def _handle_create_card(
    params: Dict[str, Any],
    board_id: uuid.UUID,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Create a new card on the board."""
    card = await boards_crud.create_card(
        db,
        board_id,
        card_type=params.get("card_type", "note"),
        title=params.get("title"),
        content=params.get("content"),
        color=params.get("color"),
    )
    return {
        "card_id": str(card.id),
        "card": _serialize_card(card),
    }


async def _handle_run_council(
    params: Dict[str, Any],
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Run a full 3-stage council deliberation and return a summary."""
    from ..council.orchestration import run_full_council

    query = params["query"]
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        query,
        user_id=user_id,
        db=db,
    )

    # Build a compact summary of individual model responses
    model_summaries: List[str] = []
    for result in stage1_results:
        model_name = result.get("model", "unknown")
        response_text = _truncate(result.get("response", ""), 300)
        model_summaries.append(f"[{model_name}]: {response_text}")

    synthesis = _truncate(stage3_result.get("response", "") if stage3_result else "", 1000)

    return {
        "synthesis": synthesis,
        "model_count": len(stage1_results),
        "model_summaries": model_summaries,
        "chairman_model": stage3_result.get("model") if stage3_result else None,
    }


async def _handle_search_cards(
    params: Dict[str, Any],
    board_id: uuid.UUID,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Search cards on the board by keyword in title or content."""
    query = params["query"]
    limit = params.get("limit", 10)
    pattern = f"%{query}%"

    result = await db.execute(
        select(Card)
        .where(
            Card.board_id == board_id,
            or_(
                Card.title.ilike(pattern),
                Card.content.ilike(pattern),
            ),
        )
        .limit(limit)
    )
    cards = list(result.scalars().all())

    matches = []
    for card in cards:
        matches.append({
            "id": str(card.id),
            "card_type": card.card_type,
            "title": card.title,
            "content_preview": _truncate(card.content or "", 200),
        })

    return {
        "count": len(matches),
        "matches": matches,
    }


async def _handle_read_card(
    params: Dict[str, Any],
    board_id: uuid.UUID,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Read a specific card's full content."""
    card_id = uuid.UUID(params["card_id"])
    card = await boards_crud.get_card_by_id(db, card_id, board_id)
    if card is None:
        return {"error": f"Card {params['card_id']} not found on this board."}
    return {
        "card_id": str(card.id),
        "card_type": card.card_type,
        "title": card.title,
        "content": _truncate(card.content or ""),
    }


async def _handle_update_card(
    params: Dict[str, Any],
    board_id: uuid.UUID,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Update an existing card's title and/or content."""
    card_id = uuid.UUID(params["card_id"])
    update_kwargs: Dict[str, Any] = {}
    if "title" in params:
        update_kwargs["title"] = params["title"]
    if "content" in params:
        update_kwargs["content"] = params["content"]

    card = await boards_crud.update_card(db, card_id, board_id, **update_kwargs)
    if card is None:
        return {"error": f"Card {params['card_id']} not found on this board."}
    return {
        "card_id": str(card.id),
        "card": _serialize_card(card),
    }


async def _handle_create_edge(
    params: Dict[str, Any],
    board_id: uuid.UUID,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Create a connection between two cards."""
    from_card_id = uuid.UUID(params["from_card_id"])
    to_card_id = uuid.UUID(params["to_card_id"])
    edge_type = params.get("edge_type", "related")
    label = params.get("label")

    edge = await boards_crud.create_edge(
        db,
        board_id,
        from_card_id=from_card_id,
        to_card_id=to_card_id,
        edge_type=edge_type,
        label=label,
    )
    return {
        "edge_id": str(edge.id),
        "from_card_id": str(edge.from_card_id),
        "to_card_id": str(edge.to_card_id),
        "edge_type": edge.edge_type,
        "label": edge.label,
    }


async def _handle_create_section(
    params: Dict[str, Any],
    board_id: uuid.UUID,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Create a visual section on the board."""
    section = await sections_crud.create_section(
        db,
        board_id,
        title=params["title"],
        color=params.get("color", "gray"),
        x=float(params.get("x", 0)),
        y=float(params.get("y", 0)),
        width=float(params.get("width", 400)),
        height=float(params.get("height", 300)),
    )
    return {
        "section_id": str(section.id),
        "title": section.title,
        "color": section.color,
        "x": section.x,
        "y": section.y,
        "width": section.width,
        "height": section.height,
    }


def _handle_done(params: Dict[str, Any]) -> Dict[str, Any]:
    """Signal that the agent has finished its goal."""
    return {
        "status": "completed",
        "summary": params["summary"],
    }


# ──────────────────────────────────────────────
# Public dispatcher
# ──────────────────────────────────────────────

async def execute_tool(
    tool_name: str,
    params: Dict[str, Any],
    board_id: str,
    user_id: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Execute a named tool and return the result as a dictionary.

    Args:
        tool_name: One of the tool names defined in ``AGENT_TOOLS``.
        params: Parameter dictionary matching the tool's JSON schema.
        board_id: UUID string of the target board.
        user_id: UUID string of the calling user.
        db: Async database session.

    Returns:
        A dictionary describing the result of the tool invocation.

    Raises:
        ValueError: If the tool_name is not recognised.
    """
    bid = uuid.UUID(board_id) if isinstance(board_id, str) else board_id
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

    if tool_name == "create_card":
        return await _handle_create_card(params, bid, db)

    if tool_name == "run_council":
        return await _handle_run_council(params, uid, db)

    if tool_name == "search_cards":
        return await _handle_search_cards(params, bid, db)

    if tool_name == "read_card":
        return await _handle_read_card(params, bid, db)

    if tool_name == "update_card":
        return await _handle_update_card(params, bid, db)

    if tool_name == "create_edge":
        return await _handle_create_edge(params, bid, db)

    if tool_name == "create_section":
        return await _handle_create_section(params, bid, db)

    if tool_name == "done":
        return _handle_done(params)

    raise ValueError(f"Unknown tool: {tool_name}")
