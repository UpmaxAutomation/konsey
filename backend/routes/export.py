"""Export, sharing, and webhook API routes."""

import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db, USE_DATABASE
from ..board_export import export_board_markdown, export_board_json, export_board_csv, export_board_zip
from ..export import create_board_share_link, get_shared_board_id

router = APIRouter(prefix="/api", tags=["export"])


class ShareResponse(BaseModel):
    token: str
    share_url: str


async def _get_board_data(db: AsyncSession, board_id: uuid.UUID) -> dict:
    """Fetch full board data for export."""
    from ..database.crud import boards as boards_crud
    from ..database.crud import sections as sections_crud

    board = await boards_crud.get_board(db, board_id)
    if not board:
        raise HTTPException(404, "Board not found")

    # Get cards and sections
    from ..database.models import Card, Section, Edge
    from sqlalchemy import select

    cards_result = await db.execute(select(Card).where(Card.board_id == board_id))
    cards = cards_result.scalars().all()

    sections_result = await db.execute(select(Section).where(Section.board_id == board_id))
    sections = sections_result.scalars().all()

    edges_result = await db.execute(select(Edge).where(Edge.board_id == board_id))
    edges = edges_result.scalars().all()

    return {
        "name": board.name,
        "description": getattr(board, "description", ""),
        "cards": [
            {
                "id": str(c.id),
                "title": c.title,
                "content": c.content or "",
                "card_type": c.card_type,
                "section_id": str(c.section_id) if c.section_id else None,
                "position_x": c.position_x,
                "position_y": c.position_y,
                "width": getattr(c, "width", 280),
                "height": getattr(c, "height", 200),
            }
            for c in cards
        ],
        "sections": [
            {
                "id": str(s.id),
                "title": s.title,
                "color": s.color,
                "position_x": s.position_x,
                "position_y": s.position_y,
                "width": s.width,
                "height": s.height,
            }
            for s in sections
        ],
        "edges": [
            {
                "source": str(e.source_card_id),
                "target": str(e.target_card_id),
                "edge_type": e.edge_type,
                "label": e.label,
            }
            for e in edges
        ],
    }


@router.get("/boards/{board_id}/export")
async def export_board(
    board_id: uuid.UUID,
    format: str = Query("md", regex="^(md|json|csv|zip)$"),
    db: AsyncSession = Depends(get_db),
):
    """Export a board in the specified format."""
    if not USE_DATABASE:
        raise HTTPException(400, "Database not enabled")

    board_data = await _get_board_data(db, board_id)

    if format == "md":
        content = export_board_markdown(board_data)
        return Response(content=content, media_type="text/markdown",
                       headers={"Content-Disposition": f'attachment; filename="{board_data["name"]}.md"'})
    elif format == "json":
        content = export_board_json(board_data)
        return Response(content=content, media_type="application/json",
                       headers={"Content-Disposition": f'attachment; filename="{board_data["name"]}.json"'})
    elif format == "csv":
        content = export_board_csv(board_data)
        return Response(content=content, media_type="text/csv",
                       headers={"Content-Disposition": f'attachment; filename="{board_data["name"]}.csv"'})
    elif format == "zip":
        content = export_board_zip(board_data)
        return Response(content=content, media_type="application/zip",
                       headers={"Content-Disposition": f'attachment; filename="{board_data["name"]}.zip"'})


@router.post("/boards/{board_id}/share")
async def share_board(board_id: uuid.UUID):
    """Create a public share link for a board."""
    result = create_board_share_link(str(board_id))
    return result


@router.get("/shared/boards/{token}")
async def get_shared_board(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Access a shared board (read-only)."""
    board_id = get_shared_board_id(token)
    if not board_id:
        raise HTTPException(404, "Share link not found or expired")

    if not USE_DATABASE:
        raise HTTPException(400, "Database not enabled")

    board_data = await _get_board_data(db, uuid.UUID(board_id))
    return {"board": board_data, "read_only": True}


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Incoming GitHub webhook -- create cards from events."""
    if not USE_DATABASE:
        raise HTTPException(400, "Database not enabled")

    body = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "unknown")

    # Parse GitHub event into card data
    card_title = ""
    card_content = ""

    if event_type == "issues":
        action = body.get("action", "")
        issue = body.get("issue", {})
        card_title = f"GitHub Issue: {issue.get('title', 'Unknown')}"
        card_content = f"**Action:** {action}\n**URL:** {issue.get('html_url', '')}\n\n{issue.get('body', '')}"
    elif event_type == "pull_request":
        action = body.get("action", "")
        pr = body.get("pull_request", {})
        card_title = f"GitHub PR: {pr.get('title', 'Unknown')}"
        card_content = f"**Action:** {action}\n**URL:** {pr.get('html_url', '')}\n\n{pr.get('body', '')}"
    elif event_type == "push":
        commits = body.get("commits", [])
        card_title = f"GitHub Push: {len(commits)} commit(s)"
        card_content = "\n".join([f"- {c.get('message', '')}" for c in commits[:10]])
    else:
        card_title = f"GitHub Event: {event_type}"
        card_content = json.dumps(body, indent=2, default=str)[:2000]

    # Look for a webhook target board_id in query params or headers
    target_board = request.headers.get("X-Board-Id") or request.query_params.get("board_id")
    if not target_board:
        return {"status": "received", "message": "No board_id specified, event logged but no card created"}

    from ..database.models import Card
    card = Card(
        board_id=uuid.UUID(target_board),
        title=card_title[:200],
        content=card_content,
        card_type="note",
        position_x=100,
        position_y=100,
    )
    db.add(card)
    await db.flush()

    return {"status": "created", "card_id": str(card.id)}


@router.post("/webhooks/slack")
async def slack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Incoming Slack webhook -- create cards from messages."""
    if not USE_DATABASE:
        raise HTTPException(400, "Database not enabled")

    body = await request.json()

    # Slack URL verification
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}

    event = body.get("event", {})
    text = event.get("text", "")
    user = event.get("user", "unknown")
    channel = event.get("channel", "unknown")

    card_title = f"Slack: message from {user} in #{channel}"
    card_content = text

    target_board = request.headers.get("X-Board-Id") or request.query_params.get("board_id")
    if not target_board:
        return {"status": "received", "message": "No board_id specified"}

    from ..database.models import Card
    card = Card(
        board_id=uuid.UUID(target_board),
        title=card_title[:200],
        content=card_content,
        card_type="note",
        position_x=100,
        position_y=150,
    )
    db.add(card)
    await db.flush()

    return {"status": "created", "card_id": str(card.id)}
