"""Tool and search routes for LLM Council."""

import logging
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_optional
from ..database.connection import get_db
from ..database.models import User
from ..config import get_enhanced_features
from ..tools import (
    web_search, fetch_url, execute_python, execute_javascript,
    remember_fact, remember_decision, get_memory_context, clear_memory, get_memory_stats,
    set_preference
)
from .. import search
from ..rate_limit import limiter, RATE_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tools"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Search query (max 1k chars)")
    num_results: Optional[int] = Field(default=5, ge=1, le=50)


class CodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000, description="Code to execute (max 50k chars)")
    language: str = Field(default="python", max_length=20)
    timeout: Optional[int] = Field(default=30, ge=1, le=120)


class MemoryRequest(BaseModel):
    action: str  # remember_fact, remember_decision, set_preference, get_context, clear, stats
    content: Optional[str] = None
    category: Optional[str] = "general"
    question: Optional[str] = None
    decision: Optional[str] = None
    reasoning: Optional[str] = None
    key: Optional[str] = None
    value: Optional[Any] = None


# ──────────────────────────────────────────────
# Tool endpoints
# ──────────────────────────────────────────────

@router.post(
    "/tools/search",
    tags=["tools"],
    summary="Web Search",
    response_description="Search results from web"
)
@limiter.limit(RATE_LIMITS["search"])
async def tool_search(request: Request, body: SearchRequest):
    """
    Perform a web search using configured search provider.

    Searches the web for the given query and returns relevant results.
    The web search feature must be enabled in enhanced features.

    Args:
        request: SearchRequest containing:
            - query: The search query string
            - num_results: Number of results to return (default: 5)

    Returns:
        dict: Search results containing:
            - query: The original query
            - results: List of search results with title, url, snippet

    Raises:
        HTTPException 403: If web search feature is disabled
    """
    features = get_enhanced_features()
    if not features.get("web_search"):
        raise HTTPException(status_code=403, detail="Web search is disabled")

    results = await web_search(body.query, body.num_results)
    return {"query": body.query, "results": results}


