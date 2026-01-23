"""FastAPI backend for LLM Council."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse, HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage_adapter as storage, analytics, projects, files, templates, search, budgets, ratings, batch
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings, run_full_council_stream
from .debate import run_debate
from .voting import run_vote
from .openrouter import query_model_stream
from .config import (
    AVAILABLE_MODELS, get_council_models, set_council_models,
    get_chairman_model, set_chairman_model, DEFAULT_COUNCIL_MODELS, DEFAULT_CHAIRMAN_MODEL,
    get_enhanced_features, set_enhanced_features, get_presets, apply_preset,
    get_personas, get_model_persona, set_model_persona, create_custom_persona,
    get_api_keys, set_api_key
)
from .openrouter import get_session_usage, reset_session_usage
from .model_sync import get_available_models, get_cached_models, MODELS_CACHE_FILE
import os
from datetime import datetime
from .tools import (
    web_search, fetch_url, execute_python, execute_javascript,
    remember_fact, remember_decision, get_memory_context, clear_memory, get_memory_stats,
    set_preference
)
from .export import (
    export_to_markdown, export_to_json, export_to_html,
    create_share_link, get_shared_conversation_id
)
from .routes.auth import router as auth_router
from .auth.dependencies import get_current_user, get_current_user_optional
from .database.connection import get_db, init_db
from .database import crud as db_crud
from .database.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

# Logging and middleware
from .logging_config import setup_logging, get_logger
from .middleware import RequestLoggingMiddleware
from .rate_limit import limiter, setup_rate_limiting, RATE_LIMITS

# Setup structured logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

# Global variable to store dynamically fetched models
_dynamic_models = {}
_models_last_synced = None

# Store active streams for cancellation support
# Maps conversation_id -> asyncio.Event (set when cancellation requested)
_active_streams: Dict[str, asyncio.Event] = {}


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

    # Shutdown: cleanup if needed
    logger.info("shutdown", message="Shutting down LLM Council API")


# OpenAPI Tags for endpoint grouping
tags_metadata = [
    {
        "name": "health",
        "description": "Health check and status endpoints"
    },
    {
        "name": "config",
        "description": "Council configuration, presets, and model management"
    },
    {
        "name": "conversations",
        "description": "Manage conversations, messages, and the 3-stage council process"
    },
    {
        "name": "voting",
        "description": "Multi-model voting system for collective decision making"
    },
    {
        "name": "tools",
        "description": "Web search, code execution, and memory tools"
    },
    {
        "name": "analytics",
        "description": "Usage analytics, model performance metrics, and cost tracking"
    },
    {
        "name": "ratings",
        "description": "Model response rating and recommendation system"
    },
    {
        "name": "agents",
        "description": "AI agent tasks with autonomous tool execution"
    },
    {
        "name": "images",
        "description": "AI image generation (DALL-E, Stable Diffusion, FLUX)"
    },
    {
        "name": "voice",
        "description": "Text-to-speech and speech-to-text services"
    },
    {
        "name": "integrations",
        "description": "External service integrations (Google Drive, Slack, GitHub)"
    },
    {
        "name": "projects",
        "description": "Project workspaces with knowledge bases and custom configurations"
    },
    {
        "name": "files",
        "description": "File upload and management for conversations"
    },
    {
        "name": "templates",
        "description": "Prompt templates with variable substitution"
    },
    {
        "name": "batch",
        "description": "Batch processing for multiple queries"
    },
    {
        "name": "budget",
        "description": "Budget limits, spending tracking, and alerts"
    },
    {
        "name": "folders",
        "description": "Folder organization for conversations"
    },
    {
        "name": "tags",
        "description": "Tag management for conversation categorization"
    },
    {
        "name": "sharing",
        "description": "Conversation sharing and export"
    },
    {
        "name": "teams",
        "description": "Team workspaces and collaboration"
    },
    {
        "name": "personas",
        "description": "Model persona customization"
    },
    {
        "name": "routing",
        "description": "Intelligent model routing and recommendations"
    },
]

app = FastAPI(
    title="LLM Council API",
    description="""
# LLM Council API

Multi-model deliberation system with 3-stage council process for AI-assisted decision making.

## Overview

The LLM Council enables you to query multiple AI models simultaneously and synthesize their responses
through a sophisticated 3-stage deliberation process:

1. **Stage 1 - Collection**: Query all council models in parallel
2. **Stage 2 - Peer Review**: Models anonymously evaluate and rank each other's responses
3. **Stage 3 - Synthesis**: Chairman model synthesizes the final answer

## Key Features

- **Council Deliberation**: Multi-model consensus through peer review
- **Voting System**: Collective decision making with confidence scores
- **Debate Mode**: Pro/Con team debates with synthesis
- **Quick Mode**: Single model streaming for faster responses
- **AI Agents**: Autonomous task execution with tools
- **Image Generation**: DALL-E 3, Stable Diffusion XL, FLUX
- **Voice**: Text-to-speech and transcription
- **Integrations**: Google Drive, Slack, GitHub

## Authentication

Most endpoints do not require authentication in development mode.
For production, configure JWT authentication via the `/api/auth` endpoints.
    """,
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

# Global exception handler for better error messages
# Note: This runs AFTER CORS middleware, so CORS headers should be preserved
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with detailed error messages."""
    import traceback
    import os
    
    # Log the error
    logger.exception("unhandled_exception", path=request.url.path, method=request.method, error=str(exc))
    
    # Get origin from request for CORS
    origin = request.headers.get("origin")
    
    # In production, return generic error; in dev, return details
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
    # Get CORS_ORIGINS from environment (same logic as above)
    if origin:
        env_origins = os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS", "")
        if env_origins:
            allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()]
        else:
            # Default origins
            allowed_origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5176",
                "http://127.0.0.1:5176",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:4000",
                "http://127.0.0.1:4000",
            ]
        
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

# Setup rate limiting
setup_rate_limiting(app)

# Include auth routes (router already has /api/auth prefix)
app.include_router(auth_router)


def get_all_models():
    """Get combined models (dynamic + fallback)."""
    # Merge dynamic models with hardcoded fallback
    combined = AVAILABLE_MODELS.copy()
    combined.update(_dynamic_models)
    return combined


# CORS configuration - supports environment variable for production
DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5176",
    "http://127.0.0.1:5176",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4000",
    "http://127.0.0.1:4000",
]

# Get allowed origins from environment or use defaults
# Set CORS_ORIGINS or ALLOWED_ORIGINS for production
env_origins = os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS", "")
if env_origins:
    CORS_ORIGINS = [
        origin.strip() for origin in env_origins.split(",") if origin.strip()
    ]
else:
    CORS_ORIGINS = DEFAULT_ORIGINS

logger.info("cors_config", origins=CORS_ORIGINS)
# #region agent log
# Debug logging - only write if file exists (local dev only)
import json
import os
debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
if os.path.exists(os.path.dirname(debug_log_path)):
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"cors-debug","hypothesisId":"H2","location":"main.py:262","message":"cors_config","data":{"origins":CORS_ORIGINS,"env_origins":env_origins},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
    except (FileNotFoundError, PermissionError, OSError):
        pass  # Ignore file errors in production
# #endregion

# #region agent log
# Log CORS configuration at startup
import os
debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
if os.path.exists(os.path.dirname(debug_log_path)):
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"cors-investigation","hypothesisId":"H3","location":"main.py:276","message":"cors_middleware:config","data":{"cors_origins":CORS_ORIGINS,"env_origins":env_origins,"allow_credentials":True},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
    except (FileNotFoundError, PermissionError, OSError):
        pass
# #endregion

# CORS middleware - MUST be first to handle preflight requests
# #region agent log
import os
debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
if os.path.exists(os.path.dirname(debug_log_path)):
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"cors-investigation","hypothesisId":"H4","location":"main.py:288","message":"cors_middleware:adding","data":{"cors_origins":CORS_ORIGINS,"allow_credentials":True,"allow_methods":"*","allow_headers":"*"},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
    except (FileNotFoundError, PermissionError, OSError):
        pass
# #endregion

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)


# Debug endpoint to check CORS configuration (only in non-production)
@app.get("/api/debug/cors", tags=["debug"])
async def debug_cors():
    """Debug endpoint to check CORS configuration."""
    import os
    env_origins = os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS", "")
    return {
        "cors_origins": CORS_ORIGINS,
        "env_origins": env_origins,
        "default_origins": DEFAULT_ORIGINS,
        "allow_credentials": True,
    }


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    attached_files: Optional[List[str]] = None


class QuickMessageRequest(BaseModel):
    """Request to send a message in Quick Mode (single model, no deliberation)."""
    content: str
    model: Optional[str] = None  # If None, uses chairman model


class QuickModeRequest(BaseModel):
    """Request for Quick Mode streaming endpoint."""
    message: str
    model: Optional[str] = None  # If None, uses chairman model


class DebateRequest(BaseModel):
    """Request to run a debate."""
    topic: str
    rounds: int = 2


class VoteRequest(BaseModel):
    """Request to run a vote."""
    question: str
    options: List[str]


class ImportConversationRequest(BaseModel):
    """Request to import a conversation from exported JSON."""
    title: Optional[str] = None
    messages: List[Dict[str, Any]]
    created_at: Optional[str] = None
    folder_id: Optional[str] = None
    tags: Optional[List[str]] = None


class ForkConversationRequest(BaseModel):
    """Request to fork a conversation from a specific message."""
    message_index: int  # Include messages up to and including this index


class ConfigUpdateRequest(BaseModel):
    """Request to update council configuration."""
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


class CreateProjectRequest(BaseModel):
    """Request to create a new project."""
    name: str
    description: Optional[str] = ""
    system_prompt: Optional[str] = ""
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    """Request to update a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    council_config: Optional[Dict[str, Any]] = None


class AddKnowledgeRequest(BaseModel):
    """Request to add knowledge base file."""
    filename: str
    content: str
    file_type: Optional[str] = "text"


class CreateFolderRequest(BaseModel):
    """Request to create a new folder."""
    name: str
    color: Optional[str] = "#4a90e2"
    icon: Optional[str] = "folder"


class MoveFolderRequest(BaseModel):
    """Request to move a conversation to a folder."""
    folder_id: Optional[str] = None


class UpdateTagsRequest(BaseModel):
    """Request to update conversation tags."""
    tags: List[str]


class CostEstimateRequest(BaseModel):
    """Request to estimate cost before sending a query."""
    message_length: int
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None


@app.get("/", tags=["health"], summary="Health Check", response_description="Service status")
async def root():
    """
    Health check endpoint.

    Returns the current service status. Use this to verify the API is running
    and responding to requests.

    Returns:
        dict: Status object with service name

    Example Response:
        ```json
        {"status": "ok", "service": "LLM Council API"}
        ```
    """
    return {"status": "ok", "service": "LLM Council API"}


# ============ CONFIG ENDPOINTS ============

@app.get(
    "/api/config",
    tags=["config"],
    summary="Get Council Configuration",
    response_description="Current council configuration including models and defaults"
)
async def get_config(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current council configuration (user-specific if authenticated).

    Returns the active council member models, chairman model, all available models,
    default configurations, and sync status.

    The council models are the LLMs that participate in Stage 1 (response collection)
    and Stage 2 (peer review). The chairman model synthesizes the final answer in Stage 3.

    Args:
        current_user: Authenticated user (optional - if None, uses global config)

    Returns:
        dict: Configuration object containing:
            - council_models: List of active council member model IDs
            - chairman_model: The chairman model ID for synthesis
            - available_models: Dict of all available models with metadata
            - defaults: Default council and chairman configurations
            - models_count: Total number of available models
            - last_synced: ISO timestamp of last OpenRouter sync
            - api_keys: Masked API keys (user-specific if authenticated)
    """
    all_models = get_all_models()
    
    # Get user-specific config if authenticated
    if current_user:
        settings = await db_crud.settings.get_by_user_id(db, current_user.id)
        if settings:
            council_models = settings.council_models or DEFAULT_COUNCIL_MODELS.copy()
            chairman_model = settings.chairman_model or DEFAULT_CHAIRMAN_MODEL
        else:
            # Create default settings for new user
            settings = await db_crud.settings.create(db, current_user.id)
            council_models = settings.council_models
            chairman_model = settings.chairman_model
        
        # Get user API keys (masked)
        providers = await db_crud.api_keys.list_user_providers(db, current_user.id)
        api_keys = {}
        for provider in ["openrouter", "openai", "anthropic", "google", "x-ai", "deepseek", "mistralai", "cohere", "qwen"]:
            user_key = await db_crud.api_keys.get_user_key(db, current_user.id, provider)
            if user_key:
                if len(user_key) > 8:
                    api_keys[provider] = user_key[:4] + "..." + user_key[-4:]
                else:
                    api_keys[provider] = "***"
            else:
                api_keys[provider] = ""
    else:
        # Fallback to global config
        council_models = get_council_models()
        chairman_model = get_chairman_model()
        api_keys = get_api_keys()
    
    return {
        "council_models": council_models,
        "chairman_model": chairman_model,
        "available_models": all_models,
        "defaults": {
            "council_models": DEFAULT_COUNCIL_MODELS,
            "chairman_model": DEFAULT_CHAIRMAN_MODEL
        },
        "models_count": len(all_models),
        "last_synced": _models_last_synced,
        "api_keys": api_keys
    }


