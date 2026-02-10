"""Features, routing, agents, images, and voice routes for LLM Council."""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_optional
from ..database.connection import get_db
from ..database.models import User
from ..database import crud as db_crud
from ..config import (
    get_enhanced_features, set_enhanced_features,
)
from ..router import route_query, get_quick_recommendation, get_council_for_query
from ..agents import (
    create_agent_task, run_agent, get_task, list_tasks,
    cancel_task, delete_task, task_to_dict, AgentStatus,
)
from ..image_gen import (
    generate_image, get_image, list_images, delete_image,
    get_available_providers, image_to_dict,
)
from ..voice import (
    text_to_speech, transcribe, get_tts_result, get_transcription_result,
    list_tts_results, list_transcriptions, get_available_tts_providers,
    get_available_stt_providers, tts_result_to_dict, transcription_result_to_dict,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["features"])


def _json_sse(data: Any) -> str:
    """Serialize data to JSON for SSE, handling Unicode properly."""
    return json.dumps(data, ensure_ascii=False)


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class FeaturesRequest(BaseModel):
    web_search: Optional[bool] = None
    deep_search: Optional[bool] = None
    code_execution: Optional[bool] = None
    memory: Optional[bool] = None
    auto_preference: Optional[Literal["quality", "speed", "cost"]] = None


class RouteRequest(BaseModel):
    query: str
    prefer_speed: bool = False
    prefer_cost: bool = False
    prefer_quality: bool = True
    num_recommendations: int = 3


class CreateAgentRequest(BaseModel):
    """Request to create an AI agent task."""
    query: str = Field(..., min_length=1, max_length=50000, description="Agent query (max 50k chars)")
    model: Optional[str] = Field(default="anthropic/claude-sonnet-4", max_length=100)
    context: Optional[Dict[str, Any]] = None


class ImageGenerationRequest(BaseModel):
    """Request to generate an image."""
    prompt: str = Field(..., min_length=1, max_length=4000, description="Image prompt (max 4k chars)")
    provider: str = Field(default="dalle-3", max_length=50)
    size: str = Field(default="1024x1024", max_length=20)
    quality: str = Field(default="standard", max_length=20)
    style: Optional[str] = "vivid"


class TTSRequest(BaseModel):
    """Request to convert text to speech."""
    text: str = Field(..., min_length=1, max_length=4096, description="Text to convert (max 4k chars)")
    provider: str = Field(default="openai", max_length=50)
    voice: str = Field(default="alloy", max_length=50)
    model: Optional[str] = Field(default="tts-1", max_length=50)
    speed: Optional[float] = 1.0


# ──────────────────────────────────────────────
# Features endpoints
# ──────────────────────────────────────────────

@router.get(
    "/features",
    tags=["tools"],
    summary="Get Enhanced Features Configuration",
    response_description="Current feature toggle states"
)
async def get_features(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Get enhanced features configuration.

    Returns the current state of enhanced features including:
    - web_search: Whether web search is enabled
    - code_execution: Whether code execution is enabled
    - memory: Whether memory/context persistence is enabled

    Returns:
        dict: Feature configuration with boolean flags
    """
    default_features = get_enhanced_features()
    if current_user:
        settings = await db_crud.settings.get_by_user_id(db, current_user.id)
        if settings and settings.enhanced_features:
            user_features = settings.enhanced_features
            merged = {**default_features, **user_features}
            return merged
    return default_features


@router.post(
    "/features",
    tags=["tools"],
    summary="Update Enhanced Features",
    response_description="Updated feature configuration"
)
async def update_features(
    request: FeaturesRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
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
    if request.deep_search is not None:
        updates["deep_search"] = request.deep_search
    if request.code_execution is not None:
        updates["code_execution"] = request.code_execution
    if request.memory is not None:
        updates["memory"] = request.memory
    if request.auto_preference is not None:
        updates["auto_preference"] = request.auto_preference

    if updates:
        if current_user:
            settings = await db_crud.settings.get_by_user_id(db, current_user.id)
            base_features = settings.enhanced_features if settings else get_enhanced_features()
            merged = {**base_features, **updates}
            await db_crud.settings.set_enhanced_features(db, current_user.id, merged)
            return merged
        set_enhanced_features(updates)

    return get_enhanced_features()


# ──────────────────────────────────────────────
# RouteLLM endpoints
# ──────────────────────────────────────────────

@router.post(
    "/route",
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


@router.get(
    "/route/quick",
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


@router.get(
    "/route/council",
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


# ──────────────────────────────────────────────
# AI Agent endpoints
# ──────────────────────────────────────────────

@router.post(
    "/agents",
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


@router.get(
    "/agents",
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


@router.get(
    "/agents/{task_id}",
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


@router.post(
    "/agents/{task_id}/run",
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


@router.post(
    "/agents/{task_id}/run/stream",
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
            yield f"data: {_json_sse({'type': 'started', 'task_id': task_id})}\n\n"

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
                from ..agents import run_agent_step
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
                    yield f"data: {_json_sse(step_event)}\n\n"

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
            yield f"data: {_json_sse(completion_event)}\n\n"

        except Exception as e:
            yield f"data: {_json_sse({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post(
    "/agents/{task_id}/cancel",
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


@router.delete(
    "/agents/{task_id}",
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


# ──────────────────────────────────────────────
# Image Generation endpoints
# ──────────────────────────────────────────────

@router.post(
    "/images/generate",
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


@router.get(
    "/images/providers",
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


@router.get(
    "/images",
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


@router.get(
    "/images/{image_id}",
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


@router.delete(
    "/images/{image_id}",
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


# ──────────────────────────────────────────────
# Voice / TTS / STT endpoints
# ──────────────────────────────────────────────

@router.post(
    "/voice/tts",
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


@router.post(
    "/voice/transcribe",
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


@router.get(
    "/voice/tts/providers",
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


@router.get(
    "/voice/stt/providers",
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


@router.get(
    "/voice/tts",
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


@router.get(
    "/voice/transcriptions",
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


@router.get(
    "/voice/tts/{result_id}",
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


@router.get(
    "/voice/transcriptions/{result_id}",
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