@router.post(
    "/tools/perplexity-search",
    tags=["tools"],
    summary="Perplexity Web Search",
    response_description="Perplexity search results with citations"
)
@limiter.limit(RATE_LIMITS["search"])
async def tool_perplexity_search(request: Request, body: SearchRequest):
    """
    Search the web using Perplexity AI.

    Uses Perplexity's sonar model for web-grounded search results.
    Requires a Perplexity API key to be configured.

    Args:
        request: SearchRequest with query and optional num_results

    Returns:
        dict: Search results containing:
            - query: The original query
            - summary: Perplexity's answer
            - citations: List of source URLs
            - results: Formatted results

    Raises:
        HTTPException 403: If no Perplexity API key configured
        HTTPException 500: If search fails
    """
    from ..config import get_perplexity_api_key, get_perplexity_models
    from ..tools import perplexity_search, web_search

    api_key = get_perplexity_api_key()
    if not api_key:
        search_result = await web_search(body.query, body.num_results)
        if isinstance(search_result, dict):
            if search_result.get("error"):
                return {
                    "query": body.query,
                    "summary": "",
                    "citations": [],
                    "results": [],
                    "model": "duckduckgo",
                    "provider": "duckduckgo",
                    "error": True,
                    "message": search_result.get(
                        "message",
                        "DuckDuckGo search unavailable. Proceeding without web context."
                    ),
                    "fallback_used": True,
                }
            results = search_result.get("results", [])
            message = search_result.get("message", "DuckDuckGo results")
        else:
            results = search_result or []
            message = "DuckDuckGo results"
        return {
            "query": body.query,
            "summary": "",
            "citations": [],
            "results": results,
            "model": "duckduckgo",
            "provider": "duckduckgo",
            "error": False,
            "message": message,
            "fallback_used": True,
        }

    try:
        models = get_perplexity_models()
        result = await perplexity_search(
            query=body.query,
            api_key=api_key,
            model=models["search"],
            num_results=body.num_results,
            deep_search=False
        )
        return {
            "query": body.query,
            "summary": result.get("summary", ""),
            "citations": result.get("citations", []),
            "results": result.get("results", []),
            "model": models["search"],
            "provider": "perplexity",
            "error": False,
            "message": "Perplexity search results",
            "fallback_used": False
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Perplexity search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post(
    "/tools/fetch",
    tags=["tools"],
    summary="Fetch URL Content",
    response_description="Fetched URL content"
)
async def tool_fetch(url: str):
    """
    Fetch and extract content from a URL.

    Retrieves the content from the specified URL and extracts readable text.
    Useful for providing web page content to the council for analysis.
    The web search feature must be enabled.

    Args:
        url: The URL to fetch content from

    Returns:
        dict: Fetched content containing:
            - url: The original URL
            - content: Extracted text content from the page

    Raises:
        HTTPException 403: If web fetch feature is disabled
    """
    features = get_enhanced_features()
    if not features.get("web_search"):
        raise HTTPException(status_code=403, detail="Web fetch is disabled")

    content = await fetch_url(url)
    return {"url": url, "content": content}


@router.post(
    "/tools/execute",
    tags=["tools"],
    summary="Execute Code",
    response_description="Code execution results"
)
async def tool_execute(request: CodeRequest):
    """
    Execute code in a sandboxed environment.

    Executes Python or JavaScript code and returns the output.
    The code execution feature must be enabled in enhanced features.

    Supported Languages:
    - python: Execute Python 3 code
    - javascript: Execute JavaScript (Node.js) code

    Args:
        request: CodeRequest containing:
            - code: The code to execute
            - language: "python" or "javascript"
            - timeout: Maximum execution time in seconds (optional)

    Returns:
        dict: Execution results containing:
            - language: The language used
            - output: Standard output from execution
            - error: Any error messages (if execution failed)
            - execution_time: Time taken to execute

    Raises:
        HTTPException 403: If code execution feature is disabled
        HTTPException 400: If language is not supported

    Warning:
        Code is executed in a sandboxed environment but users should
        still exercise caution with untrusted code.
    """
    features = get_enhanced_features()
    if not features.get("code_execution"):
        raise HTTPException(status_code=403, detail="Code execution is disabled")

    if request.language == "python":
        result = execute_python(request.code, request.timeout)
    elif request.language == "javascript":
        result = execute_javascript(request.code, request.timeout)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")

    return {"language": request.language, **result}


@router.post(
    "/tools/memory",
    tags=["tools"],
    summary="Memory Operations",
    response_description="Memory operation results"
)
async def tool_memory(request: MemoryRequest):
    """
    Perform memory operations for persistent knowledge storage.

    The memory system allows storing facts, decisions, and preferences
    that persist across conversations. The memory feature must be enabled.

    Supported Actions:
    - remember_fact: Store a fact with optional category
    - remember_decision: Store a decision with question, answer, and reasoning
    - set_preference: Store a key-value preference
    - get_context: Retrieve relevant context based on query
    - clear: Clear all stored memory
    - stats: Get memory statistics

    Args:
        request: MemoryRequest containing:
            - action: One of the supported actions above
            - content: Fact content (for remember_fact/get_context)
            - category: Category for facts (default: "general")
            - question: Question (for remember_decision)
            - decision: Decision made (for remember_decision)
            - reasoning: Reasoning behind decision (for remember_decision)
            - key: Preference key (for set_preference)
            - value: Preference value (for set_preference)

    Returns:
        dict: Operation result containing:
            - success: Boolean indicating success (for write operations)
            - action: The action that was performed
            - context: Retrieved context (for get_context)
            - stats: Memory statistics (for stats action)

    Raises:
        HTTPException 403: If memory feature is disabled
        HTTPException 400: If required fields are missing or action unknown
    """
    features = get_enhanced_features()
    if not features.get("memory"):
        raise HTTPException(status_code=403, detail="Memory is disabled")

    if request.action == "remember_fact":
        if not request.content:
            raise HTTPException(status_code=400, detail="Content required")
        success = remember_fact(request.content, request.category or "general")
        return {"success": success, "action": "remember_fact"}

    elif request.action == "remember_decision":
        if not request.question or not request.decision:
            raise HTTPException(status_code=400, detail="Question and decision required")
        success = remember_decision(request.question, request.decision, request.reasoning or "")
        return {"success": success, "action": "remember_decision"}

    elif request.action == "set_preference":
        if not request.key:
            raise HTTPException(status_code=400, detail="Key required")
        success = set_preference(request.key, request.value)
        return {"success": success, "action": "set_preference"}

    elif request.action == "get_context":
        context = get_memory_context(request.content or "", 10)
        return {"context": context, "action": "get_context"}

    elif request.action == "clear":
        success = clear_memory()
        return {"success": success, "action": "clear"}

    elif request.action == "stats":
        stats = get_memory_stats()
        return {"stats": stats, "action": "stats"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")


# ──────────────────────────────────────────────
# Search endpoints
# ──────────────────────────────────────────────

@router.get(
    "/search",
    tags=["search"],
    summary="Search Conversations",
    response_description="Search results with matching conversations"
)
@limiter.limit(RATE_LIMITS["search"])
async def search_endpoint(
    request: Request,
    q: str,
    folder: Optional[str] = None,
    tags: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Search across all conversations.

    Performs full-text search across conversation content with optional
    filtering by folder, tags, and date range.

    Args:
        q: Search query string
        folder: Filter by folder/project ID (optional)
        tags: Comma-separated tags to filter by (optional)
        from_date: Filter conversations created after this date (ISO format)
        to_date: Filter conversations created before this date (ISO format)
        limit: Maximum number of results (default: 50)
        offset: Pagination offset (default: 0)

    Returns:
        dict: Search results containing:
            - results: List of matching conversations with highlights
            - total: Total number of matches
            - query: Original search query
    """
    # Parse tags if provided
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]

    results = search.search_conversations(
        query=q,
        folder=folder,
        tags=tag_list,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset
    )

    return results


@router.get(
    "/search/suggestions",
    tags=["search"],
    summary="Search Suggestions",
    response_description="Autocomplete suggestions for search"
)
async def search_suggestions(q: str, limit: int = 5):
    """
    Get search suggestions based on query prefix.

    Provides autocomplete suggestions for the search box based on
    previous search terms and conversation content.

    Args:
        q: Partial search query
        limit: Maximum number of suggestions (default: 5)

    Returns:
        dict: Suggestions containing:
            - suggestions: List of suggested search terms
    """
    suggestions = search.get_search_suggestions(q, limit)
    return {"suggestions": suggestions}