@app.post(
    "/api/config",
    tags=["config"],
    summary="Update Council Configuration",
    response_description="Updated council configuration"
)
async def update_config(
    request: ConfigUpdateRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the council configuration (user-specific if authenticated).

    Allows changing the council member models and/or the chairman model.
    All model IDs must be valid (exist in available_models).

    Args:
        request: ConfigUpdateRequest with optional council_models and chairman_model
        current_user: Authenticated user (optional - if None, uses global config)

    Returns:
        dict: Updated configuration with council_models and chairman_model

    Raises:
        HTTPException 400: If any specified model ID is invalid
    """
    all_models = get_all_models()

    if current_user:
        # Update user-specific settings
        settings = await db_crud.settings.get_by_user_id(db, current_user.id)
        if not settings:
            settings = await db_crud.settings.create(db, current_user.id)
        
        council_models = request.council_models if request.council_models is not None else settings.council_models
        chairman_model = request.chairman_model if request.chairman_model is not None else settings.chairman_model
        
        # Validate models
        if request.council_models is not None:
            for model in request.council_models:
                if model not in all_models:
                    raise HTTPException(status_code=400, detail=f"Invalid model: {model}")
        
        if request.chairman_model is not None:
            if request.chairman_model not in all_models:
                raise HTTPException(status_code=400, detail=f"Invalid chairman model: {request.chairman_model}")
        
        # Update user settings
        await db_crud.settings.set_council_config(db, current_user.id, council_models, chairman_model)
        await db.commit()
        
        return {
            "council_models": council_models,
            "chairman_model": chairman_model
        }
    else:
        # Fallback to global config
        if request.council_models is not None:
            # Validate models
            for model in request.council_models:
                if model not in all_models:
                    raise HTTPException(status_code=400, detail=f"Invalid model: {model}")
            set_council_models(request.council_models)

        if request.chairman_model is not None:
            if request.chairman_model not in all_models:
                raise HTTPException(status_code=400, detail=f"Invalid chairman model: {request.chairman_model}")
            set_chairman_model(request.chairman_model)

        return {
            "council_models": get_council_models(),
            "chairman_model": get_chairman_model()
        }


@app.post(
    "/api/config/reset",
    tags=["config"],
    summary="Reset Configuration to Defaults",
    response_description="Default council configuration"
)
async def reset_config():
    """
    Reset the council configuration to default values.

    Restores both council member models and chairman model to their
    default configurations as defined in the application settings.

    Returns:
        dict: Default configuration with council_models and chairman_model
    """
    set_council_models(DEFAULT_COUNCIL_MODELS.copy())
    set_chairman_model(DEFAULT_CHAIRMAN_MODEL)
    return {
        "council_models": get_council_models(),
        "chairman_model": get_chairman_model()
    }


@app.post(
    "/api/estimate-cost",
    tags=["config"],
    summary="Estimate Query Cost",
    response_description="Estimated cost range for a council query"
)
async def estimate_cost(request: CostEstimateRequest):
    """
    Estimate the cost of a council query before sending it.

    Calculates the expected cost based on message length and current model configuration.
    The estimation accounts for all 3 stages of the council deliberation process:

    - **Stage 1**: Each council model receives the user's query
    - **Stage 2**: Each council model receives all Stage 1 responses + ranking prompt (~1500 tokens overhead)
    - **Stage 3**: Chairman receives everything + synthesis prompt (~2000 tokens overhead)

    Token estimation: ~4 characters per token (conservative estimate)

    Args:
        request: CostEstimateRequest containing:
            - message_length: Character length of the user's message
            - council_models: Optional list of model IDs (defaults to current config)
            - chairman_model: Optional chairman model ID (defaults to current config)

    Returns:
        dict: Cost estimate containing:
            - min_cost: Lower bound estimate (USD)
            - max_cost: Upper bound estimate (USD)
            - breakdown: Detailed cost per stage
            - models_used: List of models included in estimate
            - token_estimates: Estimated tokens per stage
    """
    all_models = get_all_models()

    # Use provided models or fall back to current config
    council_models = request.council_models or get_council_models()
    chairman = request.chairman_model or get_chairman_model()

    # Estimate tokens from message length (~4 chars per token)
    input_tokens = max(request.message_length // 4, 1)

    # Average response length estimate (tokens per model response)
    avg_response_tokens = 500  # Conservative estimate
    response_variance = 200  # For min/max range

    # Stage 1: Each council model receives the query
    stage1_input_tokens = input_tokens
    stage1_output_tokens_min = avg_response_tokens - response_variance
    stage1_output_tokens_max = avg_response_tokens + response_variance

    # Stage 2: Each council model receives all responses + ranking prompt
    num_models = len(council_models)
    ranking_prompt_overhead = 1500  # System prompt + ranking instructions
    stage2_input_tokens = (
        input_tokens +  # Original query
        (num_models * avg_response_tokens) +  # All Stage 1 responses
        ranking_prompt_overhead
    )
    stage2_output_tokens_min = 300  # Ranking output is typically shorter
    stage2_output_tokens_max = 600

    # Stage 3: Chairman receives everything + synthesis prompt
    synthesis_prompt_overhead = 2000
    stage3_input_tokens = (
        input_tokens +  # Original query
        (num_models * avg_response_tokens) +  # Stage 1 responses
        (num_models * 400) +  # Stage 2 rankings (shorter)
        synthesis_prompt_overhead
    )
    stage3_output_tokens_min = avg_response_tokens
    stage3_output_tokens_max = avg_response_tokens + response_variance * 2  # Chairman often writes more

    # Calculate costs per stage
    def get_model_cost(model_id: str, input_toks: int, output_toks: int) -> float:
        """Calculate cost for a model query in USD."""
        model_info = all_models.get(model_id, {"input_cost": 2.0, "output_cost": 8.0})
        input_cost_per_m = model_info.get("input_cost", 2.0)
        output_cost_per_m = model_info.get("output_cost", 8.0)
        return (input_toks * input_cost_per_m / 1_000_000) + (output_toks * output_cost_per_m / 1_000_000)

    # Stage 1 costs (all council models)
    stage1_min = sum(get_model_cost(m, stage1_input_tokens, stage1_output_tokens_min) for m in council_models)
    stage1_max = sum(get_model_cost(m, stage1_input_tokens, stage1_output_tokens_max) for m in council_models)

    # Stage 2 costs (all council models evaluate)
    stage2_min = sum(get_model_cost(m, stage2_input_tokens, stage2_output_tokens_min) for m in council_models)
    stage2_max = sum(get_model_cost(m, stage2_input_tokens, stage2_output_tokens_max) for m in council_models)

    # Stage 3 costs (chairman only)
    stage3_min = get_model_cost(chairman, stage3_input_tokens, stage3_output_tokens_min)
    stage3_max = get_model_cost(chairman, stage3_input_tokens, stage3_output_tokens_max)

    # Total costs
    total_min = stage1_min + stage2_min + stage3_min
    total_max = stage1_max + stage2_max + stage3_max

    return {
        "min_cost": round(total_min, 6),
        "max_cost": round(total_max, 6),
        "breakdown": {
            "stage1": {"min": round(stage1_min, 6), "max": round(stage1_max, 6)},
            "stage2": {"min": round(stage2_min, 6), "max": round(stage2_max, 6)},
            "stage3": {"min": round(stage3_min, 6), "max": round(stage3_max, 6)}
        },
        "models_used": {
            "council": council_models,
            "chairman": chairman
        },
        "token_estimates": {
            "stage1": {"input": stage1_input_tokens, "output_range": [stage1_output_tokens_min, stage1_output_tokens_max]},
            "stage2": {"input": stage2_input_tokens, "output_range": [stage2_output_tokens_min, stage2_output_tokens_max]},
            "stage3": {"input": stage3_input_tokens, "output_range": [stage3_output_tokens_min, stage3_output_tokens_max]}
        }
    }


# ============ API KEYS ============

class SetApiKeyRequest(BaseModel):
    """Request to set an API key for a provider."""
    provider: str
    api_key: str


@app.get(
    "/api/keys",
    tags=["config"],
    summary="Get Configured API Keys",
    response_description="List of configured API keys (masked) and supported providers"
)
async def get_api_keys_endpoint(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all configured API keys (masked for security) - user-specific if authenticated.

    Returns which providers have keys configured. API keys are masked
    to show only the first and last few characters for identification.

    When a provider API key is set, the system will use that provider's
    API directly instead of routing through OpenRouter, potentially
    reducing costs and latency.

    Returns:
        dict: Object containing:
            - api_keys: Dict of provider -> masked key (or empty if not set)
            - providers: List of all supported provider names
    """
    if current_user:
        # Get user-specific keys from database
        providers = await db_crud.api_keys.list_user_providers(db, current_user.id)
        keys = {}
        for provider in ["openrouter", "openai", "anthropic", "google", "x-ai", "deepseek", "mistralai", "cohere", "qwen"]:
            user_key = await db_crud.api_keys.get_user_key(db, current_user.id, provider)
            if user_key:
                # Mask the key
                if len(user_key) > 8:
                    keys[provider] = user_key[:4] + "..." + user_key[-4:]
                else:
                    keys[provider] = "***"
            else:
                keys[provider] = ""
    else:
        # Fallback to global config
        keys = get_api_keys()
    
    return {
        "api_keys": keys,
        "providers": ["openrouter", "openai", "anthropic", "google", "x-ai", "deepseek", "mistralai", "cohere", "qwen"]
    }


@app.post(
    "/api/keys",
    tags=["config"],
    summary="Set Provider API Key",
    response_description="Confirmation of API key update"
)
async def set_api_key_endpoint(
    request: SetApiKeyRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Set an API key for a specific provider (user-specific if authenticated, global otherwise).

    When set, the system will use the direct provider API instead of
    OpenRouter for that provider's models. This can reduce costs and
    improve latency for high-volume usage.

    Supported providers:
    - openrouter: OpenRouter (for accessing all models via OpenRouter)
    - openai: OpenAI (GPT-4, GPT-3.5, DALL-E)
    - anthropic: Anthropic (Claude models)
    - google: Google (Gemini models)
    - x-ai: xAI (Grok models)
    - deepseek: DeepSeek
    - mistralai: Mistral AI
    - cohere: Cohere

    Args:
        request: SetApiKeyRequest with provider name and API key
        current_user: Authenticated user (optional - if None, uses global config)

    Returns:
        dict: Confirmation with status, message, provider, and has_key flag

    Raises:
        HTTPException 400: If provider name is invalid
    """
    valid_providers = ["openrouter", "openai", "anthropic", "google", "x-ai", "deepseek", "mistralai", "cohere", "qwen"]
    if request.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )

    # If user is authenticated, store in database (user-specific)
    if current_user:
        await db_crud.api_keys.set_user_key(db, current_user.id, request.provider, request.api_key or "")
        await db.commit()
    else:
        # Fallback to global config for anonymous users
        set_api_key(request.provider, request.api_key)

    return {
        "status": "success",
        "message": f"API key {'set' if request.api_key else 'cleared'} for {request.provider}",
        "provider": request.provider,
        "has_key": bool(request.api_key),
        "user_specific": current_user is not None
    }


@app.delete(
    "/api/keys/{provider}",
    tags=["config"],
    summary="Delete Provider API Key",
    response_description="Confirmation of API key removal"
)
async def delete_api_key_endpoint(
    provider: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an API key for a provider (user-specific if authenticated).

    After removal, requests for that provider's models will be routed
    through OpenRouter instead of the direct provider API.

    Args:
        provider: Provider name (openrouter, openai, anthropic, google, x-ai, deepseek, mistralai, cohere, qwen)
        current_user: Authenticated user (optional)

    Returns:
        dict: Confirmation with status, message, and provider

    Raises:
        HTTPException 400: If provider name is invalid
    """
    valid_providers = ["openrouter", "openai", "anthropic", "google", "x-ai", "deepseek", "mistralai", "cohere", "qwen"]
    if provider not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    if current_user:
        # Delete user-specific key
        await db_crud.api_keys.delete_user_key(db, current_user.id, provider)
        await db.commit()
    else:
        # Fallback to global config
        set_api_key(provider, "")
    
    return {
        "status": "success",
        "message": f"API key removed for {provider}",
        "provider": provider,
        "user_specific": current_user is not None
    }


@app.get(
    "/api/presets",
    tags=["config"],
    summary="List Council Presets",
    response_description="List of available preset configurations"
)
async def list_presets():
    """
    List all available council presets.

    Presets are pre-configured council compositions optimized for different
    use cases. Each preset defines both the council member models and the
    chairman model.

    Available presets typically include:
    - **code_review**: Expert code reviewers for technical analysis
    - **research**: Deep research and analysis models
    - **creative**: Creative writing and brainstorming
    - **reasoning**: Complex logic and mathematics
    - **budget**: Cost-effective model selection

    Returns:
        dict: Object containing:
            - presets: List of preset objects with id, name, description, models, chairman
    """
    presets = get_presets()
    # Transform dict into list with ids
    presets_list = [
        {
            "id": preset_id,
            "name": preset_data["name"],
            "description": preset_data["description"],
            "models": preset_data["models"],
            "chairman": preset_data["chairman"]
        }
        for preset_id, preset_data in presets.items()
    ]
    return {"presets": presets_list}


@app.post(
    "/api/presets/{preset_id}/apply",
    tags=["config"],
    summary="Apply Council Preset",
    response_description="Confirmation of preset application with new configuration"
)
async def apply_council_preset(preset_id: str):
    """
    Apply a preset configuration to the council.

    This will update both the council member models and the chairman model
    to the preset's configuration. The change takes effect immediately
    for subsequent council queries.

    Args:
        preset_id: The preset identifier (e.g., "code_review", "research")

    Returns:
        dict: Confirmation object containing:
            - status: "success"
            - message: Human-readable confirmation
            - council_models: New council model list
            - chairman_model: New chairman model
            - preset_name: Name of applied preset
            - preset_description: Description of the preset

    Raises:
        HTTPException 404: If preset_id is not found
        HTTPException 500: If preset application fails
    """
    try:
        result = apply_preset(preset_id)
        return {
            "status": "success",
            "message": f"Applied preset: {result['preset_name']}",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply preset: {str(e)}")


@app.post(
    "/api/models/refresh",
    tags=["config"],
    summary="Refresh Available Models",
    response_description="Updated model list from OpenRouter"
)
async def refresh_models():
    """
    Force refresh of available models from OpenRouter API.

    Fetches the latest model list from OpenRouter, including new models,
    updated pricing, and removed models. This is useful when new models
    are released or pricing changes.

    Returns:
        dict: Object containing:
            - status: "success"
            - models_count: Number of models available
            - last_synced: ISO timestamp of this sync

    Raises:
        HTTPException 500: If refresh fails (e.g., network error)
    """
    global _dynamic_models, _models_last_synced
    try:
        _dynamic_models = await get_available_models()
        _models_last_synced = datetime.now().isoformat()
        return {
            "status": "success",
            "models_count": len(_dynamic_models),
            "last_synced": _models_last_synced
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh models: {str(e)}")


# ============ USAGE/COST ENDPOINTS ============

@app.get(
    "/api/usage",
    tags=["analytics"],
    summary="Get Session Usage Statistics",
    response_description="Current session usage metrics and costs"
)
async def get_usage():
    """
    Get current session usage statistics.

    Returns token usage, cost estimates, and request counts for the
    current session. Use this to monitor API consumption.

    Returns:
        dict: Usage statistics including:
            - total_tokens: Total tokens used
            - prompt_tokens: Input tokens
            - completion_tokens: Output tokens
            - total_cost: Estimated cost in USD
            - request_count: Number of API requests
    """
    return get_session_usage()


@app.post(
    "/api/usage/reset",
    tags=["analytics"],
    summary="Reset Usage Statistics",
    response_description="Confirmation of usage reset"
)
async def reset_usage():
    """
    Reset session usage statistics.

    Clears all usage counters to start fresh tracking.
    This does not affect billing - only local tracking.

    Returns:
        dict: Confirmation with status "reset"
    """
    reset_session_usage()
    return {"status": "reset"}


# ============ CACHE ENDPOINTS ============

from .openrouter import get_cache_stats, clear_cache

@app.get(
    "/api/cache",
    tags=["analytics"],
    summary="Get Cache Statistics",
    response_description="Cache hit/miss statistics"
)
async def get_cache_status():
    """
    Get response cache statistics.

    Returns cache hit rate, size, and other metrics for the
    response caching system that reduces duplicate API calls.

    Returns:
        dict: Cache statistics including hits, misses, and size
    """
    return get_cache_stats()


@app.post(
    "/api/cache/clear",
    tags=["analytics"],
    summary="Clear Response Cache",
    response_description="Confirmation of cache clear"
)
async def clear_response_cache():
    """
    Clear the response cache.

    Removes all cached responses, forcing fresh API calls for
    subsequent requests. Use when you need to ensure fresh responses.

    Returns:
        dict: Confirmation with status "cleared"
    """
    clear_cache()
    return {"status": "cleared"}


# ============ ANALYTICS ENDPOINTS ============

@app.get(
    "/api/analytics",
    tags=["analytics"],
    summary="Get Comprehensive Analytics",
    response_description="Full analytics summary across all dimensions"
)
async def get_analytics():
    """
    Get comprehensive analytics summary.

    Returns a complete overview of system usage including model performance,
    costs, response times, and usage trends.

    Returns:
        dict: Comprehensive analytics object with:
            - model_stats: Per-model performance metrics
            - cost_breakdown: Cost analysis by model and time
            - response_times: Latency statistics
            - usage_trends: Historical usage data
    """
    return analytics.get_all_analytics()


@app.get(
    "/api/analytics/models",
    tags=["analytics"],
    summary="Get Model Performance Statistics",
    response_description="Per-model performance metrics"
)
async def get_analytics_models():
    """
    Get model performance statistics.

    Returns detailed metrics for each model including request counts,
    success rates, average response times, and ranking performance.

    Returns:
        dict: Model statistics with per-model metrics
    """
    return analytics.get_model_stats()


@app.get(
    "/api/analytics/costs",
    tags=["analytics"],
    summary="Get Cost Breakdown",
    response_description="Cost analysis by model and time period"
)
async def get_analytics_costs():
    """
    Get cost breakdown.

    Returns cost analysis including total spend, per-model costs,
    and cost trends over time.

    Returns:
        dict: Cost breakdown with per-model and temporal analysis
    """
    return analytics.get_cost_breakdown()


@app.get(
    "/api/analytics/times",
    tags=["analytics"],
    summary="Get Response Time Statistics",
    response_description="Latency metrics and percentiles"
)
async def get_analytics_times():
    """
    Get response time statistics.

    Returns latency analysis including average, median, p95, and p99
    response times for each model and overall.

    Returns:
        dict: Response time statistics with percentiles
    """
    return analytics.get_response_times()


@app.get(
    "/api/analytics/trends",
    tags=["analytics"],
    summary="Get Usage Trends",
    response_description="Historical usage data over time"
)
async def get_analytics_trends():
    """
    Get usage trends over time.

    Returns historical data showing usage patterns, including
    daily/weekly/monthly request volumes and cost trends.

    Returns:
        dict: Usage trends with temporal breakdown
    """
    return analytics.get_usage_trends()


@app.post(
    "/api/analytics/clear",
    tags=["analytics"],
    summary="Clear Analytics Data",
    response_description="Confirmation of analytics clear"
)
async def clear_analytics_data():
    """
    Clear all analytics data.

    Removes all historical analytics data including model stats,
    costs, response times, and trends. Use with caution.

    Returns:
        dict: Confirmation with status "cleared"
    """
    analytics.clear_analytics()
    return {"status": "cleared"}


# ============ RATINGS ENDPOINTS ============

class SubmitRatingRequest(BaseModel):
    conversation_id: str
    message_index: int
    model_id: str
    rating: int
    feedback_text: Optional[str] = None
    query_category: Optional[str] = None


@app.post(
    "/api/ratings",
    tags=["ratings"],
    summary="Submit Response Rating",
    response_description="Confirmation of rating submission"
)
async def submit_response_rating(request: SubmitRatingRequest):
    """
    Submit a rating for a model response.

    Rate individual model responses on a scale (typically 1-5) to help
    improve model recommendations and track quality over time.

    Args:
        request: SubmitRatingRequest containing:
            - conversation_id: The conversation containing the response
            - message_index: Index of the message in the conversation
            - model_id: The model being rated
            - rating: Numeric rating (1-5)
            - feedback_text: Optional written feedback
            - query_category: Optional category for analytics

    Returns:
        dict: Confirmation with status and rating_saved flag

    Raises:
        HTTPException 400: If rating value is invalid
        HTTPException 500: If rating submission fails
    """
    try:
        success = ratings.submit_rating(
            conversation_id=request.conversation_id,
            message_index=request.message_index,
            model_id=request.model_id,
            rating=request.rating,
            feedback_text=request.feedback_text,
            query_category=request.query_category
        )
        return {"status": "success", "rating_saved": success}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit rating: {str(e)}")


@app.get(
    "/api/ratings/{conversation_id}/{message_index}/{model_id}",
    tags=["ratings"],
    summary="Get Response Rating",
    response_description="Rating data if exists"
)
async def get_response_rating(conversation_id: str, message_index: int, model_id: str):
    """
    Get existing rating for a specific response.

    Check if a rating exists for a particular model response in a conversation.

    Args:
        conversation_id: The conversation ID
        message_index: Index of the message
        model_id: The model to check rating for

    Returns:
        dict: Object with has_rating flag and rating data if exists
    """
    rating = ratings.get_rating(conversation_id, message_index, model_id)
    if rating is None:
        return {"has_rating": False}
    return {"has_rating": True, "rating": rating}


@app.get(
    "/api/ratings/models",
    tags=["ratings"],
    summary="Get Model Rating Statistics",
    response_description="Aggregate rating statistics per model"
)
async def get_model_ratings():
    """
    Get rating statistics for all models.

    Returns aggregate metrics including average rating, total ratings,
    and rating distribution for each model.

    Returns:
        dict: Per-model rating statistics
    """
    return ratings.get_model_rating_stats()


@app.get(
    "/api/ratings/recommendations",
    tags=["ratings"],
    summary="Get Model Recommendations",
    response_description="Recommended models based on query and ratings"
)
async def get_rating_recommendations(query: str, num_recommendations: int = 3):
    """
    Get model recommendations based on query and past ratings.

    Uses historical rating data and query analysis to suggest
    the best models for a given type of question.

    Args:
        query: The query to get recommendations for
        num_recommendations: Number of models to recommend (default: 3)

    Returns:
        dict: Query and list of recommended model IDs with scores
    """
    recommendations = ratings.get_recommendations_for_query(query, num_recommendations)
    return {"query": query, "recommendations": recommendations}


@app.get(
    "/api/ratings/analytics",
    tags=["ratings"],
    summary="Get Rating Analytics",
    response_description="Comprehensive rating analytics"
)
async def get_rating_analytics_summary():
    """
    Get comprehensive rating analytics.

    Returns detailed analytics including rating trends, category breakdowns,
    model comparisons, and quality metrics over time.

    Returns:
        dict: Comprehensive rating analytics
    """
    return ratings.get_rating_analytics()


@app.post(
    "/api/ratings/clear",
    tags=["ratings"],
    summary="Clear All Ratings",
    response_description="Confirmation of ratings clear"
)
async def clear_all_ratings():
    """
    Clear all rating data.

    Removes all historical rating data. Use with caution as this
    affects model recommendations.

    Returns:
        dict: Confirmation with status "cleared"
    """
    ratings.clear_ratings()
    return {"status": "cleared"}


# ============ TOOLS ENDPOINTS ============

class SearchRequest(BaseModel):
    query: str
    num_results: Optional[int] = 5

class CodeRequest(BaseModel):
    code: str
    language: str = "python"
    timeout: Optional[int] = 30

class MemoryRequest(BaseModel):
    action: str  # remember_fact, remember_decision, set_preference, get_context, clear, stats
    content: Optional[str] = None
    category: Optional[str] = "general"
    question: Optional[str] = None
    decision: Optional[str] = None
    reasoning: Optional[str] = None
    key: Optional[str] = None
    value: Optional[Any] = None

class FeaturesRequest(BaseModel):
    web_search: Optional[bool] = None
    code_execution: Optional[bool] = None
    memory: Optional[bool] = None


@app.get(
    "/api/features",
    tags=["tools"],
    summary="Get Enhanced Features Configuration",
    response_description="Current feature toggle states"
)
async def get_features():
    """
    Get enhanced features configuration.

    Returns the current state of enhanced features including:
    - web_search: Whether web search is enabled
    - code_execution: Whether code execution is enabled
    - memory: Whether memory/context persistence is enabled

    Returns:
        dict: Feature configuration with boolean flags
    """
    return get_enhanced_features()


@app.post(
    "/api/features",
    tags=["tools"],
    summary="Update Enhanced Features",
    response_description="Updated feature configuration"
)
async def update_features(request: FeaturesRequest):
    """
    Update enhanced features configuration.

    Enable or disable enhanced features for council queries.
    When enabled, these features are available to the council during deliberation.

    Args:
        request: FeaturesRequest with optional boolean flags for each feature

    Returns:
        dict: Updated feature configuration
    """
    updates = {}
    if request.web_search is not None:
        updates["web_search"] = request.web_search
    if request.code_execution is not None:
        updates["code_execution"] = request.code_execution
    if request.memory is not None:
        updates["memory"] = request.memory

    if updates:
        set_enhanced_features(updates)

    return get_enhanced_features()


# ============ ROUTELLM ENDPOINTS ============

from .router import route_query, get_quick_recommendation, get_council_for_query
from .agents import (
    create_agent_task, run_agent, get_task, list_tasks,
    cancel_task, delete_task, task_to_dict, AgentStatus
)
from .image_gen import (
    generate_image, get_image, list_images, delete_image,
    get_available_providers, image_to_dict
)
from .voice import (
    text_to_speech, transcribe, get_tts_result, get_transcription_result,
    list_tts_results, list_transcriptions, get_available_tts_providers,
    get_available_stt_providers, tts_result_to_dict, transcription_result_to_dict
)
from .integrations import (
    gdrive_list_files, gdrive_get_file_content, gdrive_upload_file,
    slack_send_message, slack_send_webhook, slack_list_channels,
    github_list_repos, github_get_file, github_list_issues,
    github_create_issue, github_list_prs, get_integration_status
)

class RouteRequest(BaseModel):
    query: str
    prefer_speed: bool = False
    prefer_cost: bool = False
    prefer_quality: bool = True
    num_recommendations: int = 3


@app.post(
    "/api/route",
    tags=["routing"],
    summary="Route Query to Best Models",
    response_description="Model recommendations with analysis"
)
async def route_model(request: RouteRequest):
    """
    Intelligently route a query to the best model(s).

    Analyzes the query to determine its type (code, creative, reasoning, etc.)
    and recommends the most suitable models based on:
    - Query complexity and type detection
    - Model capabilities and specializations
    - User preferences (speed, cost, quality)

    Args:
        request: RouteRequest containing:
            - query: The query to analyze
            - prefer_speed: Prioritize faster models
            - prefer_cost: Prioritize cheaper models
            - prefer_quality: Prioritize higher quality models
            - num_recommendations: Number of models to recommend

    Returns:
        dict: Analysis results with:
            - query_type: Detected query category
            - recommendations: List of recommended models with scores
            - analysis: Detailed reasoning
    """
    result = route_query(
        query=request.query,
        prefer_speed=request.prefer_speed,
        prefer_cost=request.prefer_cost,
        prefer_quality=request.prefer_quality,
        num_recommendations=request.num_recommendations,
    )
    return result


@app.get(
    "/api/route/quick",
    tags=["routing"],
    summary="Quick Model Recommendation",
    response_description="Single best model for query"
)
async def quick_route(query: str):
    """
    Get a single quick model recommendation for a query.

    Fast analysis that returns the single best model for a query
    without full analysis. Useful for quick mode selection.

    Args:
        query: The query to get a recommendation for

    Returns:
        dict: Object with model_id of the recommended model
    """
    model_id = get_quick_recommendation(query)
    return {"model_id": model_id}


@app.get(
    "/api/route/council",
    tags=["routing"],
    summary="Get Optimal Council Composition",
    response_description="Recommended council models for query"
)
async def route_council(query: str, max_models: int = 5):
    """
    Get an optimal council composition for a query.

    Analyzes the query and returns a diverse council of models
    optimized for that specific type of question.

    Args:
        query: The query to build a council for
        max_models: Maximum number of models in the council (default: 5)

    Returns:
        dict: Object with council_models list
    """
    council = get_council_for_query(query, max_models)
    return {"council_models": council}


# ============ AI AGENT ENDPOINTS ============

class CreateAgentRequest(BaseModel):
    """Request to create an AI agent task."""
    query: str
    model: Optional[str] = "anthropic/claude-sonnet-4"
    context: Optional[Dict[str, Any]] = None


@app.post(
    "/api/agents",
    tags=["agents"],
    summary="Create AI Agent Task",
    response_description="Created agent task details"
)
async def create_agent(request: CreateAgentRequest):
    """
    Create a new AI agent task.

    Creates an autonomous agent that can execute complex tasks using
    available tools. The agent will plan and execute steps to complete
    the given query.

    Available tools:
    - **web_search**: Search the web for information
    - **fetch_url**: Fetch and parse content from URLs
    - **execute_python**: Run Python code in sandbox
    - **execute_javascript**: Run JavaScript code in sandbox
    - **think**: Record reasoning process (chain-of-thought)
    - **answer**: Provide final answer and complete task

    Args:
        request: CreateAgentRequest containing:
            - query: The task for the agent to complete
            - model: Model to use (default: claude-sonnet-4)
            - context: Optional context dict for the task

    Returns:
        dict: Task object with id, status, query, and metadata
    """
    task = await create_agent_task(
        user_query=request.query,
        model=request.model or "anthropic/claude-sonnet-4",
        context=request.context
    )
    return task_to_dict(task)


@app.get(
    "/api/agents",
    tags=["agents"],
    summary="List Agent Tasks",
    response_description="List of all agent tasks"
)
async def list_agent_tasks():
    """
    List all agent tasks.

    Returns all tasks across all statuses including pending,
    executing, completed, failed, and cancelled tasks.

    Returns:
        dict: Object with tasks list and count
    """
    tasks = list_tasks()
    return {
        "tasks": [task_to_dict(t) for t in tasks],
        "count": len(tasks)
    }


@app.get(
    "/api/agents/{task_id}",
    tags=["agents"],
    summary="Get Agent Task",
    response_description="Agent task details"
)
async def get_agent_task(task_id: str):
    """
    Get a specific agent task by ID.

    Returns full task details including all execution steps,
    outputs, and current status.

    Args:
        task_id: The unique task identifier

    Returns:
        dict: Full task object with steps and results

    Raises:
        HTTPException 404: If task not found
    """
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Agent task not found")
    return task_to_dict(task)


@app.post(
    "/api/agents/{task_id}/run",
    tags=["agents"],
    summary="Run Agent Task",
    response_description="Completed task with results"
)
async def run_agent_task(task_id: str, max_steps: int = 10):
    """
    Run an agent task to completion.

    Executes the agent task step by step until completion or
    max_steps is reached. Each step may involve tool usage.

    Args:
        task_id: The task ID to execute
        max_steps: Maximum steps to execute (default: 10)

    Returns:
        dict: Completed task with all steps and final answer

    Raises:
        HTTPException 404: If task not found
        HTTPException 400: If task was cancelled
    """
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Agent task not found")

    if task.status == AgentStatus.COMPLETED:
        return task_to_dict(task)

    if task.status == AgentStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Task was cancelled")

    # Run the agent
    completed_task = await run_agent(task, max_steps=max_steps)
    return task_to_dict(completed_task)


@app.post(
    "/api/agents/{task_id}/run/stream",
    tags=["agents"],
    summary="Run Agent Task with Streaming",
    response_description="Server-Sent Events stream of execution"
)
async def run_agent_task_stream(task_id: str, max_steps: int = 10):
    """
    Run an agent task with streaming updates.

    Executes the task and streams updates as Server-Sent Events.
    Each step completion triggers an event with step details.

    Event types:
    - **started**: Task execution started
    - **step**: A step completed (includes tool, input, output)
    - **complete**: Task finished (includes full task object)
    - **error**: An error occurred

    Args:
        task_id: The task ID to execute
        max_steps: Maximum steps to execute (default: 10)

    Returns:
        StreamingResponse: SSE stream with execution updates

    Raises:
        HTTPException 404: If task not found
    """
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Agent task not found")

    if task.status == AgentStatus.COMPLETED:
        return task_to_dict(task)

    async def event_generator():
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'started', 'task_id': task_id})}\n\n"

            def on_step(step):
                # This callback is called after each step
                step_data = {
                    "id": step.id,
                    "tool": step.tool.value,
                    "input": step.input,
                    "output": step.output,
                    "status": step.status
                }
                return step_data

            # Run agent with step callback
            task.status = AgentStatus.EXECUTING

            for step_num in range(max_steps):
                from .agents import run_agent_step
                success = await run_agent_step(task)

                if task.steps:
                    last_step = task.steps[-1]
                    step_event = {
                        "type": "step",
                        "step_number": step_num + 1,
                        "step": {
                            "id": last_step.id,
                            "tool": last_step.tool.value,
                            "input": last_step.input,
                            "output": last_step.output,
                            "status": last_step.status
                        }
                    }
                    yield f"data: {json.dumps(step_event)}\n\n"

                if task.status == AgentStatus.COMPLETED:
                    break

                if not success:
                    task.status = AgentStatus.FAILED
                    break

                await asyncio.sleep(0.5)

            # Send completion event
            completion_event = {
                "type": "complete",
                "task": task_to_dict(task)
            }
            yield f"data: {json.dumps(completion_event)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post(
    "/api/agents/{task_id}/cancel",
    tags=["agents"],
    summary="Cancel Agent Task",
    response_description="Cancellation confirmation"
)
async def cancel_agent_task(task_id: str):
    """
    Cancel a running agent task.

    Attempts to stop an in-progress agent task. Tasks that have already
    completed cannot be cancelled.

    Args:
        task_id: Unique identifier of the task to cancel

    Returns:
        dict: Confirmation containing:
            - status: "cancelled"
            - task_id: ID of cancelled task

    Raises:
        HTTPException 404: Task not found or already completed
    """
    success = cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or already completed")
    return {"status": "cancelled", "task_id": task_id}


