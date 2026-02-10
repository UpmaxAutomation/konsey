"""Enhanced tools for LLM Council: Web Search, Code Execution, Memory."""

import httpx
import json
import os
import subprocess
import tempfile
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .config import PERPLEXITY_API_URL

logger = logging.getLogger(__name__)

# ============ RATE LIMITING ============

# Per-user rate limiting: {user_id: [timestamps]}
# "anonymous" is used for unauthenticated users
_search_timestamps: Dict[str, List[datetime]] = {}
SEARCH_RATE_LIMIT = 10  # Maximum searches per minute per user


def check_rate_limit(user_id: Optional[str] = None) -> bool:
    """
    Check if a search request is within rate limits for a specific user.

    Args:
        user_id: User identifier (str(uuid) or "anonymous" for unauthenticated)

    Returns:
        True if request is allowed, False if rate limited
    """
    global _search_timestamps
    user_key = str(user_id) if user_id else "anonymous"
    now = datetime.now()

    # Initialize list for new users
    if user_key not in _search_timestamps:
        _search_timestamps[user_key] = []

    # Remove timestamps older than 1 minute
    _search_timestamps[user_key] = [
        t for t in _search_timestamps[user_key] if now - t < timedelta(minutes=1)
    ]

    if len(_search_timestamps[user_key]) >= SEARCH_RATE_LIMIT:
        return False

    _search_timestamps[user_key].append(now)
    return True


def get_rate_limit_status(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get current rate limit status for a specific user."""
    user_key = str(user_id) if user_id else "anonymous"
    now = datetime.now()

    if user_key not in _search_timestamps:
        recent = []
    else:
        recent = [t for t in _search_timestamps[user_key] if now - t < timedelta(minutes=1)]

    return {
        "requests_in_window": len(recent),
        "limit": SEARCH_RATE_LIMIT,
        "remaining": max(0, SEARCH_RATE_LIMIT - len(recent)),
        "user": user_key
    }

# ============ WEB SEARCH ============

async def _duckduckgo_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Internal DuckDuckGo search implementation.

    Args:
        query: Search query
        num_results: Number of results to return

    Returns:
        List of search results with title, url, and snippet

    Raises:
        httpx.TimeoutException: If request times out
        httpx.HTTPStatusError: If HTTP error occurs
        Exception: For other errors
    """
    import re

    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, data={"q": query}, headers=headers)
        response.raise_for_status()

    html = response.text
    results = []

    # Multiple parsing strategies for robustness

    # Strategy 1: Standard result link pattern
    link_pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
    snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+(?:<[^>]+>[^<]*</[^>]+>)*[^<]*)</a>'

    links = re.findall(link_pattern, html)
    snippets = re.findall(snippet_pattern, html)

    # Strategy 2: Fallback pattern if first fails
    if not links:
        # Try alternate pattern for results
        alt_link_pattern = r'<a[^>]*class="[^"]*result[^"]*"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
        links = re.findall(alt_link_pattern, html)

    for i, (result_url, title) in enumerate(links[:num_results]):
        snippet = snippets[i] if i < len(snippets) else ""
        # Clean snippet of HTML tags
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()
        results.append({
            "title": title.strip(),
            "url": result_url,
            "snippet": snippet[:300]
        })

    return results


