"""Project routes for LLM Council."""

import logging
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from ..database.crud import projects as projects_crud
from ..auth.dependencies import get_current_user
from .. import storage_adapter as storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    """Request to create a new project."""
    name: str = Field(..., min_length=1, max_length=200, description="Project name (max 200 chars)")
    description: Optional[str] = Field(default="", max_length=2000)
    system_prompt: Optional[str] = Field(default="", max_length=50000)
    council_models: Optional[List[str]] = Field(default=None, max_length=20)
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
    layer_id: Optional[str] = None


class ProjectMemoryRequest(BaseModel):
    action: str  # add_fact, add_decision, set_preference, get_context, clear, stats
    content: Optional[str] = None
    category: Optional[str] = "general"
    question: Optional[str] = None
    decision: Optional[str] = None
    reasoning: Optional[str] = None
    key: Optional[str] = None
    value: Optional[Any] = None


# ──────────────────────────────────────────────
# Project endpoints
# ──────────────────────────────────────────────

@router.get(
    "",
    summary="List All Projects",
    response_description="List of project metadata"
)
async def list_all_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all projects for the current user (metadata only).

    Returns a list of all projects owned by the authenticated user,
    not including full knowledge base content.

    Returns:
        dict: Project list containing:
            - projects: List of project metadata (id, name, description, created_at)
    """
    project_list = await projects_crud.list_by_user(db, current_user.id)
    return {
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "conversation_count": len(p.conversations) if hasattr(p, 'conversations') and p.conversations else 0
            }
            for p in project_list
        ]
    }


@router.post(
    "",
    summary="Create Project",
    response_description="Created project details"
)
async def create_new_project(
    request: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project workspace for the current user.

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
    council_config = None
    if request.council_models or request.chairman_model:
        council_config = {
            "council_models": request.council_models,
            "chairman_model": request.chairman_model
        }

    project = await projects_crud.create(
        db,
        user_id=current_user.id,
        name=request.name,
        description=request.description or "",
        system_prompt=request.system_prompt or "",
        council_config=council_config
    )
    await db.commit()

    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "system_prompt": project.system_prompt,
        "knowledge_base": project.knowledge_base or [],
        "memory": project.memory or {"facts": [], "decisions": [], "preferences": {}},
        "council_config": project.council_config,
        "created_at": project.created_at.isoformat() if project.created_at else None
    }


@router.get(
    "/{project_id}",
    summary="Get Project Details",
    response_description="Full project information"
)
async def get_project_details(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific project with all details.

    Retrieves complete project information including knowledge base entries.
    Only returns projects owned by the authenticated user.

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
        HTTPException 404: If project not found or not owned by user
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await projects_crud.get_with_conversations(db, project_uuid, current_user.id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "system_prompt": project.system_prompt,
        "knowledge_base": project.knowledge_base or [],
        "memory": project.memory or {"facts": [], "decisions": [], "preferences": {}},
        "council_config": project.council_config,
        "conversations": [str(c.id) for c in project.conversations] if project.conversations else [],
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None
    }


@router.put(
    "/{project_id}",
    summary="Update Project",
    response_description="Updated project details"
)
async def update_existing_project(
    project_id: str,
    request: UpdateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a project's configuration.

    Updates specified fields of a project. Only provided fields are updated.
    Only the project owner can update their project.

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
        HTTPException 404: If project not found or not owned by user
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.description is not None:
        updates["description"] = request.description
    if request.system_prompt is not None:
        updates["system_prompt"] = request.system_prompt
    if request.council_config is not None:
        updates["council_config"] = request.council_config

    project = await projects_crud.update_project(db, project_uuid, current_user.id, **updates)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.commit()

    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "system_prompt": project.system_prompt,
        "knowledge_base": project.knowledge_base or [],
        "memory": project.memory or {"facts": [], "decisions": [], "preferences": {}},
        "council_config": project.council_config,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None
    }


@router.delete(
    "/{project_id}",
    summary="Delete Project",
    response_description="Deletion confirmation"
)
async def delete_existing_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a project and its knowledge base.

    Permanently removes a project. Linked conversations are not deleted
    but will be unlinked from the project. Only the project owner can delete.

    Args:
        project_id: The unique project identifier

    Returns:
        dict: Deletion confirmation with status: "deleted"

    Raises:
        HTTPException 404: If project not found or not owned by user
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    success = await projects_crud.delete_project(db, project_uuid, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.commit()
    return {"status": "deleted"}


# ──────────────────────────────────────────────
# Knowledge Base endpoints
# ──────────────────────────────────────────────

@router.post(
    "/{project_id}/knowledge",
    summary="Add Knowledge Base Entry",
    response_description="Created knowledge base entry"
)
async def add_knowledge_to_project(
    project_id: str,
    request: AddKnowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a file to the project's knowledge base.

    Knowledge base entries provide context that can be included
    in conversations within this project. Only the project owner can add.

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
        HTTPException 404: If project not found or not owned by user
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    file_id = str(uuid.uuid4())
    project = await projects_crud.add_to_knowledge_base(
        db,
        project_id=project_uuid,
        user_id=current_user.id,
        file_id=file_id,
        filename=request.filename,
        content=request.content,
        file_type=request.file_type or "text"
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.commit()

    # Auto-embed for RAG
    try:
        from .. import rag
        layer_uuid = uuid.UUID(request.layer_id) if request.layer_id else None
        await rag.embed_document(
            db, project_uuid, file_id, request.filename,
            request.content, request.file_type or "text", current_user.id,
            layer_id=layer_uuid,
        )
    except Exception as e:
        logger.warning(f"Auto-embed failed for {request.filename}: {e}")

    # Find the newly added entry
    kb_entry = None
    for item in project.knowledge_base or []:
        if item.get("id") == file_id:
            kb_entry = item
            break

    return kb_entry or {"id": file_id, "filename": request.filename, "file_type": request.file_type or "text"}


@router.delete(
    "/{project_id}/knowledge/{file_id}",
    summary="Remove Knowledge Base Entry",
    response_description="Deletion confirmation"
)
async def remove_knowledge_from_project(
    project_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a file from the project's knowledge base.

    Permanently removes a knowledge base entry from the project.
    Only the project owner can remove entries.

    Args:
        project_id: The unique project identifier
        file_id: The knowledge base entry identifier

    Returns:
        dict: Deletion confirmation with status: "deleted"

    Raises:
        HTTPException 404: If project or file not found or not owned by user
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await projects_crud.remove_from_knowledge_base(db, project_uuid, current_user.id, file_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project or file not found")

    await db.commit()

    # Remove RAG embeddings
    try:
        from .. import rag
        await rag.remove_document_embeddings(db, project_uuid, file_id)
    except Exception as e:
        logger.warning(f"Failed to remove embeddings for {file_id}: {e}")

    return {"status": "deleted"}


@router.get(
    "/{project_id}/knowledge/{file_id}",
    summary="Get Knowledge Base Content",
    response_description="Knowledge base file content"
)
async def get_knowledge_file_content(
    project_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the content of a knowledge base file.

    Retrieves the full content of a specific knowledge base entry.
    Only the project owner can access.

    Args:
        project_id: The unique project identifier
        file_id: The knowledge base entry identifier

    Returns:
        dict: File content containing:
            - content: The full file content

    Raises:
        HTTPException 404: If file not found or not owned by user
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    kb_file = await projects_crud.get_knowledge_base_file(db, project_uuid, current_user.id, file_id)
    if kb_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    return {"content": kb_file.get("content", "")}


# ──────────────────────────────────────────────
# Conversation endpoints
# ──────────────────────────────────────────────

@router.post(
    "/{project_id}/conversations",
    summary="Create Project Conversation",
    response_description="New conversation linked to project"
)
async def create_conversation_in_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new conversation within a project.

    Creates a conversation that is automatically linked to the project,
    inheriting the project's system prompt and knowledge base context.
    Only the project owner can create conversations.

    Args:
        project_id: The unique project identifier

    Returns:
        dict: Created conversation containing:
            - conversation: Full conversation object
            - project_id: The project this conversation belongs to

    Raises:
        HTTPException 404: If project not found or not owned by user
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    # Verify project exists and user owns it
    project = await projects_crud.get_by_id_for_user(db, project_uuid, current_user.id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create conversation linked to project
    conversation_id = uuid.uuid4()
    conversation = await storage.create_conversation(
        str(conversation_id),
        user_id=current_user.id,
        db=db,
        project_id=project_uuid
    )

    await db.commit()

    return {
        "conversation": conversation,
        "project_id": project_id
    }


# ──────────────────────────────────────────────
# Project Memory endpoints
# ──────────────────────────────────────────────

@router.post(
    "/{project_id}/memory",
    summary="Project Memory Operations",
    response_description="Memory operation results"
)
async def project_memory(
    project_id: str,
    request: ProjectMemoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform project-specific memory operations.

    Stores facts, decisions, and preferences specific to a project that
    persist across conversations within that project.
    Only the project owner can modify memory.

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
        HTTPException 404: Project not found or not owned by user
        HTTPException 400: Missing required fields for action
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    # Verify ownership
    project = await projects_crud.get_by_id_for_user(db, project_uuid, current_user.id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if request.action == "add_fact":
        if not request.content:
            raise HTTPException(status_code=400, detail="Content required")
        result = await projects_crud.add_fact(db, project_uuid, current_user.id, request.content)
        await db.commit()
        return {"success": result is not None, "action": "add_fact"}

    elif request.action == "add_decision":
        if not request.question or not request.decision:
            raise HTTPException(status_code=400, detail="Question and decision required")
        decision_text = f"{request.question} → {request.decision}"
        if request.reasoning:
            decision_text += f" (Reasoning: {request.reasoning})"
        result = await projects_crud.add_decision(db, project_uuid, current_user.id, decision_text, request.reasoning)
        await db.commit()
        return {"success": result is not None, "action": "add_decision"}

    elif request.action == "set_preference":
        if not request.key:
            raise HTTPException(status_code=400, detail="Key required")
        result = await projects_crud.set_preference(db, project_uuid, current_user.id, request.key, request.value)
        await db.commit()
        return {"success": result is not None, "action": "set_preference"}

    elif request.action == "get_context":
        context = projects_crud.get_project_context(project)
        return {"context": context, "action": "get_context"}

    elif request.action == "clear":
        result = await projects_crud.clear_memory(db, project_uuid, current_user.id)
        await db.commit()
        return {"success": result is not None, "action": "clear"}

    elif request.action == "stats":
        stats = await projects_crud.get_memory_stats(db, project_uuid, current_user.id)
        return {"stats": stats, "action": "stats"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