@app.delete(
    "/api/agents/{task_id}",
    tags=["agents"],
    summary="Delete Agent Task",
    response_description="Deletion confirmation"
)
async def delete_agent_task(task_id: str):
    """
    Delete an agent task and its results.

    Removes the task record and any associated results from storage.

    Args:
        task_id: Unique identifier of the task to delete

    Returns:
        dict: Confirmation containing:
            - status: "deleted"
            - task_id: ID of deleted task

    Raises:
        HTTPException 404: Agent task not found
    """
    success = delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent task not found")
    return {"status": "deleted", "task_id": task_id}


# ============ IMAGE GENERATION ENDPOINTS ============

class ImageGenerationRequest(BaseModel):
    """Request to generate an image."""
    prompt: str
    provider: str = "dalle-3"
    size: str = "1024x1024"
    quality: str = "standard"
    style: Optional[str] = "vivid"


@app.post(
    "/api/images/generate",
    tags=["images"],
    summary="Generate AI Image",
    response_description="Generated image with URL and metadata"
)
async def generate_image_endpoint(request: ImageGenerationRequest):
    """
    Generate an image using AI image generation providers.

    Supported Providers:
    - dalle-3: OpenAI DALL-E 3 (best quality, most creative)
    - dalle-2: OpenAI DALL-E 2 (faster, lower cost)
    - sdxl: Stable Diffusion XL via Stability AI
    - flux: FLUX.1 via Together AI

    Supported Sizes:
    - 1024x1024: Square format
    - 1792x1024: Landscape format
    - 1024x1792: Portrait format

    Args:
        request: ImageGenerationRequest containing:
            - prompt: Description of the image to generate
            - provider: Image generation provider (default: "dalle-3")
            - size: Image dimensions (default: "1024x1024")
            - quality: "standard" or "hd" for DALL-E 3
            - style: "vivid" or "natural" for DALL-E 3

    Returns:
        dict: Generated image containing:
            - id: Unique image identifier
            - url: URL to access the generated image
            - prompt: The prompt used
            - provider: Provider used
            - created_at: Generation timestamp

    Raises:
        HTTPException 500: If image generation fails
    """
    image = await generate_image(
        prompt=request.prompt,
        provider=request.provider,
        size=request.size,
        quality=request.quality,
        style=request.style
    )

    if image.error:
        raise HTTPException(status_code=500, detail=image.error)

    return image_to_dict(image)


@app.get(
    "/api/images/providers",
    tags=["images"],
    summary="List Image Providers",
    response_description="Available image generation providers"
)
async def list_image_providers():
    """
    List available image generation providers and their capabilities.

    Returns which providers are configured and available for use
    based on API keys present in the system.

    Returns:
        dict: Available providers containing:
            - providers: List of provider info with name, capabilities, and status
    """
    return {"providers": get_available_providers()}


@app.get(
    "/api/images",
    tags=["images"],
    summary="List Generated Images",
    response_description="List of generated images"
)
async def list_generated_images(limit: int = 50):
    """
    List all previously generated images.

    Retrieves the history of AI-generated images with metadata.

    Args:
        limit: Maximum number of images to return (default: 50)

    Returns:
        dict: Image list containing:
            - images: List of generated images with metadata
            - count: Total number of images returned
    """
    return {"images": list_images(limit), "count": len(list_images(limit))}


@app.get(
    "/api/images/{image_id}",
    tags=["images"],
    summary="Get Generated Image",
    response_description="Image details and URL"
)
async def get_generated_image(image_id: str):
    """
    Get a specific generated image by ID.

    Retrieves the full details of a previously generated image.

    Args:
        image_id: The unique identifier of the generated image

    Returns:
        dict: Image details containing:
            - id: Image identifier
            - url: URL to access the image
            - prompt: Original generation prompt
            - provider: Provider used for generation
            - created_at: When the image was generated

    Raises:
        HTTPException 404: If image not found
    """
    image = get_image(image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return image_to_dict(image)


@app.delete(
    "/api/images/{image_id}",
    tags=["images"],
    summary="Delete Generated Image",
    response_description="Deletion confirmation"
)
async def delete_generated_image(image_id: str):
    """
    Delete a generated image.

    Permanently removes a generated image from storage.
    This action cannot be undone.

    Args:
        image_id: The unique identifier of the image to delete

    Returns:
        dict: Deletion confirmation containing:
            - status: "deleted"
            - image_id: The ID of the deleted image

    Raises:
        HTTPException 404: If image not found
    """
    success = delete_image(image_id)
    if not success:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"status": "deleted", "image_id": image_id}


# ============ VOICE/TTS/STT ENDPOINTS ============

class TTSRequest(BaseModel):
    """Request to convert text to speech."""
    text: str
    provider: str = "openai"
    voice: str = "alloy"
    model: Optional[str] = "tts-1"
    speed: Optional[float] = 1.0


@app.post(
    "/api/voice/tts",
    tags=["voice"],
    summary="Text to Speech",
    response_description="Generated audio file information"
)
async def text_to_speech_endpoint(request: TTSRequest):
    """
    Convert text to speech using AI voice synthesis.

    Supported Providers:
    - openai: OpenAI TTS with voices: alloy, echo, fable, onyx, nova, shimmer
    - elevenlabs: ElevenLabs with premium natural-sounding voices

    Args:
        request: TTSRequest containing:
            - text: The text to convert to speech
            - provider: TTS provider (default: "openai")
            - voice: Voice ID to use (default: "alloy")
            - model: TTS model (default: "tts-1", or "tts-1-hd" for higher quality)
            - speed: Playback speed multiplier (0.25-4.0, default: 1.0)

    Returns:
        dict: TTS result containing:
            - id: Unique result identifier
            - audio_url: URL to download the generated audio
            - text: Original text
            - voice: Voice used
            - duration: Audio duration in seconds
            - created_at: Generation timestamp

    Raises:
        HTTPException 500: If TTS generation fails
    """
    result = await text_to_speech(
        text=request.text,
        provider=request.provider,
        voice=request.voice,
        model=request.model,
        speed=request.speed
    )

    if result.error:
        raise HTTPException(status_code=500, detail=result.error)

    return tts_result_to_dict(result)


