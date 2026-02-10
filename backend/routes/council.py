"""Council message routes for LLM Council.

Handles all council deliberation, quick-mode, debate, and voting endpoints.
Extracted from main.py for modularity.
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_optional
from ..config import get_chairman_model
from ..council import (
    run_full_council,
    run_full_council_stream,
    generate_conversation_title,
    gather_context,
    format_web_context,
)
from ..database.connection import get_db
from ..database import crud as db_crud
from ..database.models import User
from ..debate import run_debate
from ..openrouter import query_model_stream
from ..rate_limit import limiter, RATE_LIMITS
from ..voting import run_vote
from .. import storage_adapter as storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["conversations"])

# Store active streams for cancellation support
# Maps conversation_id -> asyncio.Event (set when cancellation requested)
_active_streams: Dict[str, asyncio.Event] = {}


def _json_sse(data: Any) -> str:
    """Serialize data to JSON for SSE, handling Unicode properly."""
    return json.dumps(data, ensure_ascii=False)


# ──────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str = Field(..., min_length=1, max_length=100000, description="Message content (max 100k chars)")
    attached_files: Optional[List[str]] = Field(default=None, max_length=20)
    web_search: Optional[bool] = None
    deep_search: Optional[bool] = None
    fast_mode: Optional[bool] = Field(default=False, description="Skip Stage 2 peer review for faster results")


class QuickMessageRequest(BaseModel):
    """Request to send a message in Quick Mode (single model, no deliberation)."""
    content: str = Field(..., min_length=1, max_length=100000, description="Message content (max 100k chars)")
    model: Optional[str] = Field(default=None, max_length=100)
    web_search: Optional[bool] = None
    deep_search: Optional[bool] = None
    attached_files: Optional[List[str]] = Field(default=None, max_length=20)


class QuickModeRequest(BaseModel):
    """Request for Quick Mode streaming endpoint."""
    message: str = Field(..., min_length=1, max_length=100000, description="Message content (max 100k chars)")
    model: Optional[str] = Field(default=None, max_length=100)


class DebateRequest(BaseModel):
    """Request to run a debate."""
    topic: str = Field(..., min_length=1, max_length=10000, description="Debate topic (max 10k chars)")
    rounds: int = Field(default=2, ge=1, le=10, description="Number of debate rounds (1-10)")


class VoteRequest(BaseModel):
    """Request to run a vote."""
    question: str = Field(..., min_length=1, max_length=10000, description="Vote question (max 10k chars)")
    options: List[str] = Field(..., min_length=2, max_length=26, description="Vote options (2-26)")


# ──────────────────────────────────────────────
# Council Deliberation Endpoints
# ──────────────────────────────────────────────

@router.post(
    "/conversations/{conversation_id}/message",
    tags=["conversations"],
    summary="Send Message (Council Deliberation)",
    response_description="Complete 3-stage council response"
)
@limiter.limit(RATE_LIMITS["council_query"])
async def send_message(
    request: Request,
    conversation_id: str,
    body: SendMessageRequest,
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
    # Check if conversation exists (with user_id for proper scoping)
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None and current_user:
        conversation = await storage.get_conversation(conversation_id, user_id=None, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Get conversation context for follow-up questions (before adding current message)
    conversation_context = None
    if not is_first_message:
        conversation_context = await storage.get_conversation_context(conversation_id, limit=3, user_id=user_id, db=db)

    # Add user message with attached files (use same db session)
    await storage.add_user_message(conversation_id, body.content, body.attached_files, db=db)

    # If this is the first message, generate a title (using user's API keys)
    if is_first_message:
        title = await generate_conversation_title(body.content, user_id=user_id, db=db)
        await storage.update_conversation_title(conversation_id, title, user_id=user_id, db=db)

    # Extract project_id from conversation for context injection
    project_id = conversation.get("project_id")

    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        body.content,
        conversation_context=conversation_context,
        conversation_id=conversation_id,
        attached_files=body.attached_files,
        project_id=project_id,
        web_search=body.web_search,
        deep_search=body.deep_search,
        user_id=user_id,
        db=db
    )

    # Add assistant message with all stages (use same db session)
    await storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        db=db
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@router.post(
    "/conversations/{conversation_id}/message/stream",
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
    # Fallback: try without user scoping if not found (handles user mismatch scenarios)
    if conversation is None:
        conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db, allow_any_user=True)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Get conversation context for follow-up questions (before adding current message)
    conversation_context = None
    if not is_first_message:
        conversation_context = await storage.get_conversation_context(conversation_id, limit=3, user_id=user_id, db=db)

    async def event_generator():
        # Create cancellation event and register this stream
        cancel_event = asyncio.Event()
        _active_streams[conversation_id] = cancel_event
        cancelled = False

        try:
            # Add user message with attached files (use same db session)
            await storage.add_user_message(conversation_id, request.content, request.attached_files, db=db)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content, user_id=user_id, db=db))

            # Variables to store final results
            stage1_results = None
            stage2_results = None
            stage3_result = None
            metadata = None

            # Extract project_id for context injection
            project_id = conversation.get("project_id")

            # Stream the council process with real-time token updates (using user-specific API keys)
            logger.info(f"Council request: fast_mode={request.fast_mode}, web_search={request.web_search}, deep_search={request.deep_search}, files={request.attached_files}, project_id={project_id}")
            async for event in run_full_council_stream(
                request.content,
                conversation_context,
                web_search=request.web_search,
                deep_search=request.deep_search,
                user_id=user_id,
                db=db,
                fast_mode=request.fast_mode,
                conversation_id=conversation_id,
                attached_files=request.attached_files,
                project_id=project_id
            ):
                # Check for cancellation
                if cancel_event.is_set():
                    cancelled = True
                    logger.info("stream_cancellation_detected", conversation_id=conversation_id)
                    yield f"data: {_json_sse({'type': 'cancelled', 'message': 'Stream cancelled by user', 'partial': True})}\n\n"
                    break

                # Forward all events to client
                yield f"data: {_json_sse(event)}\n\n"

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
                await storage.update_conversation_title(conversation_id, title, user_id=user_id, db=db)
                yield f"data: {_json_sse({'type': 'title_complete', 'data': {'title': title}})}\n\n"
            elif title_task and cancelled:
                # Cancel the title task if stream was cancelled
                title_task.cancel()

            # Save complete assistant message (only if not cancelled and all stages complete)
            if stage1_results and stage2_results and stage3_result and not cancelled:
                await storage.add_assistant_message(
                    conversation_id,
                    stage1_results,
                    stage2_results,
                    stage3_result,
                    db=db
                )

        except Exception as e:
            await db.rollback()
            # Send error event
            yield f"data: {_json_sse({'type': 'error', 'message': str(e)})}\n\n"
            raise
        finally:
            # Always clean up the stream registration
            _active_streams.pop(conversation_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post(
    "/conversations/{conversation_id}/cancel",
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


# ──────────────────────────────────────────────
# Quick Mode Endpoints
# ──────────────────────────────────────────────

@router.post(
    "/conversations/{conversation_id}/quick",
    tags=["quick-mode"],
    summary="Quick Mode (Streaming)",
    response_description="Streaming response from single model"
)
@limiter.limit(RATE_LIMITS["quick_mode"])
async def send_quick_mode(
    request: Request,
    conversation_id: str,
    body: QuickModeRequest,
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
    user_id = current_user.id if current_user else None
    # Check if conversation exists
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get user-specific chairman model if available
    if user_id:
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.chairman_model:
            default_model = settings.chairman_model
        else:
            default_model = get_chairman_model()
    else:
        default_model = get_chairman_model()

    # Determine which model to use
    model_to_use = body.model if body.model else default_model
    all_models = _get_all_models()

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
            await storage.add_user_message(conversation_id, body.message, db=db)

            # Start title generation in parallel if first message
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(body.message, user_id=user_id, db=db))

            # Prepare messages for the model
            messages = [{"role": "user", "content": body.message}]

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
                    yield f"data: {_json_sse({'type': 'cancelled', 'message': 'Stream cancelled by user', 'partial_content': full_content})}\n\n"
                    break

                if chunk.get("error"):
                    yield f"data: {_json_sse({'type': 'error', 'message': chunk.get('message', 'Unknown error')})}\n\n"
                    return

                if chunk.get("chunk"):
                    # Send incremental token chunk
                    text_chunk = chunk["chunk"]
                    full_content += text_chunk
                    yield f"data: {_json_sse({'type': 'chunk', 'data': text_chunk})}\n\n"

                if chunk.get("done"):
                    # Extract final metadata
                    usage_info = chunk.get("usage")
                    thinking = chunk.get("thinking")

            # Wait for title generation if it was started (and not cancelled)
            if title_task and not cancelled:
                title = await title_task
                await storage.update_conversation_title(conversation_id, title, user_id=user_id, db=db)
                yield f"data: {_json_sse({'type': 'title_complete', 'data': {'title': title}})}\n\n"
            elif title_task and cancelled:
                title_task.cancel()

            # Save the complete message to storage (only if not cancelled)
            if not cancelled:
                await storage.add_quick_message(
                    conversation_id,
                    full_content,
                    model_to_use,
                    thinking=thinking,
                    usage=usage_info,
                    db=db
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

                yield f"data: {_json_sse(completion_data)}\n\n"

        except Exception as e:
            await db.rollback()
            # Send error event
            yield f"data: {_json_sse({'type': 'error', 'message': str(e)})}\n\n"
            raise
        finally:
            # Always clean up the stream registration
            _active_streams.pop(conversation_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post(
    "/conversations/{conversation_id}/quick-message",
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
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    # Fallback: try without user scoping if not found (handles user mismatch scenarios)
    if conversation is None:
        conversation = await storage.get_conversation(
            conversation_id,
            user_id=user_id,
            db=db,
            allow_any_user=True
        )
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
    all_models = _get_all_models()

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
            # Add user message (include attached files if provided)
            await storage.add_user_message(
                conversation_id,
                request.content,
                attached_files=request.attached_files,
                db=db
            )

            # Start title generation in parallel if first message
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content, user_id=user_id, db=db))

            # Gather web/deep search context if requested
            context = await gather_context(
                request.content,
                web_search=request.web_search,
                deep_search=request.deep_search
            )
            context_sections = []

            if conversation_context:
                context_sections.append(conversation_context)

            # Handle attached files - separate images from text files
            image_content = []
            if request.attached_files:
                try:
                    from .. import files as file_utils
                    # Separate image files from text files
                    image_files = [f for f in request.attached_files if file_utils.is_image_file(f)]
                    text_files = [f for f in request.attached_files if not file_utils.is_image_file(f)]

                    # Add text files to context (ranked by relevance to user query)
                    if text_files:
                        file_context = file_utils.format_files_for_context(
                            conversation_id,
                            text_files,
                            query=request.content
                        )
                        if file_context:
                            context_sections.append(file_context)

                    # Prepare images for vision models
                    if image_files:
                        image_content = file_utils.format_files_for_vision(
                            conversation_id, image_files, query=request.content
                        )
                except Exception as err:
                    logger.warning(
                        "quick_message_file_context_error",
                        conversation_id=conversation_id,
                        error=str(err)
                    )

            if context.get("web_search") or context.get("web_search_summary"):
                web_context_text = format_web_context(
                    context.get("web_search", []),
                    context.get("web_search_summary")
                )
                if web_context_text:
                    context_sections.append(web_context_text)

            if context.get("memory"):
                context_sections.append(
                    f"**Relevant Memory Context:**\n{context['memory']}"
                )

            enhanced_content = request.content
            if context_sections:
                all_context = "\n\n".join(context_sections)
                enhanced_content = f"{all_context}\n\n---\n\n{request.content}"

            # Prepare messages for the model - handle vision content if present
            from ..config import supports_vision
            if image_content and supports_vision(model_to_use):
                # Build multimodal content for vision models
                user_content = [{"type": "text", "text": enhanced_content}]
                for img in image_content:
                    if img.get("type") == "image":
                        source = img.get("source", {})
                        if source.get("type") == "base64":
                            user_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{source.get('media_type', 'image/png')};base64,{source.get('data', '')}"
                                }
                            })
                messages = [{"role": "user", "content": user_content}]
            else:
                messages = [{"role": "user", "content": enhanced_content}]

            # Stream the response (with user-specific API keys)
            full_content = ""
            thinking = None
            usage_info = None

            async for chunk in query_model_stream(model_to_use, messages, user_id=user_id, db=db):
                # Check for cancellation
                if cancel_event.is_set():
                    cancelled = True
                    logger.info("quick_message_stream_cancelled", conversation_id=conversation_id)
                    yield f"data: {_json_sse({'type': 'cancelled', 'message': 'Stream cancelled by user', 'partial_content': full_content})}\n\n"
                    break

                if chunk.get("error"):
                    yield f"data: {_json_sse({'type': 'error', 'message': chunk.get('message', 'Unknown error')})}\n\n"
                    return

                if chunk.get("chunk"):
                    # Send incremental chunk
                    text_chunk = chunk["chunk"]
                    full_content += text_chunk
                    yield f"data: {_json_sse({'type': 'chunk', 'data': text_chunk})}\n\n"

                if chunk.get("done"):
                    # Extract final metadata
                    usage_info = chunk.get("usage")
                    thinking = chunk.get("thinking")

            # Wait for title generation if it was started (and not cancelled)
            if title_task and not cancelled:
                title = await title_task
                await storage.update_conversation_title(conversation_id, title, user_id=user_id, db=db)
                yield f"data: {_json_sse({'type': 'title_complete', 'data': {'title': title}})}\n\n"
            elif title_task and cancelled:
                title_task.cancel()

            # Save the complete message (only if not cancelled)
            if not cancelled:
                await storage.add_quick_message(
                    conversation_id,
                    full_content,
                    model_to_use,
                    thinking=thinking,
                    usage=usage_info,
                    db=db
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

                yield f"data: {_json_sse(completion_data)}\n\n"

        except Exception as e:
            await db.rollback()
            logger.exception("quick_message_stream_error", conversation_id=conversation_id, error=str(e))
            error_message = str(e)
            # In development, include more details
            if os.getenv("ENVIRONMENT", "development").lower() != "production":
                error_message = f"{type(e).__name__}: {error_message}"
            yield f"data: {_json_sse({'type': 'error', 'message': error_message})}\n\n"
            raise
        finally:
            # Always clean up the stream registration
            _active_streams.pop(conversation_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ──────────────────────────────────────────────
# Chat Models Endpoint
# ──────────────────────────────────────────────

@router.get(
    "/chat/models",
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
    all_models = _get_all_models()

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


# ──────────────────────────────────────────────
# Debate Endpoint
# ──────────────────────────────────────────────

@router.post(
    "/conversations/{conversation_id}/debate",
    tags=["debate"],
    summary="Run Debate Mode",
    response_description="Debate results with pro/con arguments and synthesis"
)
async def run_debate_mode(
    conversation_id: str,
    request: DebateRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
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
    # Check if conversation exists (with user_id for proper scoping)
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None and current_user:
        conversation = await storage.get_conversation(conversation_id, user_id=None, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message with debate topic (use same db session)
    await storage.add_user_message(conversation_id, f"DEBATE: {request.topic}", db=db)

    # Get user_id for API key resolution
    user_id = current_user.id if current_user else None

    # If this is the first message, generate a title (using user's API keys)
    if is_first_message:
        title = await generate_conversation_title(f"Debate: {request.topic}", user_id=user_id, db=db)
        await storage.update_conversation_title(conversation_id, title, user_id=user_id, db=db)

    # Run the debate (using user-specific API keys)
    debate_result = await run_debate(request.topic, request.rounds, user_id=user_id, db=db)

    # Add debate result as assistant message (use same db session)
    await storage.add_debate_message(
        conversation_id,
        debate_result,
        db=db
    )

    # Return the complete debate
    return debate_result


# ──────────────────────────────────────────────
# Voting Endpoint
# ──────────────────────────────────────────────

@router.post(
    "/conversations/{conversation_id}/vote",
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
    # Check if conversation exists (with user_id for proper scoping)
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Validate options
    if len(request.options) < 2:
        raise HTTPException(status_code=400, detail="At least 2 options are required")

    if len(request.options) > 26:
        raise HTTPException(status_code=400, detail="Maximum 26 options allowed")

    # Add user message with vote question (use same db session)
    await storage.add_user_message(conversation_id, f"VOTE: {request.question}\nOptions: {', '.join(request.options)}", db=db)

    # Run the vote (using user-specific API keys)
    vote_results = await run_vote(request.question, request.options, user_id=user_id, db=db)

    # Save vote results as assistant message (use same db session)
    await storage.add_assistant_message(
        conversation_id,
        [],  # stage1 - empty for votes
        [],  # stage2 - empty for votes
        vote_results,  # stage3 - store vote results
        db=db
    )

    return vote_results


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _get_all_models():
    """Get combined models (dynamic + fallback).

    Delegates to main.get_all_models() which merges AVAILABLE_MODELS
    with dynamically fetched models from OpenRouter.
    """
    from ..main import get_all_models
    return get_all_models()
