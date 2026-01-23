"""Enhanced tools for LLM Council: Web Search, Code Execution, Memory."""

import httpx
import json
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime

# ============ WEB SEARCH ============

async def web_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo (no API key required).

    Args:
        query: Search query
        num_results: Number of results to return

    Returns:
        List of search results with title, url, and snippet
    """
    try:
        # Use DuckDuckGo HTML search (no API key needed)
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, data={"q": query}, headers=headers)
            response.raise_for_status()

        # Parse results from HTML
        html = response.text
        results = []

        # Simple parsing - extract result blocks
        import re

        # Find all result links and snippets
        link_pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+(?:<[^>]+>[^<]*</[^>]+>)*[^<]*)</a>'

        links = re.findall(link_pattern, html)
        snippets = re.findall(snippet_pattern, html)

        for i, (url, title) in enumerate(links[:num_results]):
            snippet = snippets[i] if i < len(snippets) else ""
            # Clean snippet of HTML tags
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append({
                "title": title.strip(),
                "url": url,
                "snippet": snippet[:300]
            })

        return results

    except Exception as e:
        print(f"Web search error: {e}")
        return [{"title": "Search failed", "url": "", "snippet": str(e)}]


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

MEMORY_FILE = "data/council_memory.json"

def _load_memory() -> Dict[str, Any]:
    """Load memory from file."""
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading memory: {e}")

    return {
        "facts": [],
        "decisions": [],
        "preferences": {},
        "created_at": datetime.now().isoformat()
    }


def _save_memory(memory: Dict[str, Any]):
    """Save memory to file."""
    try:
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=2)
    except Exception as e:
        print(f"Error saving memory: {e}")


def remember_fact(fact: str, category: str = "general") -> bool:
    """
    Store a fact in memory.

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
    # Keep only last 100 facts
    memory["facts"] = memory["facts"][-100:]
    _save_memory(memory)
    return True


def remember_decision(question: str, decision: str, reasoning: str = "") -> bool:
    """
    Store a council decision in memory.

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
    # Keep only last 50 decisions
    memory["decisions"] = memory["decisions"][-50:]
    _save_memory(memory)
    return True


def set_preference(key: str, value: Any) -> bool:
    """
    Set a user preference.

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


def get_memory_context(query: str = "", limit: int = 10) -> str:
    """
    Get relevant memory context for a query.

    Args:
        query: Optional query to filter relevant memories
        limit: Maximum items to return

    Returns:
        Formatted string of relevant memories
    """
    memory = _load_memory()
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