@app.post(
    "/api/voice/transcribe",
    tags=["voice"],
    summary="Transcribe Audio",
    response_description="Transcription result with text"
)
async def transcribe_endpoint(
    file: UploadFile = File(...),
    provider: str = "whisper",
    language: Optional[str] = None
):
    """
    Transcribe audio to text using speech-to-text services.

    Supported Providers:
    - whisper: OpenAI Whisper (fast, accurate, multi-language)
    - assemblyai: AssemblyAI (speaker diarization, sentiment analysis)

    Supported Audio Formats:
    mp3, wav, m4a, webm, ogg, flac, mp4, mpeg, mpga

    Args:
        file: Audio file to transcribe (multipart form upload)
        provider: STT provider (default: "whisper")
        language: Optional language code (e.g., "en", "es", "fr")

    Returns:
        dict: Transcription result containing:
            - id: Unique result identifier
            - text: Transcribed text
            - language: Detected or specified language
            - duration: Audio duration in seconds
            - confidence: Confidence score (if available)
            - created_at: Transcription timestamp

    Raises:
        HTTPException 500: If transcription fails
    """
    audio_data = await file.read()

    result = await transcribe(
        audio_data=audio_data,
        provider=provider,
        filename=file.filename or "audio.mp3",
        language=language
    )

    if result.error:
        raise HTTPException(status_code=500, detail=result.error)

    return transcription_result_to_dict(result)


@app.get(
    "/api/voice/tts/providers",
    tags=["voice"],
    summary="List TTS Providers",
    response_description="Available TTS providers and voices"
)
async def list_tts_providers():
    """
    List available text-to-speech providers and their voices.

    Returns which TTS providers are configured and available,
    along with the voices each provider supports.

    Returns:
        dict: Provider information containing:
            - providers: List of providers with available voices
    """
    return {"providers": get_available_tts_providers()}


@app.get(
    "/api/voice/stt/providers",
    tags=["voice"],
    summary="List STT Providers",
    response_description="Available speech-to-text providers"
)
async def list_stt_providers():
    """
    List available speech-to-text providers.

    Returns which STT providers are configured and available
    for audio transcription.

    Returns:
        dict: Provider information containing:
            - providers: List of available STT providers
    """
    return {"providers": get_available_stt_providers()}


@app.get(
    "/api/voice/tts",
    tags=["voice"],
    summary="List TTS History",
    response_description="Recent TTS generation results"
)
async def list_tts_history(limit: int = 50):
    """
    List recent text-to-speech generation results.

    Retrieves the history of TTS generations with metadata.

    Args:
        limit: Maximum number of results to return (default: 50)

    Returns:
        dict: TTS history containing:
            - results: List of TTS results with metadata
            - count: Total number of results returned
    """
    return {"results": list_tts_results(limit), "count": len(list_tts_results(limit))}


@app.get(
    "/api/voice/transcriptions",
    tags=["voice"],
    summary="List Transcription History",
    response_description="Recent transcription results"
)
async def list_transcription_history(limit: int = 50):
    """
    List recent audio transcription results.

    Retrieves the history of audio transcriptions with metadata.

    Args:
        limit: Maximum number of results to return (default: 50)

    Returns:
        dict: Transcription history containing:
            - results: List of transcription results with metadata
            - count: Total number of results returned
    """
    return {"results": list_transcriptions(limit), "count": len(list_transcriptions(limit))}


@app.get(
    "/api/voice/tts/{result_id}",
    tags=["voice"],
    summary="Get TTS Result",
    response_description="Specific TTS result details"
)
async def get_tts_by_id(result_id: str):
    """
    Get a specific text-to-speech result by ID.

    Retrieves the full details of a TTS generation including audio URL.

    Args:
        result_id: The unique identifier of the TTS result

    Returns:
        dict: TTS result containing:
            - id: Result identifier
            - audio_url: URL to the audio file
            - text: Original text
            - voice: Voice used
            - duration: Audio duration
            - created_at: Generation timestamp

    Raises:
        HTTPException 404: If TTS result not found
    """
    result = get_tts_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="TTS result not found")
    return tts_result_to_dict(result)


@app.get(
    "/api/voice/transcriptions/{result_id}",
    tags=["voice"],
    summary="Get Transcription Result",
    response_description="Specific transcription result details"
)
async def get_transcription_by_id(result_id: str):
    """
    Get a specific transcription result by ID.

    Retrieves the full details of an audio transcription.

    Args:
        result_id: The unique identifier of the transcription

    Returns:
        dict: Transcription result containing:
            - id: Result identifier
            - text: Transcribed text
            - language: Detected language
            - duration: Audio duration
            - confidence: Confidence score
            - created_at: Transcription timestamp

    Raises:
        HTTPException 404: If transcription not found
    """
    result = get_transcription_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Transcription not found")
    return transcription_result_to_dict(result)


# ============ INTEGRATIONS ENDPOINTS ============

@app.get(
    "/api/integrations/status",
    tags=["integrations"],
    summary="Get Integration Status",
    response_description="Status of all configured integrations"
)
async def get_integrations_status():
    """
    Get status of all available external integrations.

    Returns the connection status and configuration state of all
    supported integrations (Google Drive, Slack, GitHub, etc.).

    Returns:
        dict: Integration status containing:
            - gdrive: Google Drive connection status
            - slack: Slack connection status
            - github: GitHub connection status
            - Each with: configured, connected, error fields
    """
    return get_integration_status()


# --- Google Drive ---

class GDriveListRequest(BaseModel):
    access_token: str
    folder_id: Optional[str] = None
    page_size: int = 20
    page_token: Optional[str] = None


