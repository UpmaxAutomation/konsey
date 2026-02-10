"""Export and sharing functionality for conversations."""

import json
import secrets
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from .config import DATA_DIR


SHARES_FILE = Path(DATA_DIR) / "shares.json"


def ensure_shares_file():
    """Ensure the shares file exists."""
    if not SHARES_FILE.exists():
        SHARES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SHARES_FILE, 'w') as f:
            json.dump({}, f, indent=2)


def load_shares() -> Dict[str, Any]:
    """Load all share links from storage."""
    ensure_shares_file()
    with open(SHARES_FILE, 'r') as f:
        return json.load(f)


def save_shares(shares: Dict[str, Any]):
    """Save share links to storage."""
    ensure_shares_file()
    with open(SHARES_FILE, 'w') as f:
        json.dump(shares, f, indent=2)


def export_to_markdown(conversation: Dict[str, Any]) -> str:
    """
    Export a conversation to Markdown format.

    Args:
        conversation: Conversation dict with all messages

    Returns:
        Markdown-formatted string
    """
    lines = []

    # Header
    lines.append(f"# {conversation['title']}")
    lines.append(f"\n*Created: {conversation['created_at']}*\n")
    lines.append("---\n")

    # Messages
    for msg in conversation['messages']:
        if msg['role'] == 'user':
            lines.append(f"## User\n")
            lines.append(f"{msg['content']}\n")

        elif msg['role'] == 'assistant':
            lines.append(f"## LLM Council Response\n")

            # Stage 1: Individual Responses
            if msg.get('stage1'):
                lines.append("### Stage 1: Individual Responses\n")
                for i, response in enumerate(msg['stage1'], 1):
                    model = response.get('model', 'Unknown')
                    content = response.get('response', '')
                    lines.append(f"#### Response {i} ({model})\n")
                    lines.append(f"{content}\n")

            # Stage 2: Peer Rankings
            if msg.get('stage2'):
                lines.append("### Stage 2: Peer Rankings\n")
                for i, ranking in enumerate(msg['stage2'], 1):
                    model = ranking.get('model', 'Unknown')
                    evaluation = ranking.get('evaluation', '')
                    parsed = ranking.get('parsed_ranking', [])
                    lines.append(f"#### Evaluation {i} ({model})\n")
                    lines.append(f"{evaluation}\n")
                    if parsed:
                        lines.append("**Extracted Ranking:**\n")
                        for rank_item in parsed:
                            lines.append(f"- {rank_item}\n")
                        lines.append("\n")

            # Stage 3: Final Synthesis
            if msg.get('stage3'):
                lines.append("### Stage 3: Final Synthesis\n")
                model = msg['stage3'].get('model', 'Unknown')
                response = msg['stage3'].get('response', '')
                lines.append(f"**Synthesized by:** {model}\n")
                lines.append(f"{response}\n")

        lines.append("---\n")

    return "\n".join(lines)


def export_to_json(conversation: Dict[str, Any]) -> str:
    """
    Export a conversation to JSON format.

    Args:
        conversation: Conversation dict with all messages

    Returns:
        JSON-formatted string
    """
    return json.dumps(conversation, indent=2)