async def _search_with_retry(
    search_fn,
    query: str,
    num_results: int = 5,
    max_retries: int = 3
) -> List[Dict[str, str]]:
    """
    Execute search with exponential backoff retry.

    Args:
        search_fn: Async search function to call
        query: Search query
        num_results: Number of results
        max_retries: Maximum retry attempts

    Returns:
        Search results list

    Raises:
        Exception: If all retries fail
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return await search_fn(query, num_results)
        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Search attempt {attempt + 1} timed out, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Search attempt {attempt + 1} failed: {e}, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise
    raise last_error


async def web_search(query: str, num_results: int = 5, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo with error handling and per-user rate limiting.

    Args:
        query: Search query
        num_results: Number of results to return
        user_id: User identifier for rate limiting (None for anonymous)

    Returns:
        Dict with keys:
        - error: bool - Whether an error occurred
        - results: List[Dict] - Search results (if successful)
        - message: str - Status or error message
    """
    # Check per-user rate limit
    if not check_rate_limit(user_id):
        logger.warning(f"Search rate limited for user {user_id}, query: {query[:50]}...")
        return {
            "error": True,
            "results": [],
            "message": "Rate limited. Please wait a moment before searching again."
        }

    try:
        results = await _search_with_retry(_duckduckgo_search, query, num_results)

        if not results:
            logger.info(f"No results found for query: {query[:50]}...")
            return {
                "error": False,
                "results": [],
                "message": "No results found for your query."
            }

        logger.info(f"Web search successful: {len(results)} results for '{query[:50]}...'")
        return {
            "error": False,
            "results": results,
            "message": f"Found {len(results)} results"
        }

    except httpx.TimeoutException:
        logger.error(f"Search timed out for query: {query[:50]}...")
        return {
            "error": True,
            "results": [],
            "message": "Search timed out. Please try again."
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"Search HTTP error {e.response.status_code} for query: {query[:50]}...")
        return {
            "error": True,
            "results": [],
            "message": f"Search service unavailable (HTTP {e.response.status_code}). Please try again later."
        }
    except Exception as e:
        logger.error(f"Search failed for query '{query[:50]}...': {e}")
        return {
            "error": True,
            "results": [],
            "message": "Search unavailable. Proceeding without web context."
        }


async def web_search_with_fallback(
    query: str,
    num_results: int = 5,
    perplexity_api_key: Optional[str] = None,
    perplexity_model: str = "sonar",
    use_deep: bool = False
) -> Dict[str, Any]:
    """
    Search the web with Perplexity fallback if DuckDuckGo fails.

    Args:
        query: Search query
        num_results: Number of results to return
        perplexity_api_key: Optional Perplexity API key for fallback
        perplexity_model: Perplexity model to use (default: sonar)
        use_deep: Whether to use deep research model

    Returns:
        Dict with error status, results, and message
    """
    # Try DuckDuckGo first
    result = await web_search(query, num_results)

    # If DuckDuckGo succeeded, return the result
    if not result.get("error"):
        return result

    # If we have a Perplexity key, try fallback
    if perplexity_api_key:
        logger.info(f"DuckDuckGo failed, falling back to Perplexity for query: {query[:50]}...")
        try:
            perplexity_result = await perplexity_search(
                query=query,
                api_key=perplexity_api_key,
                model=perplexity_model,
                num_results=num_results,
                deep_search=use_deep
            )
            return {
                "error": False,
                "results": perplexity_result.get("results", []),
                "message": f"Found {len(perplexity_result.get('results', []))} results via Perplexity",
                "summary": perplexity_result.get("summary", ""),
                "citations": perplexity_result.get("citations", []),
                "fallback_used": True
            }
        except Exception as e:
            logger.error(f"Perplexity fallback also failed: {e}")
            return {
                "error": True,
                "results": [],
                "message": "Both search services unavailable. Proceeding without web context."
            }

    # No Perplexity key, return the original DuckDuckGo error
    return result


