"""Pipeline execution engine for visual DAG pipelines on canvas.

Executes a DAG of pl_* cards connected by 'pipeline' edges.
Uses Kahn's algorithm for topological sort and processes nodes in order,
yielding SSE-formatted strings for real-time progress updates.
"""

import json
import logging
import uuid
from collections import defaultdict, deque
from typing import AsyncGenerator, Dict, List, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Card, Edge

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-4o"


def _sse(data: Dict[str, Any]) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _load_pipeline_graph(
    board_id: str, db: AsyncSession
) -> tuple[List[Card], List[Edge]]:
    """Load all pl_* cards and pipeline edges for a board."""
    bid = uuid.UUID(board_id)

    cards_result = await db.execute(
        select(Card).where(Card.board_id == bid, Card.card_type.like("pl_%"))
    )
    cards = list(cards_result.scalars().all())

    edges_result = await db.execute(
        select(Edge).where(Edge.board_id == bid, Edge.edge_type == "pipeline")
    )
    edges = list(edges_result.scalars().all())

    return cards, edges


def _topological_sort(
    cards: List[Card], edges: List[Edge]
) -> List[uuid.UUID]:
    """Topological sort via Kahn's algorithm. Raises ValueError on cycle."""
    card_ids = {c.id for c in cards}

    adjacency: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    in_degree: Dict[uuid.UUID, int] = {cid: 0 for cid in card_ids}

    for edge in edges:
        if edge.from_card_id in card_ids and edge.to_card_id in card_ids:
            adjacency[edge.from_card_id].append(edge.to_card_id)
            in_degree[edge.to_card_id] = in_degree.get(edge.to_card_id, 0) + 1

    queue = deque(cid for cid, deg in in_degree.items() if deg == 0)
    order: List[uuid.UUID] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adjacency[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(card_ids):
        raise ValueError(
            f"Pipeline contains a cycle. Sorted {len(order)} of {len(card_ids)} nodes."
        )

    return order


def _build_upstream_map(
    edges: List[Edge], card_ids: set
) -> Dict[uuid.UUID, List[tuple[uuid.UUID, Optional[str]]]]:
    """Build map of node_id -> [(upstream_node_id, source_handle), ...]."""
    upstream: Dict[uuid.UUID, List[tuple[uuid.UUID, Optional[str]]]] = defaultdict(list)
    for edge in edges:
        if edge.from_card_id in card_ids and edge.to_card_id in card_ids:
            upstream[edge.to_card_id].append((edge.from_card_id, edge.source_handle))
    return upstream


def _build_downstream_map(
    edges: List[Edge], card_ids: set
) -> Dict[uuid.UUID, List[tuple[uuid.UUID, Optional[str]]]]:
    """Build map of node_id -> [(downstream_node_id, source_handle), ...]."""
    downstream: Dict[uuid.UUID, List[tuple[uuid.UUID, Optional[str]]]] = defaultdict(list)
    for edge in edges:
        if edge.from_card_id in card_ids and edge.to_card_id in card_ids:
            downstream[edge.from_card_id].append((edge.to_card_id, edge.source_handle))
    return downstream


def _gather_inputs(
    node_id: uuid.UUID,
    upstream_map: Dict[uuid.UUID, List[tuple[uuid.UUID, Optional[str]]]],
    outputs: Dict[uuid.UUID, str],
) -> str:
    """Concatenate outputs from all upstream nodes."""
    upstream_nodes = upstream_map.get(node_id, [])
    if not upstream_nodes:
        return ""
    parts = []
    for upstream_id, _ in upstream_nodes:
        if upstream_id in outputs:
            parts.append(outputs[upstream_id])
    return "\n\n---\n\n".join(parts)


async def _execute_node(
    card: Card,
    input_text: str,
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None,
) -> str:
    """Execute a single pipeline node and return its output text."""
    card_type = card.card_type
    extra = card.extra or {}

    if card_type == "pl_input":
        return card.content or extra.get("prompt", "") or input_text

    elif card_type == "pl_llm":
        from ..llm.client import query_model

        model = extra.get("model", DEFAULT_MODEL)
        template = extra.get("prompt_template", "{{input}}")
        prompt = template.replace("{{input}}", input_text)
        messages = [{"role": "user", "content": prompt}]

        result = await query_model(model, messages, user_id=user_id, db=db)
        if result is None:
            raise RuntimeError(f"LLM node failed: model {model} returned no response.")
        return result.get("content", "")

    elif card_type == "pl_council":
        # Simplified v1: single model call (full council deliberation is v2)
        from ..llm.client import query_model

        model = extra.get("model", DEFAULT_MODEL)
        template = extra.get("prompt_template", "{{input}}")
        prompt = template.replace("{{input}}", input_text)
        messages = [{"role": "user", "content": prompt}]

        result = await query_model(model, messages, user_id=user_id, db=db)
        if result is None:
            raise RuntimeError(f"Council node failed: model {model} returned no response.")
        return result.get("content", "")

    elif card_type == "pl_transform":
        from ..llm.client import query_model

        model = extra.get("model", DEFAULT_MODEL)
        template = extra.get("prompt_template", "{{input}}")
        prompt = template.replace("{{input}}", input_text)
        messages = [{"role": "user", "content": prompt}]

        result = await query_model(model, messages, user_id=user_id, db=db)
        if result is None:
            raise RuntimeError(f"Transform node failed: model {model} returned no response.")
        return result.get("content", "")

    elif card_type == "pl_conditional":
        from ..llm.client import query_model

        model = extra.get("model", DEFAULT_MODEL)
        condition = extra.get("condition", "")
        prompt = (
            f"Evaluate the following condition given the input below. "
            f"Respond with only TRUE or FALSE.\n\n"
            f"Condition: {condition}\n\n"
            f"Input:\n{input_text}"
        )
        messages = [{"role": "user", "content": prompt}]

        result = await query_model(model, messages, user_id=user_id, db=db)
        if result is None:
            raise RuntimeError(f"Conditional node failed: model {model} returned no response.")
        response_text = result.get("content", "")
        decision = "TRUE" if "TRUE" in response_text.upper() else "FALSE"
        return decision

    elif card_type == "pl_output":
        return input_text

    else:
        raise ValueError(f"Unknown pipeline node type: {card_type}")


async def execute_pipeline(
    board_id: str,
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None,
) -> AsyncGenerator[str, None]:
    """Execute a visual pipeline DAG, yielding SSE-formatted strings.

    1. Loads pl_* cards and pipeline edges from the board
    2. Topologically sorts the DAG (Kahn's algorithm)
    3. Executes each node in order
    4. Yields SSE events for progress tracking
    5. Stores outputs in card.extra['last_output']
    """
    # Load graph
    cards, edges = await _load_pipeline_graph(board_id, db)

    if not cards:
        yield _sse({"type": "pipeline_error", "error": "No pipeline nodes found on this board."})
        return

    card_map: Dict[uuid.UUID, Card] = {c.id: c for c in cards}
    card_ids = set(card_map.keys())

    # Topological sort
    try:
        execution_order = _topological_sort(cards, edges)
    except ValueError as e:
        yield _sse({"type": "pipeline_error", "error": str(e)})
        return

    upstream_map = _build_upstream_map(edges, card_ids)
    downstream_map = _build_downstream_map(edges, card_ids)

    yield _sse({
        "type": "pipeline_start",
        "node_count": len(execution_order),
    })

    outputs: Dict[uuid.UUID, str] = {}
    skipped: set = set()  # Nodes skipped due to conditional routing or failed upstream

    for node_id in execution_order:
        card = card_map[node_id]

        # Skip if this node was marked as skipped (conditional routing)
        if node_id in skipped:
            yield _sse({
                "type": "node_skipped",
                "node_id": str(node_id),
                "node_type": card.card_type,
            })
            continue

        yield _sse({
            "type": "node_start",
            "node_id": str(node_id),
            "node_type": card.card_type,
            "title": card.title or "",
        })

        # Check if any upstream node failed/was skipped
        upstream_nodes = upstream_map.get(node_id, [])
        has_failed_upstream = any(uid in skipped for uid, _ in upstream_nodes)
        if has_failed_upstream and card.card_type != "pl_input":
            skipped.add(node_id)
            yield _sse({
                "type": "node_skipped",
                "node_id": str(node_id),
                "node_type": card.card_type,
                "reason": "upstream_skipped",
            })
            continue

        try:
            input_text = _gather_inputs(node_id, upstream_map, outputs)
            output_text = await _execute_node(card, input_text, db, user_id=user_id)
            outputs[node_id] = output_text

            # Store output in card.extra['last_output']
            new_extra = dict(card.extra or {})
            new_extra["last_output"] = output_text[:10000]
            card.extra = new_extra
            await db.flush()

            # Handle conditional routing: skip branches not taken
            if card.card_type == "pl_conditional":
                decision = output_text  # "TRUE" or "FALSE"
                downstream_nodes = downstream_map.get(node_id, [])
                for downstream_id, source_handle in downstream_nodes:
                    handle = (source_handle or "").lower()
                    if decision == "TRUE" and handle == "false":
                        skipped.add(downstream_id)
                    elif decision == "FALSE" and handle == "true":
                        skipped.add(downstream_id)

            truncated = output_text[:500] if output_text else ""
            yield _sse({
                "type": "node_complete",
                "node_id": str(node_id),
                "node_type": card.card_type,
                "output": truncated,
            })

        except Exception as exc:
            logger.exception(
                "Pipeline node %s (%s) failed: %s", node_id, card.card_type, exc
            )
            skipped.add(node_id)

            # Store error in card extra
            new_extra = dict(card.extra or {})
            new_extra["last_error"] = str(exc)[:2000]
            card.extra = new_extra
            await db.flush()

            yield _sse({
                "type": "node_error",
                "node_id": str(node_id),
                "node_type": card.card_type,
                "error": str(exc),
            })

    # Commit all card.extra updates at the end
    await db.commit()

    yield _sse({
        "type": "pipeline_complete",
        "node_count": len(execution_order),
        "skipped_count": len(skipped),
    })

    logger.info(
        "Pipeline on board %s completed: %d nodes, %d skipped",
        board_id, len(execution_order), len(skipped),
    )
