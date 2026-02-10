"""Board export utilities — export boards to Markdown, JSON, CSV, ZIP."""

import io
import csv
import json
import zipfile
from typing import List, Optional


def export_board_markdown(board_data: dict) -> str:
    """Export board as hierarchical Markdown."""
    lines = []
    name = board_data.get("name", "Untitled Board")
    lines.append(f"# {name}\n")

    if board_data.get("description"):
        lines.append(f"{board_data['description']}\n")

    # Sections first
    sections = board_data.get("sections", [])
    cards = board_data.get("cards", [])

    # Group cards by section
    section_cards = {}
    orphan_cards = []
    for card in cards:
        sid = card.get("section_id")
        if sid:
            section_cards.setdefault(sid, []).append(card)
        else:
            orphan_cards.append(card)

    for section in sections:
        sid = section.get("id")
        lines.append(f"\n## {section.get('title', 'Section')}\n")
        for card in section_cards.get(sid, []):
            _append_card_md(lines, card)

    if orphan_cards:
        if sections:
            lines.append("\n## Other Cards\n")
        for card in orphan_cards:
            _append_card_md(lines, card)

    # Edges
    edges = board_data.get("edges", [])
    if edges:
        lines.append("\n## Connections\n")
        for edge in edges:
            label = edge.get("label", edge.get("edge_type", "related"))
            lines.append(f"- {edge.get('source', '?')} --[{label}]--> {edge.get('target', '?')}")

    return "\n".join(lines)


def _append_card_md(lines: list, card: dict):
    """Append a card as Markdown."""
    card_type = card.get("card_type", "note")
    title = card.get("title", "Untitled")
    content = card.get("content", "")
    lines.append(f"\n### [{card_type.upper()}] {title}\n")
    if content:
        lines.append(content)
    props = card.get("properties", {})
    if props:
        lines.append("\n**Properties:**")
        for k, v in props.items():
            lines.append(f"- {k}: {v}")


def export_board_json(board_data: dict) -> str:
    """Export board as formatted JSON."""
    return json.dumps(board_data, indent=2, default=str, ensure_ascii=False)


def export_board_csv(board_data: dict) -> str:
    """Export board cards as CSV table."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Title", "Type", "Content", "Section", "Position X", "Position Y", "Properties"])

    sections_map = {s.get("id"): s.get("title", "") for s in board_data.get("sections", [])}

    for card in board_data.get("cards", []):
        writer.writerow([
            card.get("title", ""),
            card.get("card_type", "note"),
            card.get("content", "")[:500],
            sections_map.get(card.get("section_id"), ""),
            card.get("position_x", 0),
            card.get("position_y", 0),
            json.dumps(card.get("properties", {})),
        ])

    return output.getvalue()


def export_board_zip(board_data: dict, assets: Optional[List[dict]] = None) -> bytes:
    """Export board as ZIP containing board.json, board.md, board.csv, and asset references."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("board.json", export_board_json(board_data))
        zf.writestr("board.md", export_board_markdown(board_data))
        zf.writestr("board.csv", export_board_csv(board_data))

        if assets:
            manifest = []
            for asset in assets:
                manifest.append({
                    "name": asset.get("name"),
                    "type": asset.get("asset_type"),
                    "url": asset.get("url"),
                })
            zf.writestr("assets/manifest.json", json.dumps(manifest, indent=2))

    return buf.getvalue()