async def fetch_url(url: str) -> str:
    """
    Fetch content from a URL.

    Args:
        url: URL to fetch

    Returns:
        Text content of the page (simplified)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        # Basic HTML to text conversion
        import re
        text = response.text

        # Remove script and style elements
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Limit length
        return text[:5000]

    except Exception as e:
        return f"Error fetching URL: {e}"


def _extract_json_payload(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON object from model output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None


async def perplexity_search(
    query: str,
    api_key: str,
    model: str,
    num_results: int = 5,
    deep_search: bool = False,
    timeout: float = 60.0
) -> Dict[str, Any]:
    """
    Query Perplexity for web-grounded search results.

    Perplexity's sonar models automatically search the web and include citations.
    This function extracts the response and citations from their API.

    Args:
        query: Search query
        api_key: Perplexity API key
        model: Perplexity model ID (e.g., "sonar", "sonar-pro", "sonar-deep-research")
        num_results: Number of citations to include
        deep_search: Whether using deep research model (affects timeout)
        timeout: Request timeout in seconds

    Returns:
        Dict with keys: results (list), summary (str), citations (list)
    """
    import logging
    logger = logging.getLogger(__name__)

    if not api_key:
        raise ValueError("Perplexity API key is required.")

    # Perplexity models are web-grounded by default - just ask the question
    system_prompt = (
        "You are a helpful research assistant. Provide accurate, well-sourced information. "
        "Be concise but thorough. Include specific facts and data when available."
    )

    # Use longer timeout for deep research (can take 2-3 minutes)
    actual_timeout = timeout if not deep_search else max(timeout, 180.0)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        "temperature": 0.2,
        "return_citations": True,  # Request citations in response
        "return_related_questions": False
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    logger.info(f"Perplexity search: model={model}, query={query[:100]}...")

    try:
        # Explicit timeout configuration for long-running deep research
        timeout_config = httpx.Timeout(
            connect=30.0,  # 30s to connect
            read=actual_timeout,  # full timeout for reading response
            write=30.0,  # 30s to write request
            pool=30.0  # 30s to acquire connection from pool
        )
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(PERPLEXITY_API_URL, json=payload, headers=headers)

            if response.status_code == 401:
                logger.error("Perplexity API key is invalid")
                raise ValueError("Invalid Perplexity API key")

            if response.status_code == 429:
                logger.warning("Perplexity rate limit exceeded")
                raise ValueError("Perplexity rate limit exceeded")

            response.raise_for_status()
            data = response.json()

        # Extract content from response
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        # Citations are returned at the top level by Perplexity
        citations = data.get("citations") or []

        logger.info(f"Perplexity response: {len(content)} chars, {len(citations)} citations")

        # Build results from citations
        results = []
        for i, url in enumerate(citations[:num_results]):
            results.append({
                "title": f"Source {i + 1}",
                "url": url,
                "snippet": ""
            })

        return {
            "results": results,
            "summary": content,  # The full response IS the summary
            "citations": citations
        }

    except httpx.TimeoutException:
        logger.error(f"Perplexity request timed out after {actual_timeout}s")
        raise ValueError(f"Perplexity request timed out after {actual_timeout}s")
    except httpx.HTTPStatusError as e:
        logger.error(f"Perplexity HTTP error: {e.response.status_code}")
        raise ValueError(f"Perplexity API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Perplexity search failed: {e}")
        raise


# ============ CODE EXECUTION ============

def execute_python(code: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute Python code in a sandboxed environment.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds

    Returns:
        Dict with stdout, stderr, return_code, and execution_time
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        start_time = datetime.now()

        # Execute with timeout
        result = subprocess.run(
            ['python3', temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir()
        )

        execution_time = (datetime.now() - start_time).total_seconds()

        # Clean up
        os.unlink(temp_file)

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:5000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
            "return_code": result.returncode,
            "execution_time": round(execution_time, 3)
        }

    except subprocess.TimeoutExpired:
        if 'temp_file' in locals():
            os.unlink(temp_file)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds",
            "return_code": -1,
            "execution_time": timeout
        }
    except Exception as e:
        if 'temp_file' in locals():
            os.unlink(temp_file)
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "return_code": -1,
            "execution_time": 0
        }


def execute_javascript(code: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute JavaScript code using Node.js.

    Args:
        code: JavaScript code to execute
        timeout: Maximum execution time in seconds

    Returns:
        Dict with stdout, stderr, return_code, and execution_time
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name

        start_time = datetime.now()

        # Execute with timeout
        result = subprocess.run(
            ['node', temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir()
        )

        execution_time = (datetime.now() - start_time).total_seconds()

        # Clean up
        os.unlink(temp_file)

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:5000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
            "return_code": result.returncode,
            "execution_time": round(execution_time, 3)
        }

    except subprocess.TimeoutExpired:
        if 'temp_file' in locals():
            os.unlink(temp_file)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds",
            "return_code": -1,
            "execution_time": timeout
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Node.js not found. Please install Node.js.",
            "return_code": -1,
            "execution_time": 0
        }
    except Exception as e:
        if 'temp_file' in locals():
            os.unlink(temp_file)
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "return_code": -1,
            "execution_time": 0
        }


# ============ MEMORY / CONTEXT ============

# Legacy file-based storage for anonymous users
MEMORY_FILE = "data/council_memory.json"


def _get_memory_file(user_id: Optional[str] = None) -> str:
    """Get memory file path - per-user file for identified users, shared file for anonymous."""
    if user_id and user_id != "anonymous":
        return f"data/memory_{user_id}.json"
    return MEMORY_FILE


def _load_memory(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Load memory from file (for anonymous/legacy use)."""
    memory_file = _get_memory_file(user_id)
    try:
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading memory: {e}")

    return {
        "facts": [],
        "decisions": [],
        "preferences": {},
        "created_at": datetime.now().isoformat()
    }


