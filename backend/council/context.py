"""Context gathering utilities for council queries."""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def format_web_context(
    results: List[Dict[str, Any]],
    summary: Optional[str] = None
) -> str:
    """Format web search results and summary for prompt context."""
    if not results and not summary:
        return ""

    lines = ["**Web Context (Citations):**"]
    for result in results:
        title = result.get("title", "").strip()
        url = result.get("url", "").strip()
        snippet = result.get("snippet", "").strip()
        if title and url:
            lines.append(f"- {title} ({url}): {snippet}")
        elif url:
            lines.append(f"- {url}: {snippet}")
        elif title:
            lines.append(f"- {title}: {snippet}")
        else:
            lines.append(f"- {snippet}")

    if summary:
        lines.append("")
        lines.append("**Deep Search Summary:**")
        lines.append(summary.strip())

    return "\n".join(lines)


async def gather_context(
    user_query: str,
    web_search: Optional[bool] = None,
    deep_search: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Gather additional context using enhanced features (web search, memory, etc.)

    Args:
        user_query: The user's question
        web_search: Enable web search
        deep_search: Enable deep search (Perplexity)

    Returns:
        Dict with context from various sources
    """
    from ..config import get_enhanced_features, get_perplexity_api_key, get_perplexity_models
    from ..tools import web_search as do_web_search, perplexity_search, get_memory_context

    features = get_enhanced_features()
    if web_search is not None:
        features["web_search"] = web_search
    if deep_search is not None:
        features["deep_search"] = deep_search
    context = {}

    # Web search for current information
    use_web_search = bool(features.get("web_search"))
    use_deep_search = bool(features.get("deep_search"))
    if use_web_search or use_deep_search:
        try:
            perplexity_key = get_perplexity_api_key()
            if perplexity_key:
                models = get_perplexity_models()
                model = models["deep_search"] if use_deep_search else models["search"]
                logger.info(f"Using Perplexity search: model={model}, deep_search={use_deep_search}")
                search_payload = await perplexity_search(
                    user_query,
                    api_key=perplexity_key,
                    model=model,
                    num_results=3,
                    deep_search=use_deep_search
                )
                if search_payload.get("results"):
                    context["web_search"] = search_payload["results"]
                if search_payload.get("summary"):
                    context["web_search_summary"] = search_payload["summary"]
                if search_payload.get("citations"):
                    context["web_search_citations"] = search_payload["citations"]
                logger.info(f"Perplexity search completed: {len(context.get('web_search', []))} results")
            elif use_web_search:
                logger.info("No Perplexity key, falling back to DuckDuckGo search")
                search_result = await do_web_search(user_query, num_results=3)
                # Handle new Dict response format
                if isinstance(search_result, dict):
                    if search_result.get("error"):
                        logger.warning(f"Web search error: {search_result.get('message', 'Unknown error')}")
                        context["web_search_error"] = search_result.get("message", "Search failed")
                    elif search_result.get("results"):
                        context["web_search"] = search_result["results"]
                        logger.info(f"DuckDuckGo search completed: {len(search_result['results'])} results")
                # Handle legacy List response format for backward compatibility
                elif isinstance(search_result, list) and search_result and search_result[0].get("url"):
                    context["web_search"] = search_result
            else:
                logger.warning("Deep search requested but no Perplexity API key configured")
        except Exception as e:
            logger.error(f"Web search failed: {e}", exc_info=True)

    # Memory context
    if features.get("memory"):
        try:
            memory_context = get_memory_context(user_query, limit=5)
            if memory_context and memory_context != "No memories stored yet.":
                context["memory"] = memory_context
        except Exception as e:
            print(f"Memory retrieval failed: {e}")

    return context
