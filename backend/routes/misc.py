"""Miscellaneous routes for LLM Council.

Includes: folders, tags, templates, batch processing, sharing, export,
admin, budget, and code interpreter endpoints.
"""

import asyncio
import hashlib
import logging
import secrets
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage_adapter as storage, templates, batch, budgets
from ..auth.dependencies import get_current_user, get_current_user_optional
from ..database.connection import get_db
from ..database.models import User
from ..config import get_enhanced_features
from ..export import (
    export_to_markdown, export_to_json, export_to_html,
    create_share_link, get_shared_conversation_id,
)
from ..code_interpreter import execute_code, format_execution_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["misc"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class CreateFolderRequest(BaseModel):
    """Request to create a new folder."""
    name: str = Field(..., min_length=1, max_length=100, description="Folder name (max 100 chars)")
    color: Optional[str] = Field(default="#4a90e2", max_length=20)
    icon: Optional[str] = Field(default="folder", max_length=50)


class MoveFolderRequest(BaseModel):
    """Request to move a conversation to a folder."""
    folder_id: Optional[str] = None


class MoveProjectRequest(BaseModel):
    """Request to move a conversation to a project."""
    project_id: Optional[str] = None


class UpdateTagsRequest(BaseModel):
    """Request to update conversation tags."""
    tags: List[str]


class SetBudgetRequest(BaseModel):
    """Request to set budget limits."""
    daily: Optional[float] = None
    weekly: Optional[float] = None
    monthly: Optional[float] = None
    alert_threshold: Optional[float] = None


class CreateTemplateRequest(BaseModel):
    """Request to create a new template."""
    name: str = Field(..., min_length=1, max_length=100, description="Template name (max 100 chars)")
    category: str = Field(..., min_length=1, max_length=50)
    prompt_text: str = Field(..., min_length=1, max_length=50000)
    variables: List[str] = Field(..., max_length=50)


class UpdateTemplateRequest(BaseModel):
    """Request to update a template."""
    name: Optional[str] = None
    category: Optional[str] = None
    prompt_text: Optional[str] = None
    variables: Optional[List[str]] = None


class FillTemplateRequest(BaseModel):
    """Request to fill a template with variable values."""
    variable_values: Dict[str, str]


class CreateBatchRequest(BaseModel):
    """Request to create a batch job."""
    questions: List[str]


class CodeInterpreterRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000, description="Code to execute (max 50k chars)")
    timeout: int = Field(default=30, ge=1, le=120)


# ══════════════════════════════════════════════
# FOLDER ENDPOINTS
# ══════════════════════════════════════════════

@router.get(
    "/folders",
    tags=["folders"],
    summary="List All Folders",
    response_description="All folder definitions"
)
async def get_folders(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    List all folders for organizing conversations.

    Returns all folder definitions with their metadata.

    Returns:
        dict: Folder list containing:
            - folders: List of folder objects with id, name, color, icon
    """
    return {
        "folders": await storage.list_folders(
            user_id=current_user.id if current_user else None,
            db=db,
        )
    }


@router.post(
    "/folders",
    tags=["folders"],
    summary="Create Folder",
    response_description="Created folder details"
)
async def create_new_folder(
    request: CreateFolderRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
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
        icon=request.icon or "folder",
        user_id=current_user.id if current_user else None,
        db=db,
    )
    return folder


@router.delete(
    "/folders/{folder_id}",
    tags=["folders"],
    summary="Delete Folder",
    response_description="Deletion confirmation"
)
async def delete_existing_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
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
    deleted = await storage.delete_folder(
        folder_id,
        user_id=current_user.id if current_user else None,
        db=db,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"status": "success", "message": f"Folder {folder_id} deleted"}


@router.put(
    "/conversations/{conversation_id}/folder",
    tags=["folders"],
    summary="Move Conversation to Folder",
    response_description="Updated folder assignment"
)
async def move_to_folder(
    conversation_id: str,
    request: MoveFolderRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
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
    success = await storage.move_conversation_to_folder(
        conversation_id,
        request.folder_id,
        user_id=current_user.id if current_user else None,
        db=db,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "folder_id": request.folder_id}


@router.put(
    "/conversations/{conversation_id}/project",
    tags=["projects"],
    summary="Move Conversation to Project",
    response_description="Updated project assignment"
)
async def move_to_project(
    conversation_id: str,
    request: MoveProjectRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Move a conversation to a project.

    Assigns a conversation to a specific project, or removes it
    from its current project if project_id is null.

    Args:
        conversation_id: The conversation to move
        request: MoveProjectRequest containing:
            - project_id: Target project ID (or null to remove from project)

    Returns:
        dict: Update confirmation containing:
            - status: "success"
            - project_id: The new project ID

    Raises:
        HTTPException 404: If conversation not found
    """
    user_id = current_user.id if current_user else None
    success = await storage.move_conversation_to_project(
        conversation_id,
        request.project_id,
        user_id=user_id,
        db=db,
    )
    if not success and current_user:
        # Fallback for conversations created before login (anonymous scope)
        success = await storage.move_conversation_to_project(
            conversation_id,
            request.project_id,
            user_id=None,
            db=db,
        )
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "project_id": request.project_id}


# ══════════════════════════════════════════════
# TAG ENDPOINTS
# ══════════════════════════════════════════════