def _save_memory(memory: Dict[str, Any], user_id: Optional[str] = None):
    """Save memory to file (for anonymous/legacy use)."""
    memory_file = _get_memory_file(user_id)
    try:
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        with open(memory_file, 'w') as f:
            json.dump(memory, f, indent=2)
    except Exception as e:
        print(f"Error saving memory: {e}")


async def remember_fact_async(fact: str, category: str = "general", user_id: Optional[str] = None, db=None) -> bool:
    """
    Store a fact in memory (async, uses database for authenticated users).

    Args:
        fact: The fact to remember
        category: Category for organization
        user_id: User ID (uses database if provided with db)
        db: Database session

    Returns:
        True if successful
    """
    if user_id and db and user_id != "anonymous":
        try:
            from .database import crud as db_crud
            import uuid as uuid_module
            await db_crud.memory.add_fact(db, uuid_module.UUID(user_id), fact, category)
            return True
        except Exception as e:
            logger.warning(f"Failed to save fact to database: {e}")
            # Fall through to file-based

    # File-based fallback for anonymous users
    memory = _load_memory(user_id)
    memory["facts"].append({
        "content": fact,
        "category": category,
        "timestamp": datetime.now().isoformat()
    })
    memory["facts"] = memory["facts"][-100:]
    _save_memory(memory, user_id)
    return True


def remember_fact(fact: str, category: str = "general") -> bool:
    """
    Store a fact in memory (sync, for anonymous users).

    Args:
        fact: The fact to remember
        category: Category for organization

    Returns:
        True if successful
    """
    memory = _load_memory()
    memory["facts"].append({
        "content": fact,
        "category": category,
        "timestamp": datetime.now().isoformat()
    })
    memory["facts"] = memory["facts"][-100:]
    _save_memory(memory)
    return True


async def remember_decision_async(question: str, decision: str, reasoning: str = "", user_id: Optional[str] = None, db=None) -> bool:
    """
    Store a council decision in memory (async, uses database for authenticated users).

    Args:
        question: The original question
        decision: The council's decision/answer
        reasoning: Optional reasoning behind the decision
        user_id: User ID (uses database if provided with db)
        db: Database session

    Returns:
        True if successful
    """
    if user_id and db and user_id != "anonymous":
        try:
            from .database import crud as db_crud
            import uuid as uuid_module
            await db_crud.memory.add_decision(db, uuid_module.UUID(user_id), question, decision, reasoning)
            return True
        except Exception as e:
            logger.warning(f"Failed to save decision to database: {e}")

    # File-based fallback
    memory = _load_memory(user_id)
    memory["decisions"].append({
        "question": question[:500],
        "decision": decision[:2000],
        "reasoning": reasoning[:1000],
        "timestamp": datetime.now().isoformat()
    })
    memory["decisions"] = memory["decisions"][-50:]
    _save_memory(memory, user_id)
    return True


def remember_decision(question: str, decision: str, reasoning: str = "") -> bool:
    """
    Store a council decision in memory (sync, for anonymous users).

    Args:
        question: The original question
        decision: The council's decision/answer
        reasoning: Optional reasoning behind the decision

    Returns:
        True if successful
    """
    memory = _load_memory()
    memory["decisions"].append({
        "question": question[:500],
        "decision": decision[:2000],
        "reasoning": reasoning[:1000],
        "timestamp": datetime.now().isoformat()
    })
    memory["decisions"] = memory["decisions"][-50:]
    _save_memory(memory)
    return True


