"""RAG (Retrieval-Augmented Generation) API routes."""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from ..auth.dependencies import get_current_user
from ..database.crud import projects as projects_crud
from .. import rag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


# ──────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────

class EmbedDocumentRequest(BaseModel):
    project_id: str
    document_id: str


class EmbedAllRequest(BaseModel):
    project_id: str


class SemanticSearchRequest(BaseModel):
    project_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


# ──────────────────────────────────────────────
# Literal routes FIRST (before parameterized routes)
# ──────────────────────────────────────────────

@router.post("/embed")
async def embed_document(
    request: EmbedDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Embed a single document from a project's knowledge base."""
    try:
        project_uuid = uuid.UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await projects_crud.get_by_id_for_user(db, project_uuid, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Find the document in the knowledge base
    kb_entry = None
    for item in project.knowledge_base or []:
        if item.get("id") == request.document_id:
            kb_entry = item
            break

    if not kb_entry:
        raise HTTPException(status_code=404, detail="Document not found in knowledge base")

    try:
        result = await rag.embed_document(
            db, project_uuid, request.document_id,
            kb_entry.get("filename", "unknown"),
            kb_entry.get("content", ""),
            kb_entry.get("file_type", "text"),
            current_user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise HTTPException(status_code=500, detail="Embedding generation failed")


@router.post("/embed-all")
async def embed_all_documents(
    request: EmbedAllRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Embed all documents in a project's knowledge base."""
    try:
        project_uuid = uuid.UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await projects_crud.get_by_id_for_user(db, project_uuid, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.knowledge_base:
        return {"results": [], "total_chunks": 0}

    results = []
    total_chunks = 0
    for item in project.knowledge_base:
        try:
            result = await rag.embed_document(
                db, project_uuid, item.get("id", ""),
                item.get("filename", "unknown"),
                item.get("content", ""),
                item.get("file_type", "text"),
                current_user.id,
            )
            results.append({
                "document_id": item.get("id"),
                "filename": item.get("filename"),
                **result,
            })
            total_chunks += result.get("chunk_count", 0)
        except Exception as e:
            logger.warning(f"Failed to embed {item.get('filename')}: {e}")
            results.append({
                "document_id": item.get("id"),
                "filename": item.get("filename"),
                "error": str(e),
                "chunk_count": 0,
                "total_tokens": 0,
            })

    return {"results": results, "total_chunks": total_chunks}


@router.post("/search")
async def semantic_search(
    request: SemanticSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Perform semantic search across a project's embedded documents."""
    try:
        project_uuid = uuid.UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await projects_crud.get_by_id_for_user(db, project_uuid, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    results = await rag.search_project(
        db, project_uuid, request.query, current_user.id, top_k=request.top_k
    )
    return {"results": results}


# ──────────────────────────────────────────────
# Parameterized routes AFTER literal routes
# ──────────────────────────────────────────────

@router.get("/status/{project_id}")
async def get_rag_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get RAG embedding status for a project."""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await projects_crud.get_by_id_for_user(db, project_uuid, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    status = await rag.get_project_rag_status(db, project_uuid)
    return status


@router.delete("/{project_id}/{document_id}")
async def delete_document_embeddings(
    project_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete embeddings for a specific document."""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await projects_crud.get_by_id_for_user(db, project_uuid, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    count = await rag.remove_document_embeddings(db, project_uuid, document_id)
    return {"status": "deleted", "chunks_removed": count}
