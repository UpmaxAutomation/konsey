"""FastAPI backend for LLM Council."""

# Ensure UTF-8 encoding for all I/O operations (prevents 'ascii' codec errors)
import sys
import io
# Reconfigure stdout/stderr to use UTF-8 (handles Unicode like \u2028)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
else:
    # Fallback for older Python versions
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

import json
import asyncio
from typing import Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .config import AVAILABLE_MODELS
from .model_sync import get_available_models
from .database.connection import init_db

# Logging and middleware
from .logging_config import setup_logging, get_logger
from .middleware import RequestLoggingMiddleware
from .rate_limit import setup_rate_limiting

# Route imports
from .routes import (
    auth_router,
    boards_router,
    conversations_router,
    council_router,
    projects_router,
    config_router,
    api_keys_router,
    analytics_router,
    files_router,
    tools_router,
    teams_router,
    integrations_router,
    features_router,
    misc_router,
    workflows_router,
    workflow_templates_router,
    agents_router,
)

# Setup structured logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

# Global variable to store dynamically fetched models
_dynamic_models = {}
_models_last_synced = None

# Store active streams for cancellation support
# Maps conversation_id -> asyncio.Event (set when cancellation requested)
_active_streams: Dict[str, asyncio.Event] = {}


def _json_sse(data: Any) -> str:
    """Serialize data to JSON for SSE, handling Unicode properly."""
    return json.dumps(data, ensure_ascii=False)


def get_all_models():
    """Get combined models (dynamic + fallback)."""
    # Merge dynamic models with hardcoded fallback
    combined = AVAILABLE_MODELS.copy()
    combined.update(_dynamic_models)
    return combined


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global _dynamic_models, _models_last_synced

    logger.info("startup", message="Initializing LLM Council API")

    # Startup: Initialize database and fetch models
    try:
        await init_db()
        logger.info("database_ready", message="Database tables initialized")
    except Exception as e:
        logger.error("database_error", error=str(e))

    try:
        _dynamic_models = await get_available_models()
        _models_last_synced = datetime.now().isoformat()
        logger.info("models_loaded", count=len(_dynamic_models), message="Loaded models from OpenRouter")
    except Exception as e:
        logger.warning("models_fallback", error=str(e), message="Using fallback models")
        _dynamic_models = AVAILABLE_MODELS.copy()

    yield  # Application runs here

    # Shutdown: cleanup
    logger.info("shutdown", message="Shutting down LLM Council API")

    # Close shared HTTP client
    from .http_client import close_client
    await close_client()
    logger.info("http_client_closed", message="Closed shared HTTP client")


# OpenAPI Tags for endpoint grouping
tags_metadata = [
    {"name": "health", "description": "Health check and status endpoints"},
    {"name": "config", "description": "Council configuration, presets, and model management"},
    {"name": "conversations", "description": "Manage conversations, messages, and the 3-stage council process"},
    {"name": "voting", "description": "Multi-model voting system for collective decision making"},
    {"name": "tools", "description": "Web search, code execution, and memory tools"},
    {"name": "analytics", "description": "Usage analytics, model performance metrics, and cost tracking"},
    {"name": "ratings", "description": "Model response rating and recommendation system"},
    {"name": "agents", "description": "AI agent tasks with autonomous tool execution"},
    {"name": "images", "description": "AI image generation (DALL-E, Stable Diffusion, FLUX)"},
    {"name": "voice", "description": "Text-to-speech and speech-to-text services"},
    {"name": "integrations", "description": "External service integrations (Google Drive, Slack, GitHub)"},
    {"name": "projects", "description": "Project workspaces with knowledge bases and custom configurations"},
    {"name": "files", "description": "File upload and management for conversations"},
    {"name": "templates", "description": "Prompt templates with variable substitution"},
    {"name": "batch", "description": "Batch processing for multiple queries"},
    {"name": "budget", "description": "Budget limits, spending tracking, and alerts"},
    {"name": "folders", "description": "Folder organization for conversations"},
    {"name": "tags", "description": "Tag management for conversation categorization"},
    {"name": "sharing", "description": "Conversation sharing and export"},
    {"name": "teams", "description": "Team workspaces and collaboration"},
    {"name": "personas", "description": "Model persona customization"},
    {"name": "routing", "description": "Intelligent model routing and recommendations"},
]

app = FastAPI(
    title="LLM Council API",
    description="Multi-model deliberation system with 3-stage council process for AI-assisted decision making.",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)


# Setup rate limiting
setup_rate_limiting(app)

# CORS configuration - supports environment variable for production
DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5176",
    "http://127.0.0.1:5176",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4000",
    "http://127.0.0.1:4000",
]

env_origins = os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS", "")
if env_origins:
    CORS_ORIGINS = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
else:
    CORS_ORIGINS = DEFAULT_ORIGINS

logger.info("cors_config", origins=CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestLoggingMiddleware)


# Global exception handler for better error messages
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with detailed error messages."""
    import traceback

    logger.exception("unhandled_exception", path=request.url.path, method=request.method, error=str(exc))

    origin = request.headers.get("origin")
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Check logs for details."}
        )
    else:
        response = JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "traceback": traceback.format_exc()
            }
        )

    # Add CORS headers manually (CORS middleware might not run on exceptions)
    if origin:
        env_origins = os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS", "")
        if env_origins:
            allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()]
        else:
            allowed_origins = DEFAULT_ORIGINS
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


# ============ Include All Routers ============
app.include_router(auth_router)
app.include_router(boards_router)
app.include_router(conversations_router)
app.include_router(council_router)
app.include_router(projects_router)
app.include_router(config_router)
app.include_router(api_keys_router)
app.include_router(analytics_router)
app.include_router(files_router)
app.include_router(tools_router)
app.include_router(teams_router)
app.include_router(integrations_router)
app.include_router(features_router)
app.include_router(misc_router)
app.include_router(workflows_router)
app.include_router(workflow_templates_router)
app.include_router(agents_router)


# ============ Health Endpoints ============

@app.get("/", tags=["health"], summary="Root Health Check")
async def root():
    """Root endpoint - returns service status."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/health", tags=["health"], summary="Health Check")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy", "service": "llm-council", "version": "1.0.0"}


@app.get("/api/debug/cors", tags=["debug"], include_in_schema=False)
async def debug_cors():
    """Debug endpoint to check CORS configuration. Disabled in production."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "cors_origins": CORS_ORIGINS,
        "env_origins": os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS", ""),
        "default_origins": DEFAULT_ORIGINS,
        "allow_credentials": True,
        "environment": environment,
    }
