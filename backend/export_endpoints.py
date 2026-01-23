"""
Export and Share API endpoints to be added to main.py

Add these endpoints before the `if __name__ == "__main__":` block in main.py
"""


# ============ EXPORT AND SHARE ENDPOINTS ============

@app.get("/api/conversations/{conversation_id}/export")
async def export_conversation(conversation_id: str, format: str = "md"):
    """
    Export a conversation in the specified format.

    Args:
        conversation_id: The conversation ID to export
        format: Export format (md, json, html)

    Returns:
        Exported conversation in the requested format
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if format == "md" or format == "markdown":
        content = export_to_markdown(conversation)
        return PlainTextResponse(
            content=content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={conversation_id}.md"
            }
        )
    elif format == "json":
        content = export_to_json(conversation)
        return PlainTextResponse(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={conversation_id}.json"
            }
        )
    elif format == "html":
        content = export_to_html(conversation)
        return HTMLResponse(
            content=content,
            headers={
                "Content-Disposition": f"attachment; filename={conversation_id}.html"
            }
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


@app.post("/api/conversations/{conversation_id}/share")
async def share_conversation(conversation_id: str):
    """
    Create a shareable link for a conversation.

    Args:
        conversation_id: The conversation ID to share

    Returns:
        Share token that can be used to access the conversation
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    token = create_share_link(conversation_id)
    return {
        "token": token,
        "share_url": f"/shared/{token}"
    }


@app.get("/api/shared/{token}")
async def get_shared_conversation(token: str):
    """
    Get a shared conversation (read-only).

    Args:
        token: The share token

    Returns:
        Conversation data
    """
    conversation_id = get_shared_conversation_id(token)
    if conversation_id is None:
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation
