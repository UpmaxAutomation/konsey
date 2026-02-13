"""Prompt templates for AI actions on board cards."""

# ── Per-Card AI Actions ─────────────────────────

CARD_AI_PROMPTS = {
    "summarize": (
        "Summarize the following content in 2-4 sentences (MAXIMUM 80 words). "
        "Output ONLY the summary — no preamble, no bullet points, no headers, no extra commentary. "
        "Focus on the single most important takeaway and key supporting points.\n\n"
        "---\n{content}"
    ),
    "expand": (
        "Expand on the following content with more detail, examples, evidence, and analysis. "
        "Maintain the original perspective while adding depth.\n\n"
        "---\n{content}"
    ),
    "mind_map": (
        "Break the following content into 3-6 key sub-topics or themes. "
        "For each sub-topic, provide a short title (max 60 chars) and a brief description (2-3 sentences).\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '[\n  {{"title": "Sub-topic Title", "content": "Brief description..."}},\n  ...\n]\n\n'
        "Content to analyze:\n---\n{content}"
    ),
    "key_points": (
        "Extract the key points from the following content as a clear, structured list. "
        "Focus on the most important facts, arguments, and conclusions. "
        "Use bullet points and keep each point concise (1-2 sentences).\n\n"
        "---\n{content}"
    ),
    "ask_council": (
        "Analyze and provide a thoughtful, multi-perspective response to the following content. "
        "Consider different angles, potential counterarguments, and implications. "
        "Provide actionable insights where applicable.\n\n"
        "---\n{content}"
    ),
    "custom": "{prompt}\n\nContext:\n---\n{content}",
}


# ── Board-Level AI Actions ─────────────────────────

BOARD_AI_PROMPTS = {
    "summarize_board": (
        "Here are cards from a knowledge canvas board. "
        "Provide a comprehensive summary that captures the key themes, relationships, and insights. "
        "Structure your summary with clear sections.\n\n{cards}"
    ),
    "cluster_themes": (
        "Analyze these cards and group them into 2-6 thematic clusters. "
        "For each cluster, provide a name, description, and list the card IDs that belong to it.\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '[\n  {{"cluster_name": "Theme Name", "description": "Brief description...", '
        '"card_ids": ["id1", "id2"]}},\n  ...\n]\n\n'
        "Cards:\n{cards}"
    ),
    "find_connections": (
        "Analyze these cards and identify meaningful connections between them "
        "that may not be immediately obvious. For each connection, provide the two card IDs "
        "and a brief description of their relationship.\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '[\n  {{"from_id": "card_id_1", "to_id": "card_id_2", "label": "brief description"}},\n  ...\n]\n\n'
        "Cards:\n{cards}"
    ),
}


def format_cards_for_prompt(cards):
    """Format a list of card dicts for inclusion in a prompt."""
    parts = []
    for card in cards:
        card_type = card.get("card_type", "note")
        title = card.get("title") or "Untitled"
        content = card.get("content") or "(empty)"
        card_id = card.get("id", "unknown")
        parts.append(f"[Card {card_id} | {card_type}] {title}\n{content}")
    return "\n\n---\n\n".join(parts)
