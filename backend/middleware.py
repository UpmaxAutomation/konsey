"""FastAPI middleware for request logging and context."""

import uuid
import time
import json
from pathlib import Path
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import get_logger, bind_request_context, clear_request_context

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests with timing and context."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])

        # Get client IP (handle proxies)
        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Bind context for this request
        bind_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
        )

        # Log request start for non-health endpoints
        if request.url.path not in ["/", "/health", "/metrics"]:
            logger.info(
                "request_started",
                query_params=str(request.query_params) if request.query_params else None,
            )

        start_time = time.perf_counter()
        # #region agent log
        # Log CORS-related requests for debugging
        if request.url.path.startswith("/api/") and request.method in {"POST", "OPTIONS", "GET"}:
            try:
                import os
                debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
                if os.path.exists(os.path.dirname(debug_log_path)):
                    origin = request.headers.get("origin")
                    cors_origins_env = os.getenv("CORS_ORIGINS", "")
                    Path(debug_log_path).open("a").write(
                        json.dumps(
                            {
                                "sessionId": "debug-session",
                                "runId": "cors-investigation",
                                "hypothesisId": "H1",
                                "location": "middleware.py:18",
                                "message": "cors_request:entry",
                                "data": {
                                    "method": request.method,
                                    "path": request.url.path,
                                    "origin": origin,
                                    "cors_origins_env": cors_origins_env,
                                    "user_agent": request.headers.get("user-agent", "")[:50],
                                },
                                "timestamp": int(time.time() * 1000),
                            }
                        )
                        + "\n"
                    )
            except Exception:
                pass
        # #endregion

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request completion for non-health endpoints
            if request.url.path not in ["/", "/health", "/metrics"]:
                logger.info(
                    "request_completed",
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )

            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            # #region agent log
            # Log CORS response headers for debugging
            if request.url.path.startswith("/api/") and request.method in {"POST", "OPTIONS", "GET"}:
                try:
                    import os
                    debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
                    if os.path.exists(os.path.dirname(debug_log_path)):
                        cors_origin = response.headers.get("access-control-allow-origin", "NOT_SET")
                        cors_headers = {k: v for k, v in response.headers.items() if "access-control" in k.lower()}
                        Path(debug_log_path).open("a").write(
                            json.dumps(
                                {
                                    "sessionId": "debug-session",
                                    "runId": "cors-investigation",
                                    "hypothesisId": "H2",
                                    "location": "middleware.py:112",
                                    "message": "cors_request:response",
                                    "data": {
                                        "method": request.method,
                                        "path": request.url.path,
                                        "status": response.status_code,
                                        "cors_allow_origin": cors_origin,
                                        "all_cors_headers": cors_headers,
                                        "request_origin": request.headers.get("origin"),
                                    },
                                    "timestamp": int(time.time() * 1000),
                                }
                            )
                            + "\n"
                        )
                except Exception:
                    pass
            # #endregion

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
            )
            raise
        finally:
            clear_request_context()


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log unhandled errors."""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(
                "unhandled_error",
                path=request.url.path,
                method=request.method,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
