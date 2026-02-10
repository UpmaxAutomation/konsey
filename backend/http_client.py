"""
Shared HTTP client for LLM API calls.

Using a shared client provides significant performance benefits:
- Connection reuse (HTTP/2 multiplexing)
- DNS caching
- Reduced handshake overhead
- Better connection pooling
"""

import httpx
from typing import Optional
from contextlib import asynccontextmanager

# Default timeouts
DEFAULT_TIMEOUT = 60.0
STREAMING_TIMEOUT = 120.0
REASONING_TIMEOUT = 180.0

# Global client instance - initialized lazily
_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    """Get the shared HTTP client, creating it if needed."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(DEFAULT_TIMEOUT, connect=10.0),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
            http2=True,  # Enable HTTP/2 for better multiplexing
            default_encoding="utf-8",  # Ensure UTF-8 for Unicode support
        )
    return _client


async def close_client():
    """Close the shared client (call on shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


@asynccontextmanager
async def get_client_with_timeout(timeout: float = DEFAULT_TIMEOUT):
    """
    Get client with custom timeout for specific request.

    Usage:
        async with get_client_with_timeout(120.0) as client:
            response = await client.post(...)
    """
    client = get_client()
    # Create a new client with different timeout for this request
    # This is still efficient because we reuse connections
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=10.0),
        limits=client._limits,
        http2=True,
    ) as temp_client:
        yield temp_client


# Convenience functions for common operations

async def post_json(
    url: str,
    json: dict,
    headers: dict,
    timeout: float = DEFAULT_TIMEOUT,
) -> httpx.Response:
    """POST JSON data to URL."""
    client = get_client()
    return await client.post(
        url,
        json=json,
        headers=headers,
        timeout=timeout,
    )


async def post_stream(
    url: str,
    json: dict,
    headers: dict,
    timeout: float = STREAMING_TIMEOUT,
):
    """POST and stream response."""
    client = get_client()
    async with client.stream(
        "POST",
        url,
        json=json,
        headers=headers,
        timeout=timeout,
    ) as response:
        async for line in response.aiter_lines():
            yield line
