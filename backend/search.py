"""Global search functionality for conversations."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR


def search_conversations(
    query: str,
    folder: Optional[str] = None,
    tags: Optional[List[str]] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Search across all conversations for matching content.

    Args:
        query: Search query string
        folder: Filter by folder/project ID (optional)
        tags: Filter by tags (optional)
        from_date: Filter conversations created after this date (ISO format)
        to_date: Filter conversations created before this date (ISO format)
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)

    Returns:
        Dict with search results and metadata
    """
    if not query or len(query.strip()) < 2:
        return {
            "results": [],
            "total": 0,
            "query": query,
            "limit": limit,
            "offset": offset
        }

    query_lower = query.lower().strip()
    results = []

    # Ensure data directory exists
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    # Scan all conversation files
    for filename in os.listdir(DATA_DIR):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(DATA_DIR, filename)

        try:
            with open(filepath, 'r') as f:
                conversation = json.load(f)

            # Apply date filters
            if from_date or to_date:
                created_at = conversation.get('created_at', '')
                if from_date and created_at < from_date:
                    continue
                if to_date and created_at > to_date:
                    continue

            # Apply folder filter (if supported in future)
            if folder:
                # Placeholder for future folder/project support
                conv_folder = conversation.get('folder_id', None)
                if conv_folder != folder:
                    continue

            # Apply tags filter (if supported in future)
            if tags:
                # Placeholder for future tags support
                conv_tags = conversation.get('tags', [])
                if not any(tag in conv_tags for tag in tags):
                    continue

            # Search in conversation data
            matches = _search_in_conversation(conversation, query_lower)

            if matches:
                results.append({
                    "conversation_id": conversation['id'],
                    "title": conversation.get('title', 'New Conversation'),
                    "created_at": conversation.get('created_at', ''),
                    "matches": matches,
                    "match_count": len(matches)
                })

        except (json.JSONDecodeError, IOError) as e:
            # Skip malformed or unreadable files
            continue

    # Sort by relevance (match count, then by date)
    results.sort(key=lambda x: (x['match_count'], x['created_at']), reverse=True)

    # Apply pagination
    total_results = len(results)
    paginated_results = results[offset:offset + limit]

    return {
        "results": paginated_results,
        "total": total_results,
        "query": query,
        "limit": limit,
        "offset": offset
    }


def _search_in_conversation(conversation: Dict[str, Any], query: str) -> List[Dict[str, str]]:
    """
    Search within a single conversation and return all matches.

    Args:
        conversation: Conversation dict
        query: Lowercase search query

    Returns:
        List of match dicts with snippet and context
    """
    matches = []

    # Search in title
    title = conversation.get('title', '')
    if query in title.lower():
        matches.append({
            "type": "title",
            "snippet": _create_snippet(title, query),
            "context": "Conversation title"
        })

    # Search in messages
    messages = conversation.get('messages', [])
    for msg_idx, message in enumerate(messages):
        role = message.get('role', 'unknown')

        # Search in user messages
        if role == 'user':
            content = message.get('content', '')
            if query in content.lower():
                matches.append({
                    "type": "user_message",
                    "snippet": _create_snippet(content, query),
                    "context": f"User message #{msg_idx + 1}"
                })

        # Search in assistant messages (stage3 final response)
        elif role == 'assistant':
            # Search in Stage 1 responses
            stage1 = message.get('stage1', [])
            for response in stage1:
                model = response.get('model', 'unknown')
                content = response.get('response', '')
                if query in content.lower():
                    matches.append({
                        "type": "stage1_response",
                        "snippet": _create_snippet(content, query),
                        "context": f"Response from {model}"
                    })

            # Search in Stage 2 evaluations
            stage2 = message.get('stage2', [])
            for evaluation in stage2:
                model = evaluation.get('model', 'unknown')
                content = evaluation.get('evaluation', '')
                if query in content.lower():
                    matches.append({
                        "type": "stage2_evaluation",
                        "snippet": _create_snippet(content, query),
                        "context": f"Evaluation from {model}"
                    })

            # Search in Stage 3 final synthesis
            stage3 = message.get('stage3', {})
            final_response = stage3.get('response', '')
            if query in final_response.lower():
                matches.append({
                    "type": "stage3_synthesis",
                    "snippet": _create_snippet(final_response, query),
                    "context": "Final synthesized answer"
                })

    return matches


def _create_snippet(text: str, query: str, max_length: int = 200) -> str:
    """
    Create a highlighted snippet around the search query.

    Args:
        text: Full text content
        query: Search query (lowercase)
        max_length: Maximum snippet length

    Returns:
        Snippet with query highlighted
    """
    text_lower = text.lower()
    query_pos = text_lower.find(query)

    if query_pos == -1:
        # Query not found, return beginning of text
        return text[:max_length] + ('...' if len(text) > max_length else '')

    # Calculate snippet window around the match
    snippet_start = max(0, query_pos - max_length // 2)
    snippet_end = min(len(text), query_pos + len(query) + max_length // 2)

    # Extract snippet
    snippet = text[snippet_start:snippet_end]

    # Add ellipsis if truncated
    if snippet_start > 0:
        snippet = '...' + snippet
    if snippet_end < len(text):
        snippet = snippet + '...'

    # Highlight the query match (case-insensitive)
    # Find the actual query in the snippet (preserve original case)
    snippet_lower = snippet.lower()
    match_pos = snippet_lower.find(query)

    if match_pos != -1:
        # Wrap match in special markers for frontend highlighting
        before = snippet[:match_pos]
        match = snippet[match_pos:match_pos + len(query)]
        after = snippet[match_pos + len(query):]
        snippet = f"{before}[[HIGHLIGHT]]{match}[[/HIGHLIGHT]]{after}"

    return snippet


def get_search_suggestions(query: str, limit: int = 5) -> List[str]:
    """
    Get search suggestions based on query prefix.

    Args:
        query: Partial search query
        limit: Maximum number of suggestions

    Returns:
        List of suggested search terms
    """
    # This is a simple implementation - can be enhanced with:
    # - Search history tracking
    # - Common terms extraction
    # - Recent conversations analysis

    suggestions = []

    if len(query) < 2:
        return suggestions

    query_lower = query.lower().strip()
    seen_titles = set()

    # Scan conversations for title matches
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    for filename in os.listdir(DATA_DIR):
        if not filename.endswith('.json'):
            continue

        try:
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, 'r') as f:
                conversation = json.load(f)

            title = conversation.get('title', '')
            if query_lower in title.lower() and title not in seen_titles:
                suggestions.append(title)
                seen_titles.add(title)

                if len(suggestions) >= limit:
                    break

        except (json.JSONDecodeError, IOError):
            continue

    return suggestions
