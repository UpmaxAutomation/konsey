"""CRUD operations for document chunks (RAG)."""

import json
import uuid
from typing import Optional, List

from sqlalchemy import text, delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DocumentChunk


# ──────────────────────────────────────────────
# Document chunk operations
# ──────────────────────────────────────────────

async def create_chunks_batch(
    db: AsyncSession,
    chunks: list[dict],
) -> int:
    """Bulk insert document chunks with vector embeddings.

    Each dict must contain: project_id, document_id, filename, chunk_index,
    content, embedding (list[float]), start_line, end_line, tokens, metadata.
    Returns the count of rows inserted.
    """
    if not chunks:
        return 0

    sql = text("""
        INSERT INTO document_chunks
            (id, project_id, document_id, filename, chunk_index, content,
             embedding, start_line, end_line, tokens, metadata, layer_id)
        VALUES
            (gen_random_uuid(), :project_id, :document_id, :filename,
             :chunk_index, :content, :embedding::vector,
             :start_line, :end_line, :tokens, :metadata::jsonb, :layer_id)
    """)

    count = 0
    for chunk in chunks:
        embedding = chunk.get("embedding")
        embedding_str = str(embedding) if embedding else None

        metadata_val = chunk.get("metadata") or {}
        metadata_str = json.dumps(metadata_val) if isinstance(metadata_val, dict) else str(metadata_val)

        layer_id = chunk.get("layer_id")
        if isinstance(layer_id, str):
            layer_id = uuid.UUID(layer_id) if layer_id else None

        await db.execute(sql, {
            "project_id": chunk["project_id"],
            "document_id": chunk["document_id"],
            "filename": chunk["filename"],
            "chunk_index": chunk["chunk_index"],
            "content": chunk["content"],
            "embedding": embedding_str,
            "start_line": chunk.get("start_line"),
            "end_line": chunk.get("end_line"),
            "tokens": chunk.get("tokens", 0),
            "metadata": metadata_str,
            "layer_id": layer_id,
        })
        count += 1

    return count


async def delete_chunks_for_document(
    db: AsyncSession,
    project_id: uuid.UUID,
    document_id: str,
) -> int:
    """Delete all chunks for a specific document within a project.

    Returns the count of rows deleted.
    """
    result = await db.execute(
        delete(DocumentChunk)
        .where(
            DocumentChunk.project_id == project_id,
            DocumentChunk.document_id == document_id,
        )
    )
    return result.rowcount


async def delete_chunks_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> int:
    """Delete all chunks for a project.

    Returns the count of rows deleted.
    """
    result = await db.execute(
        delete(DocumentChunk)
        .where(DocumentChunk.project_id == project_id)
    )
    return result.rowcount


async def search_similar(
    db: AsyncSession,
    project_id: uuid.UUID,
    query_embedding: list[float],
    top_k: int = 5,
    layer_id: Optional[uuid.UUID] = None,
) -> list[dict]:
    """Cosine similarity search against document chunk embeddings.

    Returns a list of dicts with all chunk columns plus a similarity score.
    Optionally filter by layer_id.
    """
    where_clause = "WHERE project_id = :project_id AND embedding IS NOT NULL"
    params = {
        "project_id": project_id,
        "query": str(query_embedding),
        "top_k": top_k,
    }

    if layer_id is not None:
        where_clause += " AND layer_id = :layer_id"
        params["layer_id"] = layer_id

    sql = text(f"""
        SELECT
            id, project_id, document_id, filename, chunk_index, content,
            start_line, end_line, tokens, metadata, layer_id,
            1 - (embedding <=> :query::vector) AS similarity
        FROM document_chunks
        {where_clause}
        ORDER BY embedding <=> :query::vector
        LIMIT :top_k
    """)

    result = await db.execute(sql, params)

    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def get_document_chunk_counts(
    db: AsyncSession,
    project_id: uuid.UUID,
    layer_id: Optional[uuid.UUID] = None,
) -> dict:
    """Get chunk counts grouped by document.

    Returns a dict mapping document_id to {filename, chunk_count}.
    Optionally filter by layer_id.
    """
    where_clause = "WHERE project_id = :project_id"
    params = {"project_id": project_id}

    if layer_id is not None:
        where_clause += " AND layer_id = :layer_id"
        params["layer_id"] = layer_id

    sql = text(f"""
        SELECT document_id, filename, COUNT(*) as chunk_count
        FROM document_chunks
        {where_clause}
        GROUP BY document_id, filename
    """)

    result = await db.execute(sql, params)
    rows = result.mappings().all()

    return {
        row["document_id"]: {
            "filename": row["filename"],
            "chunk_count": row["chunk_count"],
        }
        for row in rows
    }


async def count_chunks(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> int:
    """Total chunk count for a project."""
    result = await db.execute(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.project_id == project_id)
    )
    return result.scalar_one()


async def assign_layer_to_document(
    db: AsyncSession,
    project_id: uuid.UUID,
    document_id: str,
    layer_id: uuid.UUID,
) -> int:
    """Assign all chunks of a document to a knowledge layer.

    Returns the count of rows updated.
    """
    sql = text("""
        UPDATE document_chunks
        SET layer_id = :layer_id
        WHERE project_id = :project_id AND document_id = :document_id
    """)
    result = await db.execute(sql, {
        "layer_id": layer_id,
        "project_id": project_id,
        "document_id": document_id,
    })
    return result.rowcount


async def get_layer_chunk_counts(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict:
    """Get chunk counts grouped by layer.

    Returns a dict mapping layer_id (str or 'unassigned') to chunk_count.
    """
    sql = text("""
        SELECT layer_id, COUNT(*) as chunk_count
        FROM document_chunks
        WHERE project_id = :project_id
        GROUP BY layer_id
    """)
    result = await db.execute(sql, {"project_id": project_id})
    rows = result.mappings().all()

    return {
        (str(row["layer_id"]) if row["layer_id"] else "unassigned"): row["chunk_count"]
        for row in rows
    }