@router.get(
    "/tags",
    tags=["tags"],
    summary="List All Tags",
    response_description="All unique tags in use"
)
async def get_all_tags(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    List all unique tags across all conversations.

    Returns a deduplicated list of all tags that have been
    applied to any conversation.

    Returns:
        dict: Tag list containing:
            - tags: List of unique tag strings
    """
    return {
        "tags": await storage.list_all_tags(
            user_id=current_user.id if current_user else None,
            db=db,
        )
    }


@router.put(
    "/conversations/{conversation_id}/tags",
    tags=["tags"],
    summary="Update Conversation Tags",
    response_description="Updated tag assignment"
)
async def update_conversation_tags(
    conversation_id: str,
    request: UpdateTagsRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
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
    success = await storage.update_tags(
        conversation_id,
        request.tags,
        user_id=current_user.id if current_user else None,
        db=db,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "tags": request.tags}


# ══════════════════════════════════════════════
# TEMPLATE ENDPOINTS
# ══════════════════════════════════════════════

@router.get(
    "/templates",
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


@router.get(
    "/templates/categories",
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


@router.get(
    "/templates/{template_id}",
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


@router.post(
    "/templates",
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


@router.put(
    "/templates/{template_id}",
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


@router.delete(
    "/templates/{template_id}",
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


@router.post(
    "/templates/{template_id}/fill",
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


# ══════════════════════════════════════════════
# BATCH PROCESSING ENDPOINTS
# ══════════════════════════════════════════════

@router.post(
    "/batch",
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


@router.get(
    "/batch",
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


@router.get(
    "/batch/{job_id}",
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


@router.delete(
    "/batch/{job_id}",
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


# ══════════════════════════════════════════════
# SHARING ENDPOINTS
# ══════════════════════════════════════════════

@router.post(
    "/share/{conversation_id}",
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


@router.get(
    "/shared/{token}",
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


# ══════════════════════════════════════════════
# CODE INTERPRETER ENDPOINTS
# ══════════════════════════════════════════════

@router.post(
    "/interpreter/execute",
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


# ══════════════════════════════════════════════
# EXPORT ENDPOINTS
# ══════════════════════════════════════════════

@router.get(
    "/export/{conversation_id}/markdown",
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


@router.get(
    "/export/{conversation_id}/json",
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


@router.get(
    "/export/{conversation_id}/html",
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


# ══════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════

@router.get(
    "/admin/conversations",
    tags=["admin"],
    summary="List All Conversations (Admin)",
    response_description="Paginated list of all conversations"
)
async def admin_list_conversations(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all conversations in the system (admin only).

    Allows admins to view and manage all user conversations for
    support, moderation, or debugging purposes.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        user_id: Optional filter by specific user
        current_user: Must be an admin user

    Returns:
        List of conversations with user info

    Raises:
        HTTPException 403: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    from ..database.crud import conversations as db_conversations

    user_filter = uuid.UUID(user_id) if user_id else None
    convs = await db_conversations.list_all(db, skip=skip, limit=limit, user_filter=user_filter)
    total = await db_conversations.count_all(db, user_filter=user_filter)

    return {
        "conversations": [
            {
                "id": str(conv.id),
                "user_id": str(conv.user_id) if conv.user_id else None,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "message_count": len(conv.messages) if hasattr(conv, 'messages') else 0,
                "project_id": str(conv.project_id) if conv.project_id else None,
            }
            for conv in convs
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get(
    "/admin/conversations/{conversation_id}",
    tags=["admin"],
    summary="Get Any Conversation (Admin)",
    response_description="Full conversation with messages"
)
async def admin_get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get any conversation by ID (admin only).

    Allows admins to view full conversation content regardless
    of ownership, for support or moderation purposes.

    Args:
        conversation_id: ID of the conversation
        current_user: Must be an admin user

    Returns:
        Full conversation with messages

    Raises:
        HTTPException 403: If user is not an admin
        HTTPException 404: If conversation not found
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    from ..database.crud import conversations as db_conversations

    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    conv = await db_conversations.admin_get_by_id(db, conv_uuid)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "id": str(conv.id),
        "user_id": str(conv.user_id) if conv.user_id else None,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "project_id": str(conv.project_id) if conv.project_id else None,
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "message_type": msg.message_type,
                "created_at": msg.created_at.isoformat(),
                "stage1": msg.stage1,
                "stage2": msg.stage2,
                "stage3": msg.stage3,
            }
            for msg in sorted(conv.messages, key=lambda m: m.message_index)
        ] if hasattr(conv, 'messages') else []
    }


@router.get(
    "/admin/users",
    tags=["admin"],
    summary="List All Users (Admin)",
    response_description="List of all users"
)
async def admin_list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users in the system (admin only).

    Provides user list for filtering conversations by user.

    Args:
        current_user: Must be an admin user

    Returns:
        List of users with basic info

    Raises:
        HTTPException 403: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import select
    from ..database.models import User as UserModel

    result = await db.execute(
        select(UserModel).order_by(UserModel.created_at.desc())
    )
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "is_admin": user.is_admin,
                "created_at": user.created_at.isoformat(),
                "conversation_count": len(user.conversations) if hasattr(user, 'conversations') else 0
            }
            for user in users
        ]
    }


# ══════════════════════════════════════════════
# BUDGET ENDPOINTS
# ══════════════════════════════════════════════

@router.get(
    "/budget",
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


@router.post(
    "/budget",
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


@router.get(
    "/budget/alerts",
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


@router.post(
    "/budget/reset",
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


@router.post(
    "/budget/alerts/clear",
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
