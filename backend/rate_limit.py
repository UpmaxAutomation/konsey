"""Rate limiting configuration for LLM Council API."""

import os
from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse


def get_identifier(request: Request) -> str:
    """
    Get rate limit identifier.
    Uses user ID if authenticated, otherwise IP address.
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Fall back to IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    return f"ip:{request.client.host if request.client else 'unknown'}"


# Get Redis URL or use in-memory storage
REDIS_URL = os.getenv("REDIS_URL")

# Configure limiter
limiter = Limiter(
    key_func=get_identifier,
    storage_uri=REDIS_URL,  # Uses memory if None
    strategy="fixed-window",
    default_limits=["100/minute"],
)

# Rate limit configurations by endpoint type
RATE_LIMITS = {
    "council_query": "10/minute",      # Council deliberation (expensive)
    "quick_mode": "30/minute",         # Single model queries
    "api_general": "100/minute",       # General API calls
    "auth": "5/minute",                # Auth endpoints (prevent brute force)
    "export": "20/minute",             # Export operations
    "batch": "5/hour",                 # Batch processing
    "image_gen": "10/minute",          # Image generation
    "voice": "20/minute",              # TTS/STT
    "search": "30/minute",             # Search operations
}


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60),
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
            "X-RateLimit-Limit": str(getattr(exc, "limit", "unknown")),
        },
    )


def setup_rate_limiting(app):
    """Configure rate limiting for FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    # Note: SlowAPIMiddleware is added separately if needed for global limiting