def export_to_html(conversation: Dict[str, Any]) -> str:
    """
    Export a conversation to HTML format.

    Args:
        conversation: Conversation dict with all messages

    Returns:
        HTML-formatted string
    """
    lines = []

    # HTML header
    lines.append("<!DOCTYPE html>")
    lines.append("<html lang='en'>")
    lines.append("<head>")
    lines.append("    <meta charset='UTF-8'>")
    lines.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    lines.append(f"    <title>{conversation['title']}</title>")
    lines.append("    <style>")
    lines.append("        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }")
    lines.append("        h1 { color: #333; border-bottom: 3px solid #4a90e2; padding-bottom: 10px; }")
    lines.append("        h2 { color: #4a90e2; margin-top: 30px; }")
    lines.append("        h3 { color: #666; margin-top: 20px; }")
    lines.append("        h4 { color: #888; margin-top: 15px; }")
    lines.append("        .metadata { color: #999; font-style: italic; margin-bottom: 20px; }")
    lines.append("        .user-message { background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0; }")
    lines.append("        .assistant-message { margin: 15px 0; }")
    lines.append("        .stage { margin: 20px 0; }")
    lines.append("        .response { background: #fafafa; padding: 12px; border-left: 3px solid #4a90e2; margin: 10px 0; }")
    lines.append("        .final-synthesis { background: #f0fff0; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745; }")
    lines.append("        .model-name { font-weight: bold; color: #4a90e2; }")
    lines.append("        pre { background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }")
    lines.append("        hr { border: none; border-top: 1px solid #ddd; margin: 30px 0; }")
    lines.append("    </style>")
    lines.append("</head>")
    lines.append("<body>")

    # Content
    lines.append(f"    <h1>{conversation['title']}</h1>")
    lines.append(f"    <div class='metadata'>Created: {conversation['created_at']}</div>")

    # Messages
    for msg in conversation['messages']:
        if msg['role'] == 'user':
            lines.append("    <div class='user-message'>")
            lines.append("        <h2>User</h2>")
            lines.append(f"        <p>{msg['content']}</p>")
            lines.append("    </div>")

        elif msg['role'] == 'assistant':
            lines.append("    <div class='assistant-message'>")
            lines.append("        <h2>LLM Council Response</h2>")

            # Stage 1
            if msg.get('stage1'):
                lines.append("        <div class='stage'>")
                lines.append("            <h3>Stage 1: Individual Responses</h3>")
                for i, response in enumerate(msg['stage1'], 1):
                    model = response.get('model', 'Unknown')
                    content = response.get('response', '').replace('\n', '<br>')
                    lines.append("            <div class='response'>")
                    lines.append(f"                <h4>Response {i} (<span class='model-name'>{model}</span>)</h4>")
                    lines.append(f"                <p>{content}</p>")
                    lines.append("            </div>")
                lines.append("        </div>")

            # Stage 2
            if msg.get('stage2'):
                lines.append("        <div class='stage'>")
                lines.append("            <h3>Stage 2: Peer Rankings</h3>")
                for i, ranking in enumerate(msg['stage2'], 1):
                    model = ranking.get('model', 'Unknown')
                    evaluation = ranking.get('evaluation', '').replace('\n', '<br>')
                    parsed = ranking.get('parsed_ranking', [])
                    lines.append("            <div class='response'>")
                    lines.append(f"                <h4>Evaluation {i} (<span class='model-name'>{model}</span>)</h4>")
                    lines.append(f"                <p>{evaluation}</p>")
                    if parsed:
                        lines.append("                <p><strong>Extracted Ranking:</strong></p>")
                        lines.append("                <ul>")
                        for rank_item in parsed:
                            lines.append(f"                    <li>{rank_item}</li>")
                        lines.append("                </ul>")
                    lines.append("            </div>")
                lines.append("        </div>")

            # Stage 3
            if msg.get('stage3'):
                lines.append("        <div class='stage'>")
                lines.append("            <h3>Stage 3: Final Synthesis</h3>")
                model = msg['stage3'].get('model', 'Unknown')
                response = msg['stage3'].get('response', '').replace('\n', '<br>')
                lines.append("            <div class='final-synthesis'>")
                lines.append(f"                <p><strong>Synthesized by:</strong> <span class='model-name'>{model}</span></p>")
                lines.append(f"                <p>{response}</p>")
                lines.append("            </div>")
                lines.append("        </div>")

            lines.append("    </div>")

        lines.append("    <hr>")

    # HTML footer
    lines.append("</body>")
    lines.append("</html>")

    return "\n".join(lines)


def create_share_link(conversation_id: str) -> str:
    """
    Create a shareable link for a conversation.

    Args:
        conversation_id: The conversation ID to share

    Returns:
        Unique share token
    """
    shares = load_shares()

    # Generate unique token
    token = secrets.token_urlsafe(16)

    # Ensure uniqueness
    while token in shares:
        token = secrets.token_urlsafe(16)

    # Store share mapping
    shares[token] = {
        "conversation_id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": None  # No expiration for now
    }

    save_shares(shares)
    return token


def get_shared_conversation_id(token: str) -> Optional[str]:
    """
    Get the conversation ID associated with a share token.

    Args:
        token: The share token

    Returns:
        Conversation ID or None if token not found
    """
    shares = load_shares()
    share_info = shares.get(token)

    if not share_info:
        return None

    # Check expiration if set
    if share_info.get('expires_at'):
        expires = datetime.fromisoformat(share_info['expires_at'])
        if datetime.utcnow() > expires:
            return None

    return share_info.get('conversation_id')


# ---- Board sharing ----

def create_board_share_link(board_id: str) -> dict:
    """Generate a share token for a board."""
    import hashlib
    import time
    token = hashlib.sha256(f"{board_id}-{time.time()}".encode()).hexdigest()[:16]

    shares = load_shares()

    shares[token] = {
        "board_id": board_id,
        "created_at": datetime.utcnow().isoformat(),
    }

    save_shares(shares)

    return {"token": token, "share_url": f"/shared/board/{token}"}


def get_shared_board_id(token: str) -> Optional[str]:
    """Validate a board share token and return the board_id."""
    shares = load_shares()
    entry = shares.get(token)
    if entry and entry.get("board_id"):
        return entry.get("board_id")
    return None