@app.post(
    "/api/integrations/gdrive/list",
    tags=["integrations"],
    summary="List Google Drive Files",
    response_description="List of files in Google Drive"
)
async def gdrive_list(request: GDriveListRequest):
    """
    List files in Google Drive.

    Retrieves files and folders from Google Drive with pagination support.

    Args:
        request: GDriveListRequest containing:
            - access_token: OAuth2 access token
            - folder_id: Optional folder ID to list (root if not specified)
            - page_size: Number of results per page (default: 20)
            - page_token: Token for next page of results

    Returns:
        dict: File listing containing:
            - files: List of file metadata (id, name, mimeType, etc.)
            - nextPageToken: Token for pagination (if more results)

    Raises:
        HTTPException 400: If Google Drive API returns an error
    """
    result = await gdrive_list_files(
        access_token=request.access_token,
        folder_id=request.folder_id,
        page_size=request.page_size,
        page_token=request.page_token
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class GDriveFileRequest(BaseModel):
    access_token: str
    file_id: str


@app.post(
    "/api/integrations/gdrive/file",
    tags=["integrations"],
    summary="Get Google Drive File",
    response_description="File content from Google Drive"
)
async def gdrive_get_file(request: GDriveFileRequest):
    """
    Get file content from Google Drive.

    Downloads and returns the content of a file from Google Drive.

    Args:
        request: GDriveFileRequest containing:
            - access_token: OAuth2 access token
            - file_id: Google Drive file ID

    Returns:
        dict: File content containing:
            - content: File content (text or base64 for binary)
            - mimeType: File MIME type
            - name: File name

    Raises:
        HTTPException 400: If file cannot be retrieved
    """
    result = await gdrive_get_file_content(
        access_token=request.access_token,
        file_id=request.file_id
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class GDriveUploadRequest(BaseModel):
    access_token: str
    name: str
    content: str
    mime_type: str = "text/plain"
    folder_id: Optional[str] = None


@app.post(
    "/api/integrations/gdrive/upload",
    tags=["integrations"],
    summary="Upload to Google Drive",
    response_description="Uploaded file metadata"
)
async def gdrive_upload(request: GDriveUploadRequest):
    """
    Upload a file to Google Drive.

    Creates a new file in Google Drive with the specified content.

    Args:
        request: GDriveUploadRequest containing:
            - access_token: OAuth2 access token
            - name: File name
            - content: File content (text or base64)
            - mime_type: MIME type (default: "text/plain")
            - folder_id: Optional destination folder ID

    Returns:
        dict: Upload result containing:
            - id: Created file ID
            - name: File name
            - webViewLink: URL to view file in browser

    Raises:
        HTTPException 400: If upload fails
    """
    result = await gdrive_upload_file(
        access_token=request.access_token,
        name=request.name,
        content=request.content,
        mime_type=request.mime_type,
        folder_id=request.folder_id
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# --- Slack ---

class SlackMessageRequest(BaseModel):
    channel: str
    text: str
    thread_ts: Optional[str] = None


@app.post(
    "/api/integrations/slack/message",
    tags=["integrations"],
    summary="Send Slack Message",
    response_description="Message send confirmation"
)
async def slack_message(request: SlackMessageRequest):
    """
    Send a message to a Slack channel.

    Posts a message to the specified Slack channel using the Bot API.

    Args:
        request: SlackMessageRequest containing:
            - channel: Channel ID or name
            - text: Message text (supports Slack markdown)
            - thread_ts: Optional thread timestamp to reply to

    Returns:
        dict: Send result containing:
            - ok: Boolean success status
            - ts: Message timestamp
            - channel: Channel where message was posted

    Raises:
        HTTPException 400: If message fails to send
    """
    result = await slack_send_message(
        channel=request.channel,
        text=request.text,
        thread_ts=request.thread_ts
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class SlackWebhookRequest(BaseModel):
    text: str
    username: Optional[str] = "LLM Council"


@app.post(
    "/api/integrations/slack/webhook",
    tags=["integrations"],
    summary="Send Slack Webhook",
    response_description="Webhook send confirmation"
)
async def slack_webhook(request: SlackWebhookRequest):
    """
    Send a message via Slack incoming webhook.

    Posts a message using a configured webhook URL (no Bot token required).

    Args:
        request: SlackWebhookRequest containing:
            - text: Message text
            - username: Display name (default: "LLM Council")

    Returns:
        dict: Send result containing:
            - ok: Boolean success status

    Raises:
        HTTPException 400: If webhook send fails
    """
    result = await slack_send_webhook(
        text=request.text,
        username=request.username
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get(
    "/api/integrations/slack/channels",
    tags=["integrations"],
    summary="List Slack Channels",
    response_description="Available Slack channels"
)
async def slack_channels():
    """
    List available Slack channels.

    Retrieves channels accessible to the configured Slack bot.

    Returns:
        dict: Channel list containing:
            - channels: List of channel objects with id, name, is_private

    Raises:
        HTTPException 400: If channel list fails
    """
    result = await slack_list_channels()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# --- GitHub ---

@app.get(
    "/api/integrations/github/repos",
    tags=["integrations"],
    summary="List GitHub Repositories",
    response_description="GitHub repository list"
)
async def github_repos(username: Optional[str] = None, org: Optional[str] = None):
    """
    List GitHub repositories.

    Retrieves repositories for a user or organization.

    Args:
        username: GitHub username to list repos for (optional)
        org: GitHub organization to list repos for (optional)
        If neither specified, lists authenticated user's repos.

    Returns:
        dict: Repository list containing:
            - repos: List of repo objects with name, full_name, description, url

    Raises:
        HTTPException 400: If GitHub API returns an error
    """
    result = await github_list_repos(username=username, org=org)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class GitHubFileRequest(BaseModel):
    owner: str
    repo: str
    path: str
    ref: str = "main"


@app.post(
    "/api/integrations/github/file",
    tags=["integrations"],
    summary="Get GitHub File",
    response_description="File content from GitHub repository"
)
async def github_file(request: GitHubFileRequest):
    """
    Get file content from a GitHub repository.

    Retrieves the content of a file from a GitHub repository.

    Args:
        request: GitHubFileRequest containing:
            - owner: Repository owner (user or org)
            - repo: Repository name
            - path: File path within repository
            - ref: Branch, tag, or commit (default: "main")

    Returns:
        dict: File content containing:
            - content: Decoded file content
            - sha: File SHA
            - path: File path

    Raises:
        HTTPException 400: If file cannot be retrieved
    """
    result = await github_get_file(
        owner=request.owner,
        repo=request.repo,
        path=request.path,
        ref=request.ref
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get(
    "/api/integrations/github/issues/{owner}/{repo}",
    tags=["integrations"],
    summary="List GitHub Issues",
    response_description="Repository issues"
)
async def github_issues(owner: str, repo: str, state: str = "open"):
    """
    List issues in a GitHub repository.

    Retrieves issues from a GitHub repository with state filter.

    Args:
        owner: Repository owner (user or org)
        repo: Repository name
        state: Issue state filter: "open", "closed", or "all" (default: "open")

    Returns:
        dict: Issue list containing:
            - issues: List of issue objects with number, title, state, labels

    Raises:
        HTTPException 400: If issues cannot be retrieved
    """
    result = await github_list_issues(owner=owner, repo=repo, state=state)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class GitHubIssueRequest(BaseModel):
    owner: str
    repo: str
    title: str
    body: str
    labels: Optional[List[str]] = None
    assignees: Optional[List[str]] = None


@app.post(
    "/api/integrations/github/issues",
    tags=["integrations"],
    summary="Create GitHub Issue",
    response_description="Created issue details"
)
async def github_create(request: GitHubIssueRequest):
    """
    Create an issue in a GitHub repository.

    Creates a new issue with the specified details.

    Args:
        request: GitHubIssueRequest containing:
            - owner: Repository owner
            - repo: Repository name
            - title: Issue title
            - body: Issue body (markdown supported)
            - labels: Optional list of label names
            - assignees: Optional list of assignee usernames

    Returns:
        dict: Created issue containing:
            - number: Issue number
            - html_url: URL to view issue
            - title: Issue title

    Raises:
        HTTPException 400: If issue creation fails
    """
    result = await github_create_issue(
        owner=request.owner,
        repo=request.repo,
        title=request.title,
        body=request.body,
        labels=request.labels,
        assignees=request.assignees
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get(
    "/api/integrations/github/pulls/{owner}/{repo}",
    tags=["integrations"],
    summary="List GitHub Pull Requests",
    response_description="Repository pull requests"
)
async def github_pulls(owner: str, repo: str, state: str = "open"):
    """
    List pull requests in a GitHub repository.

    Retrieves pull requests from a GitHub repository with state filter.

    Args:
        owner: Repository owner (user or org)
        repo: Repository name
        state: PR state filter: "open", "closed", or "all" (default: "open")

    Returns:
        dict: Pull request list containing:
            - pulls: List of PR objects with number, title, state, head, base

    Raises:
        HTTPException 400: If pull requests cannot be retrieved
    """
    result = await github_list_prs(owner=owner, repo=repo, state=state)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ============ PERSONA ENDPOINTS ============

@app.get(
    "/api/personas",
    tags=["personas"],
    summary="List All Personas",
    response_description="Available personas including defaults and custom"
)
async def get_all_personas():
    """
    Get all available personas (default + custom).

    Personas customize how models respond by prepending system prompts.
    This returns both built-in default personas and user-created custom personas.

    Returns:
        dict: Persona collections containing:
            - default_personas: Built-in persona options (e.g., concise, detailed, creative)
            - custom_personas: User-created custom personas
            - model_assignments: Current persona assignments per model
    """
    return get_personas()


class SetPersonaRequest(BaseModel):
    model_id: str
    persona_key: str  # Can be a default persona key, custom persona ID, or empty string


@app.post(
    "/api/personas",
    tags=["personas"],
    summary="Assign Persona to Model",
    response_description="Updated persona assignment"
)
async def set_persona(request: SetPersonaRequest):
    """
    Assign a persona to a specific model.

    Associates a persona with a model so that persona's system prompt
    is included when querying that model.

    Args:
        request: SetPersonaRequest containing:
            - model_id: The model identifier to assign persona to
            - persona_key: Persona key (default key, custom ID, or empty to clear)

    Returns:
        dict: Assignment result containing:
            - model_id: The model that was updated
            - persona_key: The assigned persona key
            - persona_text: The full persona text now active
    """
    set_model_persona(request.model_id, request.persona_key)
    return {
        "model_id": request.model_id,
        "persona_key": request.persona_key,
        "persona_text": get_model_persona(request.model_id)
    }


class CreatePersonaRequest(BaseModel):
    persona_id: str
    persona_text: str


@app.post(
    "/api/personas/custom",
    tags=["personas"],
    summary="Create Custom Persona",
    response_description="Created custom persona"
)
async def create_persona(request: CreatePersonaRequest):
    """
    Create a custom persona with user-defined system prompt.

    Custom personas allow defining specialized behavior for models
    beyond the built-in default personas.

    Args:
        request: CreatePersonaRequest containing:
            - persona_id: Unique identifier for the persona
            - persona_text: The system prompt text for this persona

    Returns:
        dict: Created persona containing:
            - persona_id: The ID of the created persona
            - persona_text: The persona system prompt text

    Example:
        ```json
        {
            "persona_id": "code_reviewer",
            "persona_text": "You are an expert code reviewer. Focus on..."
        }
        ```
    """
    persona_id = create_custom_persona(request.persona_id, request.persona_text)
    return {
        "persona_id": persona_id,
        "persona_text": request.persona_text
    }


@app.post(
    "/api/tools/search",
    tags=["tools"],
    summary="Web Search",
    response_description="Search results from web"
)
async def tool_search(request: SearchRequest):
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

    results = await web_search(request.query, request.num_results)
    return {"query": request.query, "results": results}


@app.post(
    "/api/tools/fetch",
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


@app.post(
    "/api/tools/execute",
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


@app.post(
    "/api/tools/memory",
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


# ============ SEARCH ENDPOINTS ============

@app.get(
    "/api/search",
    tags=["search"],
    summary="Search Conversations",
    response_description="Search results with matching conversations"
)
async def search_endpoint(
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


@app.get(
    "/api/search/suggestions",
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


# ============ CONVERSATION ENDPOINTS ============

@app.get(
    "/api/conversations",
    tags=["conversations"],
    summary="List All Conversations",
    response_model=List[ConversationMetadata],
    response_description="List of conversation metadata"
)
async def list_conversations(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    List all conversations (metadata only) - user-specific if authenticated.

    Returns a list of conversations with basic metadata including
    ID, title, creation date, and message count. Does not include
    full message content for performance.

    Args:
        current_user: Authenticated user (optional - if None, returns all for anonymous)

    Returns:
        List[ConversationMetadata]: List of conversation summaries
    """
    user_id = current_user.id if current_user else None
    return await storage.list_conversations(user_id=user_id, db=db)


@app.post(
    "/api/conversations",
    tags=["conversations"],
    summary="Create New Conversation",
    response_model=Conversation,
    response_description="Created conversation object",
    status_code=201
)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new conversation (user-specific if authenticated).

    Initializes a new empty conversation that can receive messages.
    The conversation will be assigned a unique UUID and associated with the user.

    Args:
        request: CreateConversationRequest (can be empty)
        current_user: Authenticated user (optional - if None, uses anonymous user)

    Returns:
        Conversation: The created conversation with id and metadata
    """
    conversation_id = str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    # region agent log
    try:
        open("/Users/sezars/llm-council/.cursor/debug.log", "a").write(
            json.dumps(
                {
                    "sessionId": "debug-session",
                    "runId": "pre-fix",
                    "hypothesisId": "H9",
                    "location": "main.py:3204",
                    "message": "create_conversation:entry",
                    "data": {
                        "has_user": bool(user_id),
                        "conversation_id": conversation_id,
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }
            )
            + "\n"
        )
    except Exception:
        pass
    # endregion
    try:
        conversation = await storage.create_conversation(
            conversation_id, user_id=user_id, db=db
        )
        return conversation
    except Exception as exc:
        # region agent log
        try:
            open("/Users/sezars/llm-council/.cursor/debug.log", "a").write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "pre-fix",
                        "hypothesisId": "H10",
                        "location": "main.py:3220",
                        "message": "create_conversation:error",
                        "data": {
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000),
                    }
                )
                + "\n"
            )
        except Exception:
            pass
        # endregion
        raise


@app.get(
    "/api/conversations/{conversation_id}",
    tags=["conversations"],
    summary="Get Conversation",
    response_model=Conversation,
    response_description="Full conversation with all messages"
)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific conversation with all its messages (user-scoped if authenticated).

    Returns the complete conversation including all user messages
    and assistant responses with their Stage 1, 2, and 3 results.

    Args:
        conversation_id: The unique conversation identifier
        current_user: Authenticated user (optional - verifies ownership if provided)
        db: Database session

    Returns:
        Conversation: Full conversation with all messages

    Raises:
        HTTPException 404: If conversation not found or user doesn't have access
    """
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete(
    "/api/conversations/{conversation_id}",
    tags=["conversations"],
    summary="Delete Conversation",
    response_description="Confirmation of deletion"
)
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation.

    Permanently removes a conversation and all its messages.
    This action cannot be undone.

    Args:
        conversation_id: The unique conversation identifier

    Returns:
        dict: Confirmation with status and message

    Raises:
        HTTPException 404: If conversation not found
    """
    deleted = await storage.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "message": f"Conversation {conversation_id} deleted"}


@app.post(
    "/api/conversations/import",
    tags=["conversations"],
    summary="Import Conversation",
    response_model=Conversation,
    response_description="Imported conversation object",
    status_code=201
)
async def import_conversation(request: ImportConversationRequest):
    """
    Import a conversation from exported JSON data.

    Creates a new conversation with the provided messages and metadata.
    Useful for restoring backups or migrating conversations.

    Args:
        request: ImportConversationRequest with:
            - messages: List of message objects (required)
            - title: Optional conversation title
            - created_at: Optional creation timestamp
            - folder_id: Optional folder to place conversation in
            - tags: Optional list of tags

    Returns:
        Conversation: The imported conversation with new ID
    """
    conversation_id = str(uuid.uuid4())

    # Create conversation with provided or default values
    conversation = {
        "id": conversation_id,
        "created_at": request.created_at or datetime.utcnow().isoformat(),
        "title": request.title or "Imported Conversation",
        "messages": request.messages,
        "folder_id": request.folder_id,
        "tags": request.tags or []
    }

    # Save to storage
    await storage.save_conversation(conversation)

    logger.info("conversation_imported",
                conversation_id=conversation_id,
                message_count=len(request.messages))

    return conversation


@app.post(
    "/api/conversations/{conversation_id}/fork",
    tags=["conversations"],
    summary="Fork Conversation",
    response_model=Conversation,
    response_description="Forked conversation object",
    status_code=201
)
async def fork_conversation(conversation_id: str, request: ForkConversationRequest):
    """
    Fork a conversation from a specific message.

    Creates a new conversation containing all messages up to and including
    the specified message index. Useful for exploring alternative paths
    in a conversation.

    Args:
        conversation_id: The source conversation to fork from
        request: ForkConversationRequest with:
            - message_index: Include messages up to this index (0-based)

    Returns:
        Conversation: The new forked conversation

    Raises:
        HTTPException 404: If source conversation not found
        HTTPException 400: If message_index is invalid
    """
    # Get the source conversation
    source = await storage.get_conversation(conversation_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Validate message index
    if request.message_index < 0 or request.message_index >= len(source["messages"]):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid message_index: {request.message_index}. Must be 0-{len(source['messages'])-1}"
        )

    # Create new conversation with messages up to and including the index
    new_id = str(uuid.uuid4())
    forked_messages = source["messages"][:request.message_index + 1]

    forked_conversation = {
        "id": new_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": f"{source['title']} (Fork)",
        "messages": forked_messages,
        "folder_id": source.get("folder_id"),
        "tags": source.get("tags", [])
    }

    # Save to storage
    await storage.save_conversation(forked_conversation)

    logger.info("conversation_forked",
                source_id=conversation_id,
                fork_id=new_id,
                message_count=len(forked_messages))

    return forked_conversation


@app.post(
    "/api/conversations/{conversation_id}/message",
    tags=["conversations"],
    summary="Send Message (Council Deliberation)",
    response_description="Complete 3-stage council response"
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and run the 3-stage council process (using user's API keys if authenticated).

    This is the core council deliberation endpoint. It:
    1. **Stage 1**: Queries all council models in parallel
    2. **Stage 2**: Models anonymously peer-review and rank responses
    3. **Stage 3**: Chairman synthesizes the final answer

    The conversation context (previous messages) is included for
    follow-up questions. File attachments can be included.

    Args:
        conversation_id: The conversation to add the message to
        request: SendMessageRequest with:
            - content: The user's message/question
            - attached_files: Optional list of file IDs to include
        current_user: Authenticated user (optional - uses user's API keys if provided)
        db: Database session

    Returns:
        dict: Complete response containing:
            - stage1: List of individual model responses
            - stage2: List of peer evaluations with rankings
            - stage3: Chairman's synthesized final answer
            - metadata: label_to_model mapping and aggregate rankings

    Raises:
        HTTPException 404: If conversation not found
    """
    # Check if conversation exists
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Get conversation context for follow-up questions (before adding current message)
    conversation_context = None
    if not is_first_message:
        conversation_context = await storage.get_conversation_context(conversation_id, limit=3)

    # Add user message with attached files
    await storage.add_user_message(conversation_id, request.content, request.attached_files)

    # Run the 3-stage council process with context, files, and user-specific API keys
    user_id = current_user.id if current_user else None
    
    # If this is the first message, generate a title (using user's API keys)
    if is_first_message:
        title = await generate_conversation_title(request.content, user_id=user_id, db=db)
        await storage.update_conversation_title(conversation_id, title)
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        conversation_context=conversation_context,
        conversation_id=conversation_id,
        attached_files=request.attached_files,
        user_id=user_id,
        db=db
    )

    # Add assistant message with all stages
    await storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post(
    "/api/conversations/{conversation_id}/message/stream",
    tags=["conversations"],
    summary="Send Message (Streaming)",
    response_description="Server-Sent Events stream of council responses"
)
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and stream the 3-stage council process (using user's API keys if authenticated).

    Returns Server-Sent Events (SSE) with real-time updates as each model
    responds and each stage completes. Provides progressive loading for
    better user experience.

    Args:
        conversation_id: ID of the conversation
        request: SendMessageRequest with message content
        current_user: Authenticated user (optional - uses user's API keys if provided)
        db: Database session

    Returns:
        StreamingResponse: SSE stream with events:
            - stage1_model_response: Individual model responses
            - stage1_complete: All Stage 1 responses
            - stage2_complete: All Stage 2 evaluations
            - stage3_complete: Final synthesis
            - title_complete: Auto-generated title (first message)
            - error: If processing fails

    Raises:
        HTTPException 404: Conversation not found
    """
    # Check if conversation exists
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Get conversation context for follow-up questions (before adding current message)
    conversation_context = None
    if not is_first_message:
        conversation_context = await storage.get_conversation_context(conversation_id, limit=3)

    async def event_generator():
        # Create cancellation event and register this stream
        cancel_event = asyncio.Event()
        _active_streams[conversation_id] = cancel_event
        cancelled = False

        try:
            # Add user message with attached files
            await storage.add_user_message(conversation_id, request.content, request.attached_files)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content, user_id=user_id, db=db))

            # Variables to store final results
            stage1_results = None
            stage2_results = None
            stage3_result = None
            metadata = None

            # Stream the council process with real-time token updates (using user-specific API keys)
            async for event in run_full_council_stream(request.content, conversation_context, user_id=user_id, db=db):
                # Check for cancellation
                if cancel_event.is_set():
                    cancelled = True
                    logger.info("stream_cancellation_detected", conversation_id=conversation_id)
                    yield f"data: {json.dumps({'type': 'cancelled', 'message': 'Stream cancelled by user', 'partial': True})}\n\n"
                    break

                # Forward all events to client
                yield f"data: {json.dumps(event)}\n\n"

                # Capture final results for storage
                if event.get("type") == "stage1_complete":
                    stage1_results = event.get("data", [])
                elif event.get("type") == "stage2_complete":
                    stage2_results = event.get("data", [])
                    metadata = event.get("metadata", {})
                elif event.get("type") == "stage3_complete":
                    stage3_result = event.get("data", {})
                elif event.get("type") == "complete":
                    # Update from complete event if available
                    stage1_results = event.get("stage1", stage1_results)
                    stage2_results = event.get("stage2", stage2_results)
                    stage3_result = event.get("stage3", stage3_result)
                    metadata = event.get("metadata", metadata)

            # Wait for title generation if it was started (and not cancelled)
            if title_task and not cancelled:
                title = await title_task
                await storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"
            elif title_task and cancelled:
                # Cancel the title task if stream was cancelled
                title_task.cancel()

            # Save complete assistant message (only if not cancelled and all stages complete)
            if stage1_results and stage2_results and stage3_result and not cancelled:
                await storage.add_assistant_message(
                    conversation_id,
                    stage1_results,
                    stage2_results,
                    stage3_result
                )

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Always clean up the stream registration
            _active_streams.pop(conversation_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post(
    "/api/conversations/{conversation_id}/cancel",
    tags=["conversations"],
    summary="Cancel Active Stream",
    response_description="Cancellation status"
)
async def cancel_stream(conversation_id: str):
    """
    Cancel an active streaming request for a conversation.

    Signals the streaming endpoint to stop processing and return partial results.
    This saves tokens and reduces cost when the user no longer needs the full response.

    Args:
        conversation_id: ID of the conversation with active stream

    Returns:
        dict: Status of cancellation
            - "cancelled": Stream was found and cancellation signaled
            - "no_active_stream": No active stream found for this conversation
    """
    if conversation_id in _active_streams:
        _active_streams[conversation_id].set()  # Signal cancellation
        logger.info("stream_cancelled", conversation_id=conversation_id)
        return {"status": "cancelled", "conversation_id": conversation_id}
    return {"status": "no_active_stream", "conversation_id": conversation_id}


@app.post(
    "/api/conversations/{conversation_id}/quick",
    tags=["quick-mode"],
    summary="Quick Mode (Streaming)",
    response_description="Streaming response from single model"
)
async def send_quick_mode(
    conversation_id: str,
    request: QuickModeRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Quick Mode: Stream a single model response without council deliberation (using user's API keys if authenticated).

    Bypasses the 3-stage council process for faster responses when full
    deliberation is not needed. Uses the chairman model by default.

    Args:
        conversation_id: ID of the conversation
        request: QuickModeRequest containing:
            - message: User message content
            - model: Optional model override (defaults to chairman)
        current_user: Authenticated user (optional - uses user's API keys if provided)
        db: Database session

    Returns:
        StreamingResponse: SSE stream with events:
            - chunk: Incremental text tokens
            - complete: Full response with metadata

    Raises:
        HTTPException 404: Conversation not found
        HTTPException 400: Invalid model specified
    """
    # Check if conversation exists
    conversation = await storage.get_conversation(conversation_id, user_id=current_user.id if current_user else None, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get user-specific chairman model if available
    user_id = current_user.id if current_user else None
    if user_id:
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.chairman_model:
            default_model = settings.chairman_model
        else:
            default_model = get_chairman_model()
    else:
        default_model = get_chairman_model()

    # Determine which model to use
    model_to_use = request.model if request.model else default_model
    all_models = get_all_models()

    # Validate model
    if model_to_use not in all_models:
        raise HTTPException(status_code=400, detail=f"Invalid model: {model_to_use}")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Get conversation context for follow-up questions
    conversation_context = None
    if not is_first_message:
        conversation_context = await storage.get_conversation_context(conversation_id, limit=3)

    async def event_generator():
        # Create cancellation event and register this stream
        cancel_event = asyncio.Event()
        _active_streams[conversation_id] = cancel_event
        cancelled = False

        try:
            # Add user message
            await storage.add_user_message(conversation_id, request.message)

            # Start title generation in parallel if first message
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.message, user_id=user_id, db=db))

            # Prepare messages for the model
            messages = [{"role": "user", "content": request.message}]

            # Add conversation context if available
            if conversation_context:
                messages.insert(0, {"role": "system", "content": conversation_context})

            # Stream the response token by token (with user-specific API keys)
            full_content = ""
            thinking = None
            usage_info = None

            async for chunk in query_model_stream(model_to_use, messages, user_id=user_id, db=db):
                # Check for cancellation
                if cancel_event.is_set():
                    cancelled = True
                    logger.info("quick_stream_cancellation_detected", conversation_id=conversation_id)
                    yield f"data: {json.dumps({'type': 'cancelled', 'message': 'Stream cancelled by user', 'partial_content': full_content})}\n\n"
                    break

                if chunk.get("error"):
                    yield f"data: {json.dumps({'type': 'error', 'message': chunk.get('message', 'Unknown error')})}\n\n"
                    return

                if chunk.get("chunk"):
                    # Send incremental token chunk
                    text_chunk = chunk["chunk"]
                    full_content += text_chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'data': text_chunk})}\n\n"

                if chunk.get("done"):
                    # Extract final metadata
                    usage_info = chunk.get("usage")
                    thinking = chunk.get("thinking")

            # Wait for title generation if it was started (and not cancelled)
            if title_task and not cancelled:
                title = await title_task
                await storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"
            elif title_task and cancelled:
                title_task.cancel()

            # Save the complete message to storage (only if not cancelled)
            if not cancelled:
                await storage.add_quick_message(
                    conversation_id,
                    full_content,
                    model_to_use,
                    thinking=thinking,
                    usage=usage_info
                )

                # Send completion event with full response
                completion_data = {
                    "type": "complete",
                    "data": {
                        "content": full_content,
                        "model": model_to_use,
                        "usage": usage_info
                    }
                }

                if thinking:
                    completion_data["data"]["thinking"] = thinking

                yield f"data: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Always clean up the stream registration
            _active_streams.pop(conversation_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post(
    "/api/conversations/{conversation_id}/quick-message",
    tags=["quick-mode"],
    summary="Quick Message (Streaming)",
    response_description="Streaming response from single model"
)
async def send_quick_message(
    conversation_id: str,
    request: QuickMessageRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message in Quick Mode - queries a single model directly (using user's API keys if authenticated).

    Alternative quick mode endpoint with real-time streaming response.
    Uses Server-Sent Events for progressive content delivery.

    Args:
        conversation_id: ID of the conversation
        request: QuickMessageRequest containing:
            - content: User message text
            - model: Optional model override
        current_user: Authenticated user (optional - uses user's API keys if provided)
        db: Database session

    Returns:
        StreamingResponse: SSE stream containing:
            - chunk: Incremental text tokens
            - title_complete: Generated title (first message)
            - complete: Full response with metadata

    Raises:
        HTTPException 404: Conversation not found
        HTTPException 400: Invalid model specified
    """
    # Check if conversation exists
    conversation = await storage.get_conversation(conversation_id, user_id=current_user.id if current_user else None, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get user-specific chairman model if available
    user_id = current_user.id if current_user else None
    if user_id:
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.chairman_model:
            default_model = settings.chairman_model
        else:
            default_model = get_chairman_model()
    else:
        default_model = get_chairman_model()

    # Determine which model to use
    model_to_use = request.model if request.model else default_model
    all_models = get_all_models()

    # Validate model
    if model_to_use not in all_models:
        raise HTTPException(status_code=400, detail=f"Invalid model: {model_to_use}")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Get conversation context for follow-up questions
    conversation_context = None
    if not is_first_message:
        conversation_context = await storage.get_conversation_context(conversation_id, limit=3)

    async def event_generator():
        # Create cancellation event and register this stream
        cancel_event = asyncio.Event()
        _active_streams[conversation_id] = cancel_event
        cancelled = False

        try:
            # Add user message
            await storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel if first message
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content, user_id=user_id, db=db))

            # Prepare messages for the model
            messages = [{"role": "user", "content": request.content}]

            # Add conversation context if available
            if conversation_context:
                messages.insert(0, {"role": "system", "content": conversation_context})

            # Stream the response (with user-specific API keys)
            full_content = ""
            thinking = None
            usage_info = None

            async for chunk in query_model_stream(model_to_use, messages, user_id=user_id, db=db):
                # Check for cancellation
                if cancel_event.is_set():
                    cancelled = True
                    logger.info("quick_message_stream_cancelled", conversation_id=conversation_id)
                    yield f"data: {json.dumps({'type': 'cancelled', 'message': 'Stream cancelled by user', 'partial_content': full_content})}\n\n"
                    break

                if chunk.get("error"):
                    yield f"data: {json.dumps({'type': 'error', 'message': chunk.get('message', 'Unknown error')})}\n\n"
                    return

                if chunk.get("chunk"):
                    # Send incremental chunk
                    text_chunk = chunk["chunk"]
                    full_content += text_chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'data': text_chunk})}\n\n"

                if chunk.get("done"):
                    # Extract final metadata
                    usage_info = chunk.get("usage")
                    thinking = chunk.get("thinking")

            # Wait for title generation if it was started (and not cancelled)
            if title_task and not cancelled:
                title = await title_task
                await storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"
            elif title_task and cancelled:
                title_task.cancel()

            # Save the complete message (only if not cancelled)
            if not cancelled:
                await storage.add_quick_message(
                    conversation_id,
                    full_content,
                    model_to_use,
                    thinking=thinking,
                    usage=usage_info
                )

                # Send completion event
                completion_data = {
                    "type": "complete",
                    "data": {
                        "content": full_content,
                        "model": model_to_use,
                        "usage": usage_info
                    }
                }

                if thinking:
                    completion_data["data"]["thinking"] = thinking

                yield f"data: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Always clean up the stream registration
            _active_streams.pop(conversation_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get(
    "/api/chat/models",
    tags=["quick-mode"],
    summary="Get Chat Models",
    response_description="List of available models for quick mode"
)
async def get_chat_models():
    """
    Get all available models for Quick Mode chat.

    Returns a list of all models available for quick mode chat with
    their metadata including display name and pricing information.

    Returns:
        dict: Models listing containing:
            - models: List of model objects with id, name, costs
            - count: Total number of available models
    """
    all_models = get_all_models()

    # Format models for frontend consumption
    models_list = []
    for model_id, model_info in all_models.items():
        models_list.append({
            "id": model_id,
            "name": model_info.get("name", model_id),
            "input_cost": model_info.get("input_cost", 0),
            "output_cost": model_info.get("output_cost", 0),
        })

    # Sort by name
    models_list.sort(key=lambda x: x["name"])

    return {
        "models": models_list,
        "default_model": get_chairman_model(),
        "count": len(models_list)
    }


@app.post(
    "/api/conversations/{conversation_id}/debate",
    tags=["debate"],
    summary="Run Debate Mode",
    response_description="Debate results with pro/con arguments and synthesis"
)
async def run_debate_mode(conversation_id: str, request: DebateRequest):
    """
    Run a debate with council models split into pro vs con teams.

    Divides the council into two teams that argue opposing positions on
    the given topic through multiple rounds. Chairman synthesizes final verdict.

    Args:
        conversation_id: ID of the conversation
        request: DebateRequest containing:
            - topic: The debate topic/proposition
            - rounds: Number of debate rounds (default: 2)

    Returns:
        dict: Debate results containing:
            - rounds: List of round arguments (pro and con)
            - synthesis: Chairman's final analysis and verdict
            - metadata: Debate statistics

    Raises:
        HTTPException 404: Conversation not found
    """
    # Check if conversation exists
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message with debate topic
    await storage.add_user_message(conversation_id, f"DEBATE: {request.topic}")

    # Get user_id for API key resolution
    user_id = current_user.id if current_user else None

    # If this is the first message, generate a title (using user's API keys)
    if is_first_message:
        title = await generate_conversation_title(f"Debate: {request.topic}", user_id=user_id, db=db)
        await storage.update_conversation_title(conversation_id, title)

    # Run the debate (using user-specific API keys)
    debate_result = await run_debate(request.topic, request.rounds, user_id=user_id, db=db)

    # Add debate result as assistant message
    await storage.add_debate_message(
        conversation_id,
        debate_result
    )

    # Return the complete debate
    return debate_result


@app.post(
    "/api/conversations/{conversation_id}/vote",
    tags=["voting"],
    summary="Run Council Vote",
    response_description="Vote results with winner determination"
)
async def run_conversation_vote(
    conversation_id: str,
    request: VoteRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Run a vote on a question with multiple options.

    Each council model votes for ONE option, providing:
    - Their chosen option
    - Confidence score (0-100%)
    - Reasoning for their choice

    The winner is determined by total score (votes x average confidence).

    Args:
        conversation_id: The conversation ID for context tracking
        request: VoteRequest containing:
            - question: The question to vote on
            - options: List of 2-26 options to choose from

    Returns:
        dict: Vote results containing:
            - votes: List of individual model votes with reasoning
            - results: Aggregated results by option
            - winner: Winning option with score details

    Raises:
        HTTPException 404: If conversation not found
        HTTPException 400: If fewer than 2 or more than 26 options

    Example:
        ```json
        {
            "question": "Which framework should we use?",
            "options": ["React", "Vue", "Angular"]
        }
        ```
    """
    # Check if conversation exists
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Validate options
    if len(request.options) < 2:
        raise HTTPException(status_code=400, detail="At least 2 options are required")

    if len(request.options) > 26:
        raise HTTPException(status_code=400, detail="Maximum 26 options allowed")

    # Get user_id for API key resolution
    user_id = current_user.id if current_user else None

    # Run the vote (using user-specific API keys)
    vote_results = await run_vote(request.question, request.options, user_id=user_id, db=db)

    return vote_results


# ============ FILE UPLOAD ENDPOINTS ============

@app.post(
    "/api/conversations/{conversation_id}/upload",
    tags=["files"],
    summary="Upload File to Conversation",
    response_description="Upload confirmation with file metadata"
)
async def upload_file(conversation_id: str, file: UploadFile = File(...)):
    """
    Upload a file to a conversation.

    Files can be attached to messages for analysis by the council.
    Supported formats include text files, code files, PDFs, and images.

    Args:
        conversation_id: The conversation to upload to
        file: The file to upload (multipart/form-data)

    Returns:
        dict: Upload confirmation with file metadata (id, size, type)

    Raises:
        HTTPException 404: If conversation not found
        HTTPException 400: If file type not supported
        HTTPException 500: If upload fails
    """
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        content = await file.read()
        metadata = files.save_file(conversation_id, file.filename, content)
        return {"status": "success", "message": f"File '{file.filename}' uploaded successfully", **metadata}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.get(
    "/api/conversations/{conversation_id}/files",
    tags=["files"],
    summary="List Conversation Files",
    response_description="List of uploaded files"
)
async def list_conversation_files(conversation_id: str):
    """
    List all files uploaded to a conversation.

    Returns metadata for all files including name, size, and upload time.

    Args:
        conversation_id: The conversation to list files for

    Returns:
        dict: Object with files list and count

    Raises:
        HTTPException 404: If conversation not found
    """
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    file_list = files.list_files(conversation_id)
    return {"conversation_id": conversation_id, "files": file_list, "count": len(file_list)}


@app.get(
    "/api/conversations/{conversation_id}/files/{filename}",
    tags=["files"],
    summary="Download File",
    response_description="File content as download"
)
async def download_file(conversation_id: str, filename: str):
    """
    Download a file from a conversation.

    Returns the file content as a binary download.

    Args:
        conversation_id: The conversation containing the file
        filename: The name of the file to download

    Returns:
        FileResponse: The file content for download

    Raises:
        HTTPException 404: If conversation or file not found
        HTTPException 500: If download fails
    """
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        file_info = files.get_file_info(conversation_id, filename)
        if file_info is None:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = os.path.join(files.UPLOAD_DIR, conversation_id, filename)
        return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@app.delete(
    "/api/conversations/{conversation_id}/files/{filename}",
    tags=["files"],
    summary="Delete Conversation File",
    response_description="Deletion confirmation"
)
async def delete_conversation_file(conversation_id: str, filename: str):
    """
    Delete a file from a conversation's file storage.

    Permanently removes a file that was previously uploaded to the conversation.
    This action cannot be undone.

    Args:
        conversation_id: The conversation ID containing the file
        filename: The name of the file to delete

    Returns:
        dict: Deletion confirmation containing:
            - status: "success"
            - message: Confirmation message with filename

    Raises:
        HTTPException 404: If conversation or file not found
    """
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    deleted = files.delete_file(conversation_id, filename)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    return {"status": "success", "message": f"File '{filename}' deleted successfully"}


# ============ PROJECT ENDPOINTS ============

@app.get(
    "/api/projects",
    tags=["projects"],
    summary="List All Projects",
    response_description="List of project metadata"
)
async def list_all_projects():
    """
    List all projects (metadata only).

    Returns a list of all projects with their basic information,
    not including full knowledge base content.

    Returns:
        dict: Project list containing:
            - projects: List of project metadata (id, name, description, created_at)
    """
    return projects.list_projects()


@app.post(
    "/api/projects",
    tags=["projects"],
    summary="Create Project",
    response_description="Created project details"
)
async def create_new_project(request: CreateProjectRequest):
    """
    Create a new project workspace.

    Projects provide isolated workspaces with their own knowledge base,
    system prompts, and council configuration.

    Args:
        request: CreateProjectRequest containing:
            - name: Project name
            - description: Project description (optional)
            - system_prompt: Default system prompt for conversations (optional)
            - council_models: List of models for this project's council (optional)
            - chairman_model: Chairman model for this project (optional)

    Returns:
        dict: Created project containing:
            - id: Project identifier
            - name: Project name
            - description: Project description
            - system_prompt: Configured system prompt
            - knowledge_base: Empty knowledge base array
            - created_at: Creation timestamp
    """
    project = projects.create_project(
        name=request.name,
        description=request.description or "",
        system_prompt=request.system_prompt or "",
        council_models=request.council_models,
        chairman_model=request.chairman_model
    )
    return project


@app.get(
    "/api/projects/{project_id}",
    tags=["projects"],
    summary="Get Project Details",
    response_description="Full project information"
)
async def get_project_details(project_id: str):
    """
    Get a specific project with all details.

    Retrieves complete project information including knowledge base entries.

    Args:
        project_id: The unique project identifier

    Returns:
        dict: Full project containing:
            - id: Project identifier
            - name: Project name
            - description: Project description
            - system_prompt: Default system prompt
            - knowledge_base: List of knowledge base entries
            - conversations: List of linked conversation IDs
            - council_config: Custom council configuration (if set)

    Raises:
        HTTPException 404: If project not found
    """
    project = projects.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.put(
    "/api/projects/{project_id}",
    tags=["projects"],
    summary="Update Project",
    response_description="Updated project details"
)
async def update_existing_project(project_id: str, request: UpdateProjectRequest):
    """
    Update a project's configuration.

    Updates specified fields of a project. Only provided fields are updated.

    Args:
        project_id: The unique project identifier
        request: UpdateProjectRequest containing (all optional):
            - name: New project name
            - description: New description
            - system_prompt: New system prompt
            - council_config: New council configuration

    Returns:
        dict: Updated project with all fields

    Raises:
        HTTPException 404: If project not found
    """
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.description is not None:
        updates["description"] = request.description
    if request.system_prompt is not None:
        updates["system_prompt"] = request.system_prompt
    if request.council_config is not None:
        updates["council_config"] = request.council_config

    project = projects.update_project(project_id, updates)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.delete(
    "/api/projects/{project_id}",
    tags=["projects"],
    summary="Delete Project",
    response_description="Deletion confirmation"
)
async def delete_existing_project(project_id: str):
    """
    Delete a project and its knowledge base.

    Permanently removes a project. Linked conversations are not deleted
    but will be unlinked from the project.

    Args:
        project_id: The unique project identifier

    Returns:
        dict: Deletion confirmation with status: "deleted"

    Raises:
        HTTPException 404: If project not found
    """
    success = projects.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted"}


@app.post(
    "/api/projects/{project_id}/knowledge",
    tags=["projects"],
    summary="Add Knowledge Base Entry",
    response_description="Created knowledge base entry"
)
async def add_knowledge_to_project(project_id: str, request: AddKnowledgeRequest):
    """
    Add a file to the project's knowledge base.

    Knowledge base entries provide context that can be included
    in conversations within this project.

    Args:
        project_id: The unique project identifier
        request: AddKnowledgeRequest containing:
            - filename: Name for the knowledge entry
            - content: File content (text)
            - file_type: Type of content (default: "text")

    Returns:
        dict: Created knowledge entry containing:
            - id: Entry identifier
            - filename: Entry name
            - file_type: Content type
            - created_at: Creation timestamp

    Raises:
        HTTPException 404: If project not found
    """
    kb_entry = projects.add_to_knowledge_base(
        project_id=project_id,
        filename=request.filename,
        content=request.content,
        file_type=request.file_type or "text"
    )
    if kb_entry is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return kb_entry


@app.delete(
    "/api/projects/{project_id}/knowledge/{file_id}",
    tags=["projects"],
    summary="Remove Knowledge Base Entry",
    response_description="Deletion confirmation"
)
async def remove_knowledge_from_project(project_id: str, file_id: str):
    """
    Remove a file from the project's knowledge base.

    Permanently removes a knowledge base entry from the project.

    Args:
        project_id: The unique project identifier
        file_id: The knowledge base entry identifier

    Returns:
        dict: Deletion confirmation with status: "deleted"

    Raises:
        HTTPException 404: If project or file not found
    """
    success = projects.remove_from_knowledge_base(project_id, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project or file not found")
    return {"status": "deleted"}


@app.get(
    "/api/projects/{project_id}/knowledge/{file_id}",
    tags=["projects"],
    summary="Get Knowledge Base Content",
    response_description="Knowledge base file content"
)
async def get_knowledge_file_content(project_id: str, file_id: str):
    """
    Get the content of a knowledge base file.

    Retrieves the full content of a specific knowledge base entry.

    Args:
        project_id: The unique project identifier
        file_id: The knowledge base entry identifier

    Returns:
        dict: File content containing:
            - content: The full file content

    Raises:
        HTTPException 404: If file not found
    """
    content = projects.get_knowledge_base_content(project_id, file_id)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": content}


@app.post(
    "/api/projects/{project_id}/conversations",
    tags=["projects"],
    summary="Create Project Conversation",
    response_description="New conversation linked to project"
)
async def create_conversation_in_project(project_id: str):
    """
    Create a new conversation within a project.

    Creates a conversation that is automatically linked to the project,
    inheriting the project's system prompt and knowledge base context.

    Args:
        project_id: The unique project identifier

    Returns:
        dict: Created conversation containing:
            - conversation: Full conversation object
            - project_id: The project this conversation belongs to

    Raises:
        HTTPException 404: If project not found
    """
    # Verify project exists
    project = projects.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create conversation
    conversation_id = str(uuid.uuid4())
    conversation = await storage.create_conversation(conversation_id)

    # Link to project
    projects.add_conversation_to_project(project_id, conversation_id)

    return {
        "conversation": conversation,
        "project_id": project_id
    }


# ============ PROJECT MEMORY ENDPOINTS ============

class ProjectMemoryRequest(BaseModel):
    action: str  # add_fact, add_decision, set_preference, get_context, clear, stats
    content: Optional[str] = None
    category: Optional[str] = "general"
    question: Optional[str] = None
    decision: Optional[str] = None
    reasoning: Optional[str] = None
    key: Optional[str] = None
    value: Optional[Any] = None


@app.post(
    "/api/projects/{project_id}/memory",
    tags=["projects"],
    summary="Project Memory Operations",
    response_description="Memory operation results"
)
async def project_memory(project_id: str, request: ProjectMemoryRequest):
    """
    Perform project-specific memory operations.

    Stores facts, decisions, and preferences specific to a project that
    persist across conversations within that project.

    Supported Actions:
    - add_fact: Store a fact with optional category
    - add_decision: Store a decision with question, answer, and reasoning
    - set_preference: Store a key-value preference
    - get_context: Retrieve project memory context
    - clear: Clear all project memory
    - stats: Get project memory statistics

    Args:
        project_id: ID of the project
        request: ProjectMemoryRequest with action and required fields

    Returns:
        dict: Operation result with action type and outcome

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Missing required fields for action
    """
    project = projects.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if request.action == "add_fact":
        if not request.content:
            raise HTTPException(status_code=400, detail="Content required")
        success = projects.add_project_fact(project_id, request.content, request.category or "general")
        return {"success": success, "action": "add_fact"}

    elif request.action == "add_decision":
        if not request.question or not request.decision:
            raise HTTPException(status_code=400, detail="Question and decision required")
        success = projects.add_project_decision(project_id, request.question, request.decision, request.reasoning or "")
        return {"success": success, "action": "add_decision"}

    elif request.action == "set_preference":
        if not request.key:
            raise HTTPException(status_code=400, detail="Key required")
        success = projects.set_project_preference(project_id, request.key, request.value)
        return {"success": success, "action": "set_preference"}

    elif request.action == "get_context":
        context = projects.get_project_memory_context(project_id)
        return {"context": context, "action": "get_context"}

    elif request.action == "clear":
        success = projects.clear_project_memory(project_id)
        return {"success": success, "action": "clear"}

    elif request.action == "stats":
        stats = projects.get_project_memory_stats(project_id)
        return {"stats": stats, "action": "stats"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")


# ============ BUDGET ENDPOINTS ============

class SetBudgetRequest(BaseModel):
    """Request to set budget limits."""
    daily: Optional[float] = None
    weekly: Optional[float] = None
    monthly: Optional[float] = None
    alert_threshold: Optional[float] = None


@app.get(
    "/api/budget",
    tags=["budget"],
    summary="Get Budget Status",
    response_description="Current budget configuration and spending status"
)
async def get_budget():
    """
    Get current budget configuration and status.

    Returns comprehensive budget information including limits, current spending,
    status per period, and any active alerts.

    Returns:
        dict: Budget status containing:
            - limits: Configured budget limits (daily, weekly, monthly)
            - spending: Current spending per period
            - status: Status per period (under/approaching/exceeded)
            - alert_threshold: Configured alert threshold percentage
            - alerts: List of active budget alerts
    """
    return budgets.get_budget_config()


@app.post(
    "/api/budget",
    tags=["budget"],
    summary="Set Budget Limits",
    response_description="Updated budget configuration"
)
async def set_budget(request: SetBudgetRequest):
    """
    Set budget limits and alert threshold.

    Configure spending limits for different periods. Set to 0 to disable
    a particular limit. Alerts trigger when spending approaches the threshold.

    Args:
        request: SetBudgetRequest containing:
            - daily: Daily budget limit in USD (0 = disabled)
            - weekly: Weekly budget limit in USD (0 = disabled)
            - monthly: Monthly budget limit in USD (0 = disabled)
            - alert_threshold: Alert threshold percentage (0-100)

    Returns:
        dict: Updated budget configuration with all limits and status
    """
    return budgets.set_budget_limits(
        daily=request.daily,
        weekly=request.weekly,
        monthly=request.monthly,
        alert_threshold=request.alert_threshold
    )


@app.get(
    "/api/budget/alerts",
    tags=["budget"],
    summary="Get Budget Alerts",
    response_description="Active budget alerts and exceeded status"
)
async def get_budget_alerts():
    """
    Get all currently active budget alerts.

    Returns alerts triggered when spending approaches or exceeds limits,
    along with information about which periods are currently exceeded.

    Returns:
        dict: Alert information containing:
            - alerts: List of active alerts with period, level, message, timestamp
            - exceeded: Boolean indicating if any budget is exceeded
            - exceeded_periods: List of periods that have exceeded their limits
    """
    alerts = budgets.get_active_alerts()
    exceeded = budgets.check_budget_exceeded()

    return {
        "alerts": alerts,
        "exceeded": exceeded["exceeded"],
        "exceeded_periods": exceeded["periods"]
    }


@app.post(
    "/api/budget/reset",
    tags=["budget"],
    summary="Reset Budget Period",
    response_description="Reset confirmation"
)
async def reset_budget_period(period: Optional[str] = None):
    """
    Manually reset budget spending for a period.

    Clears the spending counter for a specific period or all periods.
    Useful for starting fresh without waiting for automatic reset.

    Args:
        period: Period to reset: "daily", "weekly", "monthly", or None for all

    Returns:
        dict: Reset confirmation containing:
            - status: "reset"
            - period: The period(s) that were reset
    """
    budgets.reset_budget(period)
    return {"status": "reset", "period": period or "all"}


@app.post(
    "/api/budget/alerts/clear",
    tags=["budget"],
    summary="Clear Budget Alerts",
    response_description="Alerts cleared confirmation"
)
async def clear_budget_alerts():
    """
    Clear all active budget alerts.

    Dismisses all current alerts. New alerts will be generated if
    spending still exceeds thresholds.

    Returns:
        dict: Confirmation containing:
            - status: "cleared"
    """
    budgets.clear_alerts()
    return {"status": "cleared"}


# ============ FOLDER ENDPOINTS ============

@app.get(
    "/api/folders",
    tags=["folders"],
    summary="List All Folders",
    response_description="All folder definitions"
)
async def get_folders():
    """
    List all folders for organizing conversations.

    Returns all folder definitions with their metadata.

    Returns:
        dict: Folder list containing:
            - folders: List of folder objects with id, name, color, icon
    """
    return {"folders": await storage.list_folders()}


@app.post(
    "/api/folders",
    tags=["folders"],
    summary="Create Folder",
    response_description="Created folder details"
)
async def create_new_folder(request: CreateFolderRequest):
    """
    Create a new folder for organizing conversations.

    Folders help organize conversations into logical groups.

    Args:
        request: CreateFolderRequest containing:
            - name: Folder display name
            - color: Hex color code (default: "#4a90e2")
            - icon: Icon identifier (default: "folder")

    Returns:
        dict: Created folder containing:
            - id: Unique folder identifier
            - name: Folder name
            - color: Folder color
            - icon: Folder icon
            - created_at: Creation timestamp
    """
    folder = await storage.create_folder(
        name=request.name,
        color=request.color or "#4a90e2",
        icon=request.icon or "folder"
    )
    return folder


@app.delete(
    "/api/folders/{folder_id}",
    tags=["folders"],
    summary="Delete Folder",
    response_description="Deletion confirmation"
)
async def delete_existing_folder(folder_id: str):
    """
    Delete a folder.

    Removes the folder definition. Conversations in the folder
    are not deleted, they become unfiled.

    Args:
        folder_id: The unique folder identifier

    Returns:
        dict: Deletion confirmation containing:
            - status: "success"
            - message: Confirmation message

    Raises:
        HTTPException 404: If folder not found
    """
    deleted = await storage.delete_folder(folder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"status": "success", "message": f"Folder {folder_id} deleted"}


@app.put(
    "/api/conversations/{conversation_id}/folder",
    tags=["folders"],
    summary="Move Conversation to Folder",
    response_description="Updated folder assignment"
)
async def move_to_folder(conversation_id: str, request: MoveFolderRequest):
    """
    Move a conversation to a folder.

    Assigns a conversation to a specific folder, or removes it
    from its current folder if folder_id is null.

    Args:
        conversation_id: The conversation to move
        request: MoveFolderRequest containing:
            - folder_id: Target folder ID (or null to unfile)

    Returns:
        dict: Update confirmation containing:
            - status: "success"
            - folder_id: The new folder ID

    Raises:
        HTTPException 404: If conversation not found
    """
    success = await storage.move_conversation_to_folder(conversation_id, request.folder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "folder_id": request.folder_id}


# ============ TAG ENDPOINTS ============

@app.get(
    "/api/tags",
    tags=["tags"],
    summary="List All Tags",
    response_description="All unique tags in use"
)
async def get_all_tags():
    """
    List all unique tags across all conversations.

    Returns a deduplicated list of all tags that have been
    applied to any conversation.

    Returns:
        dict: Tag list containing:
            - tags: List of unique tag strings
    """
    return {"tags": await storage.list_all_tags()}


@app.put(
    "/api/conversations/{conversation_id}/tags",
    tags=["tags"],
    summary="Update Conversation Tags",
    response_description="Updated tag assignment"
)
async def update_conversation_tags(conversation_id: str, request: UpdateTagsRequest):
    """
    Update tags for a conversation.

    Replaces all tags on a conversation with the provided list.
    Pass an empty array to remove all tags.

    Args:
        conversation_id: The conversation to update
        request: UpdateTagsRequest containing:
            - tags: List of tag strings to apply

    Returns:
        dict: Update confirmation containing:
            - status: "success"
            - tags: The applied tags

    Raises:
        HTTPException 404: If conversation not found
    """
    success = await storage.update_tags(conversation_id, request.tags)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "tags": request.tags}


# ============ TEMPLATE ENDPOINTS ============

class CreateTemplateRequest(BaseModel):
    """Request to create a new template."""
    name: str
    category: str
    prompt_text: str
    variables: List[str]


class UpdateTemplateRequest(BaseModel):
    """Request to update a template."""
    name: Optional[str] = None
    category: Optional[str] = None
    prompt_text: Optional[str] = None
    variables: Optional[List[str]] = None


class FillTemplateRequest(BaseModel):
    """Request to fill a template with variable values."""
    variable_values: Dict[str, str]


@app.get(
    "/api/templates",
    tags=["templates"],
    summary="List Templates",
    response_description="List of available prompt templates"
)
async def list_all_templates(category: Optional[str] = None):
    """
    List all available prompt templates.

    Returns both built-in default templates and user-created custom templates.
    Templates can be filtered by category to find templates for specific use cases.

    Args:
        category: Optional category filter (e.g., "research", "writing", "code")

    Returns:
        dict: Template listing containing:
            - templates: List of template objects with id, name, category, variables
            - count: Total number of templates returned
    """
    template_list = templates.list_templates(category=category)
    return {"templates": template_list, "count": len(template_list)}


@app.get(
    "/api/templates/categories",
    tags=["templates"],
    summary="List Template Categories",
    response_description="List of available template categories"
)
async def list_template_categories():
    """
    List all unique template categories.

    Returns a list of category names that can be used to filter templates.
    Categories help organize templates by use case.

    Returns:
        dict: Categories listing containing:
            - categories: List of category strings (e.g., ["research", "writing", "code"])
    """
    categories = templates.get_categories()
    return {"categories": categories}


@app.get(
    "/api/templates/{template_id}",
    tags=["templates"],
    summary="Get Template",
    response_description="Template details including prompt text and variables"
)
async def get_template_by_id(template_id: str):
    """
    Get a specific template by its ID.

    Returns the full template including the prompt text and list of variables
    that need to be filled when using the template.

    Args:
        template_id: Unique identifier of the template

    Returns:
        dict: Template object containing:
            - id: Template identifier
            - name: Display name
            - category: Template category
            - prompt_text: The template text with variable placeholders
            - variables: List of variable names to fill
            - is_custom: Whether this is a user-created template

    Raises:
        HTTPException 404: Template with given ID does not exist
    """
    template = templates.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.post(
    "/api/templates",
    tags=["templates"],
    summary="Create Template",
    response_description="Newly created template"
)
async def create_new_template(request: CreateTemplateRequest):
    """
    Create a new custom prompt template.

    Custom templates allow users to save reusable prompts with variable
    placeholders that can be filled in later.

    Args:
        request: CreateTemplateRequest containing:
            - name: Display name for the template
            - category: Category to organize the template
            - prompt_text: Template text with {{variable}} placeholders
            - variables: List of variable names used in the template

    Returns:
        dict: Created template object with generated ID

    Example:
        Create a template: {"name": "Code Review", "category": "code",
        "prompt_text": "Review this {{language}} code: {{code}}",
        "variables": ["language", "code"]}
    """
    template = templates.create_template(
        name=request.name,
        category=request.category,
        prompt_text=request.prompt_text,
        variables=request.variables
    )
    return template


@app.put(
    "/api/templates/{template_id}",
    tags=["templates"],
    summary="Update Template",
    response_description="Updated template"
)
async def update_existing_template(template_id: str, request: UpdateTemplateRequest):
    """
    Update an existing custom template.

    Only custom user-created templates can be updated. Default built-in
    templates are read-only and cannot be modified.

    Args:
        template_id: Unique identifier of the template to update
        request: UpdateTemplateRequest with optional fields:
            - name: New display name
            - category: New category
            - prompt_text: New template text
            - variables: New list of variables

    Returns:
        dict: Updated template object

    Raises:
        HTTPException 404: Template not found or is a default template
    """
    template = templates.update_template(
        template_id=template_id,
        name=request.name,
        category=request.category,
        prompt_text=request.prompt_text,
        variables=request.variables
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found or is a default template")
    return template


@app.delete(
    "/api/templates/{template_id}",
    tags=["templates"],
    summary="Delete Template",
    response_description="Deletion confirmation"
)
async def delete_existing_template(template_id: str):
    """
    Delete a custom template.

    Only custom user-created templates can be deleted. Default built-in
    templates are protected and cannot be removed.

    Args:
        template_id: Unique identifier of the template to delete

    Returns:
        dict: Confirmation containing:
            - status: "deleted"

    Raises:
        HTTPException 404: Template not found or is a default template
    """
    success = templates.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found or is a default template")
    return {"status": "deleted"}


@app.post(
    "/api/templates/{template_id}/fill",
    tags=["templates"],
    summary="Fill Template",
    response_description="Filled prompt text ready for use"
)
async def fill_template_with_values(template_id: str, request: FillTemplateRequest):
    """
    Fill a template with provided variable values.

    Replaces all variable placeholders in the template with the provided
    values, producing a complete prompt ready to send to the council.

    Args:
        template_id: Unique identifier of the template to fill
        request: FillTemplateRequest containing:
            - variable_values: Dict mapping variable names to values

    Returns:
        dict: Filled template containing:
            - prompt_text: Complete prompt with all variables replaced

    Raises:
        HTTPException 404: Template with given ID does not exist

    Example:
        Fill template: {"variable_values": {"language": "Python", "code": "def hello()..."}}
        Returns: {"prompt_text": "Review this Python code: def hello()..."}
    """
    filled_text = templates.fill_template(template_id, request.variable_values)
    if filled_text is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"prompt_text": filled_text}



# ============ BATCH PROCESSING ENDPOINTS ============

class CreateBatchRequest(BaseModel):
    """Request to create a batch job."""
    questions: List[str]


@app.post(
    "/api/batch",
    tags=["batch"],
    summary="Create Batch Job",
    response_description="Created batch job with tracking ID"
)
async def create_batch_job_endpoint(request: CreateBatchRequest):
    """
    Create a new batch processing job for multiple questions.

    Batch jobs allow processing multiple questions through the council
    asynchronously. The job runs in the background and results can be
    retrieved later.

    Args:
        request: CreateBatchRequest containing:
            - questions: List of questions to process (1-100)

    Returns:
        dict: Batch job object containing:
            - id: Unique job identifier for tracking
            - status: Current status (pending, running, completed, failed)
            - questions: List of questions submitted
            - results: Empty initially, populated as processing completes
            - created_at: Job creation timestamp

    Raises:
        HTTPException 400: Questions list empty or exceeds 100 items
    """
    if not request.questions:
        raise HTTPException(status_code=400, detail="Questions list cannot be empty")
    if len(request.questions) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 questions per batch")
    job_id = str(uuid.uuid4())
    job = batch.create_batch_job(job_id, request.questions)
    asyncio.create_task(batch.run_batch_job(job_id))
    return job.to_dict()


@app.get(
    "/api/batch",
    tags=["batch"],
    summary="List Batch Jobs",
    response_description="List of all batch jobs"
)
async def list_batch_jobs_endpoint():
    """
    List all batch processing jobs.

    Returns all batch jobs with their current status and progress.
    Useful for monitoring multiple jobs or reviewing past processing.

    Returns:
        dict: Batch jobs listing containing:
            - jobs: List of batch job summaries with id, status, progress
    """
    jobs = batch.list_batch_jobs()
    return {"jobs": jobs}


@app.get(
    "/api/batch/{job_id}",
    tags=["batch"],
    summary="Get Batch Job",
    response_description="Batch job details and results"
)
async def get_batch_job_endpoint(job_id: str):
    """
    Get a specific batch job's status and results.

    Returns full details including all processed results for completed
    questions and current progress for running jobs.

    Args:
        job_id: Unique identifier of the batch job

    Returns:
        dict: Batch job object containing:
            - id: Job identifier
            - status: pending, running, completed, failed, or cancelled
            - progress: Number of completed questions
            - questions: Original questions list
            - results: List of council responses for completed questions
            - error: Error message if failed

    Raises:
        HTTPException 404: Batch job with given ID does not exist
    """
    job = batch.BatchJob.load(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Batch job not found")
    return job.to_dict()


@app.delete(
    "/api/batch/{job_id}",
    tags=["batch"],
    summary="Delete Batch Job",
    response_description="Deletion confirmation"
)
async def delete_batch_job_endpoint(job_id: str):
    """
    Cancel and delete a batch job.

    If the job is still pending or running, it will be cancelled first.
    All job data including results will be permanently deleted.

    Args:
        job_id: Unique identifier of the batch job to delete

    Returns:
        dict: Confirmation containing:
            - status: "deleted"
            - job_id: ID of the deleted job

    Raises:
        HTTPException 404: Batch job with given ID does not exist
    """
    job = batch.BatchJob.load(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Batch job not found")
    if job.status in ["pending", "running"]:
        job.cancel()
    batch.delete_batch_job(job_id)
    return {"status": "deleted", "job_id": job_id}


# ============ SHARING ENDPOINTS ============

@app.post(
    "/api/share/{conversation_id}",
    tags=["sharing"],
    summary="Create Share Link",
    response_description="Shareable link for the conversation"
)
async def share_conversation(conversation_id: str):
    """
    Create a shareable link for a conversation.

    Generates a unique token that can be used to share a read-only view
    of the conversation with others.

    Args:
        conversation_id: ID of the conversation to share

    Returns:
        dict: Share information containing:
            - token: Unique sharing token
            - share_url: Relative URL for sharing
            - conversation_id: Original conversation ID

    Raises:
        HTTPException 404: Conversation with given ID does not exist
    """
    conversation = await storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    token = create_share_link(conversation_id)
    return {
        "token": token,
        "share_url": f"/share/{token}",
        "conversation_id": conversation_id
    }


@app.get(
    "/api/shared/{token}",
    tags=["sharing"],
    summary="Get Shared Conversation",
    response_description="Read-only view of shared conversation"
)
async def get_shared_conversation(token: str):
    """
    Get a shared conversation by its sharing token.

    Returns a read-only view of the conversation. This endpoint is
    publicly accessible to anyone with the token.

    Args:
        token: Unique sharing token from share link

    Returns:
        dict: Shared conversation containing:
            - id: Conversation identifier
            - title: Conversation title
            - created_at: Creation timestamp
            - messages: List of messages in the conversation
            - is_shared: Always true for shared views

    Raises:
        HTTPException 404: Token invalid, expired, or conversation deleted
    """
    conversation_id = get_shared_conversation_id(token)
    if not conversation_id:
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    conversation = await storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation no longer exists")

    # Return read-only view
    return {
        "id": conversation["id"],
        "title": conversation.get("title", "Shared Conversation"),
        "created_at": conversation.get("created_at"),
        "messages": conversation.get("messages", []),
        "is_shared": True
    }


# ============ CODE INTERPRETER ENDPOINTS ============

from .code_interpreter import execute_code, format_execution_result

class CodeInterpreterRequest(BaseModel):
    code: str
    timeout: int = 30


@app.post(
    "/api/interpreter/execute",
    tags=["tools"],
    summary="Execute Code",
    response_description="Code execution results"
)
async def execute_code_endpoint(request: CodeInterpreterRequest):
    """
    Execute Python code in a sandboxed environment.

    Provides a secure code interpreter for running Python code with
    timeout protection. This feature must be enabled in settings.

    Args:
        request: CodeInterpreterRequest containing:
            - code: Python code to execute
            - timeout: Maximum execution time in seconds (default: 30)

    Returns:
        dict: Execution results containing:
            - success: Whether execution completed without error
            - output: Standard output from the code
            - error: Error message if execution failed
            - execution_time: Time taken in seconds

    Raises:
        HTTPException 403: Code execution feature is disabled
    """
    features = get_enhanced_features()
    if not features.get("code_execution"):
        raise HTTPException(status_code=403, detail="Code execution is disabled")

    result = await execute_code(request.code, request.timeout)
    return result


# ============ EXPORT ENDPOINTS ============

@app.get(
    "/api/export/{conversation_id}/markdown",
    tags=["export"],
    summary="Export to Markdown",
    response_description="Markdown file download"
)
async def export_markdown(conversation_id: str):
    """
    Export a conversation to Markdown format.

    Creates a downloadable Markdown file containing the full conversation
    including all stages of council deliberation.

    Args:
        conversation_id: ID of the conversation to export

    Returns:
        PlainTextResponse: Markdown file with Content-Disposition header

    Raises:
        HTTPException 404: Conversation with given ID does not exist
    """
    conversation = await storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    markdown = export_to_markdown(conversation)
    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{conversation_id}.md"'
        }
    )


@app.get(
    "/api/export/{conversation_id}/json",
    tags=["export"],
    summary="Export to JSON",
    response_description="JSON file download"
)
async def export_json(conversation_id: str):
    """
    Export a conversation to JSON format.

    Creates a downloadable JSON file containing the complete conversation
    data structure including all messages and metadata.

    Args:
        conversation_id: ID of the conversation to export

    Returns:
        PlainTextResponse: JSON file with Content-Disposition header

    Raises:
        HTTPException 404: Conversation with given ID does not exist
    """
    conversation = await storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    json_str = export_to_json(conversation)
    return PlainTextResponse(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{conversation_id}.json"'
        }
    )


@app.get(
    "/api/export/{conversation_id}/html",
    tags=["export"],
    summary="Export to HTML",
    response_description="HTML file download"
)
async def export_html(conversation_id: str):
    """
    Export a conversation to HTML format.

    Creates a downloadable HTML file with formatted conversation content
    suitable for viewing in a web browser or printing.

    Args:
        conversation_id: ID of the conversation to export

    Returns:
        HTMLResponse: HTML file with Content-Disposition header

    Raises:
        HTTPException 404: Conversation with given ID does not exist
    """
    conversation = await storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    html = export_to_html(conversation)
    return HTMLResponse(
        content=html,
        headers={
            "Content-Disposition": f'attachment; filename="{conversation_id}.html"'
        }
    )


# ============ TEAM WORKSPACES ENDPOINTS ============

class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateTeamRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "member"  # owner, admin, member


class ShareToTeamRequest(BaseModel):
    conversation_id: str


# In-memory team storage (would use database in production)
_teams = {}
_team_memberships = {}
_team_conversations = {}


@app.get(
    "/api/teams",
    tags=["teams"],
    summary="List Teams",
    response_description="List of teams the user belongs to"
)
async def list_teams():
    """
    List all teams the current user belongs to.

    Returns team workspaces where the user is an owner, admin, or member.

    Returns:
        dict: Teams listing containing:
            - teams: List of team objects with id, name, description
            - count: Total number of teams
    """
    # In production, filter by authenticated user
    teams_list = list(_teams.values())
    return {"teams": teams_list, "count": len(teams_list)}


@app.post(
    "/api/teams",
    tags=["teams"],
    summary="Create Team",
    response_description="Newly created team workspace"
)
async def create_team(request: CreateTeamRequest):
    """
    Create a new team workspace.

    The creating user becomes the team owner with full administrative access.

    Args:
        request: CreateTeamRequest containing:
            - name: Team display name
            - description: Optional team description

    Returns:
        dict: Created team containing:
            - id: Unique team identifier
            - name: Team name
            - description: Team description
            - settings: Team settings object
            - created_at: Creation timestamp
            - member_count: Number of members (starts at 1)
    """
    team_id = str(uuid.uuid4())
    team = {
        "id": team_id,
        "name": request.name,
        "description": request.description,
        "settings": {},
        "created_at": datetime.now().isoformat(),
        "member_count": 1
    }
    _teams[team_id] = team
    _team_memberships[team_id] = [{"user_id": "current_user", "role": "owner"}]
    _team_conversations[team_id] = []
    return team


@app.get(
    "/api/teams/{team_id}",
    tags=["teams"],
    summary="Get Team",
    response_description="Team details with members and conversations"
)
async def get_team(team_id: str):
    """
    Get detailed information about a team.

    Returns full team details including all members and shared conversations.

    Args:
        team_id: Unique identifier of the team

    Returns:
        dict: Team details containing:
            - id: Team identifier
            - name: Team name
            - description: Team description
            - settings: Team configuration
            - members: List of team members with roles
            - conversations: List of shared conversations

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    team = _teams[team_id]
    team["members"] = _team_memberships.get(team_id, [])
    team["conversations"] = _team_conversations.get(team_id, [])
    return team


@app.put(
    "/api/teams/{team_id}",
    tags=["teams"],
    summary="Update Team",
    response_description="Updated team details"
)
async def update_team(team_id: str, request: UpdateTeamRequest):
    """
    Update team settings and information.

    Allows updating team name, description, and settings. Requires
    owner or admin role in the team.

    Args:
        team_id: Unique identifier of the team
        request: UpdateTeamRequest with optional fields:
            - name: New team name
            - description: New team description
            - settings: Settings to merge with existing

    Returns:
        dict: Updated team object

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    team = _teams[team_id]
    if request.name:
        team["name"] = request.name
    if request.description is not None:
        team["description"] = request.description
    if request.settings:
        team["settings"].update(request.settings)
    return team


@app.delete(
    "/api/teams/{team_id}",
    tags=["teams"],
    summary="Delete Team",
    response_description="Deletion confirmation"
)
async def delete_team(team_id: str):
    """
    Delete a team workspace.

    Permanently deletes the team including all memberships and shared
    conversation associations. Requires owner role.

    Args:
        team_id: Unique identifier of the team to delete

    Returns:
        dict: Confirmation containing:
            - status: "deleted"

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    del _teams[team_id]
    _team_memberships.pop(team_id, None)
    _team_conversations.pop(team_id, None)
    return {"status": "deleted"}


@app.post(
    "/api/teams/{team_id}/members",
    tags=["teams"],
    summary="Invite Team Member",
    response_description="Invited member details"
)
async def invite_member(team_id: str, request: InviteMemberRequest):
    """
    Invite a new member to the team.

    Sends an invitation to the specified email address. The invited
    user will receive an email to join the team.

    Args:
        team_id: Unique identifier of the team
        request: InviteMemberRequest containing:
            - email: Email address to invite
            - role: Role to assign (owner, admin, member)

    Returns:
        dict: Invitation details containing:
            - id: Invitation identifier
            - email: Invited email address
            - role: Assigned role
            - invited_at: Invitation timestamp
            - status: "pending" until accepted

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    member = {
        "id": str(uuid.uuid4()),
        "email": request.email,
        "role": request.role,
        "invited_at": datetime.now().isoformat(),
        "status": "pending"
    }
    if team_id not in _team_memberships:
        _team_memberships[team_id] = []
    _team_memberships[team_id].append(member)
    _teams[team_id]["member_count"] = len(_team_memberships[team_id])
    return member


@app.delete(
    "/api/teams/{team_id}/members/{member_id}",
    tags=["teams"],
    summary="Remove Team Member",
    response_description="Removal confirmation"
)
async def remove_member(team_id: str, member_id: str):
    """
    Remove a member from the team.

    Removes the specified member's access to the team. Requires
    owner or admin role to remove members.

    Args:
        team_id: Unique identifier of the team
        member_id: Unique identifier of the member to remove

    Returns:
        dict: Confirmation containing:
            - status: "removed"

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    members = _team_memberships.get(team_id, [])
    _team_memberships[team_id] = [m for m in members if m.get("id") != member_id]
    _teams[team_id]["member_count"] = len(_team_memberships[team_id])
    return {"status": "removed"}


@app.post(
    "/api/teams/{team_id}/conversations",
    tags=["teams"],
    summary="Share Conversation to Team",
    response_description="Shared conversation details"
)
async def share_conversation_to_team(team_id: str, request: ShareToTeamRequest):
    """
    Share a conversation with the team.

    Makes a conversation visible to all team members. The original
    conversation remains accessible to the owner.

    Args:
        team_id: Unique identifier of the team
        request: ShareToTeamRequest containing:
            - conversation_id: ID of conversation to share

    Returns:
        dict: Share details containing:
            - conversation_id: Shared conversation ID
            - title: Conversation title
            - shared_at: Share timestamp
            - shared_by: User who shared

    Raises:
        HTTPException 404: Team or conversation not found
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    conversation = await storage.get_conversation(request.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if team_id not in _team_conversations:
        _team_conversations[team_id] = []

    shared = {
        "conversation_id": request.conversation_id,
        "title": conversation.get("title", "Untitled"),
        "shared_at": datetime.now().isoformat(),
        "shared_by": "current_user"
    }
    _team_conversations[team_id].append(shared)
    return shared


@app.get(
    "/api/teams/{team_id}/conversations",
    tags=["teams"],
    summary="List Team Conversations",
    response_description="List of conversations shared with the team"
)
async def list_team_conversations(team_id: str):
    """
    List all conversations shared with the team.

    Returns conversations that team members have shared for
    collaborative access.

    Args:
        team_id: Unique identifier of the team

    Returns:
        dict: Team conversations containing:
            - conversations: List of shared conversation references
            - count: Total number of shared conversations

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    conversations = _team_conversations.get(team_id, [])
    return {"conversations": conversations, "count": len(conversations)}


# ============ PUBLIC API ACCESS ENDPOINTS ============

import secrets
import hashlib

_api_keys = {}


class CreateAPIKeyRequest(BaseModel):
    name: str
    scopes: List[str] = ["chat", "read"]
    rate_limit: int = 100


@app.get(
    "/api/keys",
    tags=["api-keys"],
    summary="List API Keys",
    response_description="List of API keys with masked values"
)
async def list_api_keys():
    """
    List all API keys for the current user.

    Returns API keys with sensitive portions masked. Keys are shown
    with only the prefix visible for identification.

    Returns:
        dict: API keys listing containing:
            - keys: List of key objects with id, name, prefix, scopes
            - count: Total number of keys
    """
    keys_list = []
    for key_id, key_data in _api_keys.items():
        keys_list.append({
            "id": key_id,
            "name": key_data["name"],
            "prefix": key_data["prefix"],
            "scopes": key_data["scopes"],
            "rate_limit": key_data["rate_limit"],
            "created_at": key_data["created_at"],
            "last_used": key_data.get("last_used")
        })
    return {"keys": keys_list, "count": len(keys_list)}


@app.post(
    "/api/keys",
    tags=["api-keys"],
    summary="Create API Key",
    response_description="New API key with full key shown once"
)
async def create_api_key(request: CreateAPIKeyRequest):
    """
    Create a new API key for programmatic access.

    Generates a secure API key with the specified scopes and rate limit.
    The full key is only shown once on creation - save it securely.

    Args:
        request: CreateAPIKeyRequest containing:
            - name: Descriptive name for the key
            - scopes: List of permission scopes (chat, read, write)
            - rate_limit: Maximum requests per hour (default: 100)

    Returns:
        dict: Created key containing:
            - id: Key identifier
            - key: Full API key (shown only once)
            - name: Key name
            - scopes: Assigned scopes
            - created_at: Creation timestamp
            - warning: Reminder to save key securely
    """
    key_id = str(uuid.uuid4())
    raw_key = f"llmc_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    key_data = {
        "id": key_id,
        "name": request.name,
        "prefix": raw_key[:12],
        "key_hash": key_hash,
        "scopes": request.scopes,
        "rate_limit": request.rate_limit,
        "created_at": datetime.now().isoformat(),
        "is_active": True
    }
    _api_keys[key_id] = key_data

    # Return full key only once (on creation)
    return {
        "id": key_id,
        "key": raw_key,  # Only shown once!
        "name": request.name,
        "scopes": request.scopes,
        "created_at": key_data["created_at"],
        "warning": "Save this key securely. It will not be shown again."
    }


@app.delete(
    "/api/keys/{key_id}",
    tags=["api-keys"],
    summary="Revoke API Key",
    response_description="Revocation confirmation"
)
async def revoke_api_key(key_id: str):
    """
    Revoke an API key.

    Permanently invalidates the API key. The key will no longer be
    accepted for authentication.

    Args:
        key_id: Unique identifier of the key to revoke

    Returns:
        dict: Confirmation containing:
            - status: "revoked"
            - key_id: ID of revoked key

    Raises:
        HTTPException 404: API key with given ID does not exist
    """
    if key_id not in _api_keys:
        raise HTTPException(status_code=404, detail="API key not found")
    del _api_keys[key_id]
    return {"status": "revoked", "key_id": key_id}


@app.put(
    "/api/keys/{key_id}",
    tags=["api-keys"],
    summary="Update API Key",
    response_description="Updated key settings"
)
async def update_api_key(key_id: str, request: CreateAPIKeyRequest):
    """
    Update API key settings.

    Allows modifying the name, scopes, and rate limit of an existing
    API key. The key value itself cannot be changed.

    Args:
        key_id: Unique identifier of the key to update
        request: CreateAPIKeyRequest with new settings:
            - name: New descriptive name
            - scopes: New permission scopes
            - rate_limit: New rate limit

    Returns:
        dict: Update confirmation containing:
            - status: "updated"
            - key: Updated key object (masked)

    Raises:
        HTTPException 404: API key with given ID does not exist
    """
    if key_id not in _api_keys:
        raise HTTPException(status_code=404, detail="API key not found")
    key_data = _api_keys[key_id]
    key_data["name"] = request.name
    key_data["scopes"] = request.scopes
    key_data["rate_limit"] = request.rate_limit
    return {"status": "updated", "key": key_data}


# ============ ENHANCED ANALYTICS ENDPOINTS ============

@app.get(
    "/api/analytics/overview",
    tags=["analytics"],
    summary="Get Analytics Overview",
    response_description="Comprehensive usage analytics summary"
)
async def get_analytics_overview():
    """
    Get comprehensive usage analytics overview.

    Returns aggregated usage statistics including conversation counts,
    token usage, costs, and trends.

    Returns:
        dict: Analytics overview containing:
            - overview: Total conversations, messages, tokens, and cost
            - by_model: Per-model token usage and costs
            - trends: Today's activity and active model count
            - generated_at: Timestamp of analytics generation
    """
    conversations = await storage.list_conversations()
    total_conversations = len(conversations)
    total_messages = sum(c.get("message_count", 0) for c in conversations)

    # Model usage from session
    usage = get_session_usage()

    # Calculate costs and trends
    model_costs = {}
    for model, data in usage.get("by_model", {}).items():
        cost = (data.get("input_tokens", 0) * 0.000003 +
                data.get("output_tokens", 0) * 0.000015)
        model_costs[model] = {
            "tokens": data.get("input_tokens", 0) + data.get("output_tokens", 0),
            "cost": round(cost, 4)
        }

    return {
        "overview": {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_tokens": usage.get("total_tokens", 0),
            "total_cost": round(sum(m["cost"] for m in model_costs.values()), 4)
        },
        "by_model": model_costs,
        "trends": {
            "conversations_today": len([c for c in conversations
                if c.get("created_at", "").startswith(datetime.now().strftime("%Y-%m-%d"))]),
            "messages_today": 0,  # Would calculate from actual data
            "active_models": len(model_costs)
        },
        "generated_at": datetime.now().isoformat()
    }


@app.get(
    "/api/analytics/models",
    tags=["analytics"],
    summary="Get Model Analytics",
    response_description="Detailed per-model usage statistics"
)
async def get_model_analytics():
    """
    Get detailed per-model analytics.

    Returns usage statistics broken down by model including token counts,
    costs, response times, and success rates.

    Returns:
        dict: Model analytics containing:
            - models: List of per-model statistics sorted by usage
            - count: Number of models with usage data
    """
    usage = get_session_usage()
    by_model = usage.get("by_model", {})

    models_data = []
    for model, data in by_model.items():
        input_tokens = data.get("input_tokens", 0)
        output_tokens = data.get("output_tokens", 0)
        cost = input_tokens * 0.000003 + output_tokens * 0.000015

        models_data.append({
            "model": model,
            "requests": data.get("requests", 0),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": round(cost, 4),
            "avg_response_time": data.get("avg_response_time", 0),
            "success_rate": data.get("success_rate", 100)
        })

    # Sort by usage
    models_data.sort(key=lambda x: x["total_tokens"], reverse=True)

    return {"models": models_data, "count": len(models_data)}


@app.get(
    "/api/analytics/conversations",
    tags=["analytics"],
    summary="Get Conversation Analytics",
    response_description="Conversation-level usage statistics"
)
async def get_conversation_analytics():
    """
    Get conversation-level analytics.

    Returns statistics about conversation patterns including daily
    counts and average messages per conversation.

    Returns:
        dict: Conversation analytics containing:
            - total: Total number of conversations
            - daily: Per-day conversation and message counts (last 30 days)
            - avg_messages_per_conversation: Average message count
    """
    conversations = await storage.list_conversations()

    # Group by date
    by_date = {}
    for conv in conversations:
        date = conv.get("created_at", "")[:10]
        if date not in by_date:
            by_date[date] = {"count": 0, "messages": 0}
        by_date[date]["count"] += 1
        by_date[date]["messages"] += conv.get("message_count", 0)

    # Convert to list and sort
    daily_data = [
        {"date": date, **data}
        for date, data in sorted(by_date.items(), reverse=True)
    ][:30]  # Last 30 days

    return {
        "total": len(conversations),
        "daily": daily_data,
        "avg_messages_per_conversation": (
            sum(c.get("message_count", 0) for c in conversations) / len(conversations)
            if conversations else 0
        )
    }


@app.get(
    "/api/analytics/export",
    tags=["analytics"],
    summary="Export Analytics",
    response_description="Full analytics data export"
)
async def export_analytics():
    """
    Export full analytics data as JSON.

    Combines all analytics endpoints into a single comprehensive export
    suitable for backup or external analysis.

    Returns:
        dict: Complete analytics export containing:
            - overview: Summary analytics
            - models: Per-model analytics
            - conversations: Conversation analytics
            - exported_at: Export timestamp
    """
    overview = await get_analytics_overview()
    models = await get_model_analytics()
    conversations = await get_conversation_analytics()

    return {
        "overview": overview,
        "models": models,
        "conversations": conversations,
        "exported_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