async def set_preference_async(key: str, value: Any, user_id: Optional[str] = None, db=None) -> bool:
    """
    Set a user preference (async, uses database for authenticated users).

    Args:
        key: Preference key
        value: Preference value
        user_id: User ID (uses database if provided with db)
        db: Database session

    Returns:
        True if successful
    """
    if user_id and db and user_id != "anonymous":
        try:
            from .database import crud as db_crud
            import uuid as uuid_module
            await db_crud.memory.set_preference(db, uuid_module.UUID(user_id), key, value)
            return True
        except Exception as e:
            logger.warning(f"Failed to save preference to database: {e}")

    # File-based fallback
    memory = _load_memory(user_id)
    memory["preferences"][key] = {
        "value": value,
        "updated_at": datetime.now().isoformat()
    }
    _save_memory(memory, user_id)
    return True


def set_preference(key: str, value: Any) -> bool:
    """
    Set a user preference (sync, for anonymous users).

    Args:
        key: Preference key
        value: Preference value

    Returns:
        True if successful
    """
    memory = _load_memory()
    memory["preferences"][key] = {
        "value": value,
        "updated_at": datetime.now().isoformat()
    }
    _save_memory(memory)
    return True


async def get_memory_context_async(query: str = "", limit: int = 10, user_id: Optional[str] = None, db=None) -> str:
    """
    Get relevant memory context for a query (async, uses database for authenticated users).

    Args:
        query: Optional query to filter relevant memories
        limit: Maximum items to return
        user_id: User ID (uses database if provided with db)
        db: Database session

    Returns:
        Formatted string of relevant memories
    """
    if user_id and db and user_id != "anonymous":
        try:
            from .database import crud as db_crud
            import uuid as uuid_module
            return await db_crud.memory.get_memory_context(db, uuid_module.UUID(user_id), limit)
        except Exception as e:
            logger.warning(f"Failed to get memory from database: {e}")

    # File-based fallback
    return get_memory_context(query, limit, user_id)


def get_memory_context(query: str = "", limit: int = 10, user_id: Optional[str] = None) -> str:
    """
    Get relevant memory context for a query (sync, file-based).

    Args:
        query: Optional query to filter relevant memories
        limit: Maximum items to return
        user_id: User ID for file isolation

    Returns:
        Formatted string of relevant memories
    """
    memory = _load_memory(user_id)
    context_parts = []

    # Add recent facts
    if memory.get("facts"):
        recent_facts = memory["facts"][-limit:]
        if recent_facts:
            context_parts.append("**Remembered Facts:**")
            for fact in recent_facts:
                context_parts.append(f"- [{fact.get('category', 'general')}] {fact['content']}")

    # Add recent decisions
    if memory.get("decisions"):
        recent_decisions = memory["decisions"][-5:]
        if recent_decisions:
            context_parts.append("\n**Previous Council Decisions:**")
            for dec in recent_decisions:
                context_parts.append(f"- Q: {dec['question'][:100]}...")
                context_parts.append(f"  A: {dec['decision'][:200]}...")

    # Add preferences
    if memory.get("preferences"):
        context_parts.append("\n**User Preferences:**")
        for key, pref in memory["preferences"].items():
            context_parts.append(f"- {key}: {pref['value']}")

    return "\n".join(context_parts) if context_parts else "No memories stored yet."


def clear_memory() -> bool:
    """Clear all memory."""
    _save_memory({
        "facts": [],
        "decisions": [],
        "preferences": {},
        "created_at": datetime.now().isoformat()
    })
    return True


def get_memory_stats() -> Dict[str, Any]:
    """Get memory statistics."""
    memory = _load_memory()
    return {
        "facts_count": len(memory.get("facts", [])),
        "decisions_count": len(memory.get("decisions", [])),
        "preferences_count": len(memory.get("preferences", {})),
        "created_at": memory.get("created_at"),
        "memory_file": MEMORY_FILE
    }
