"""RAG (Retrieval-Augmented Generation) orchestrator.

Ties together document chunking, embedding generation, and semantic search
to provide context-aware retrieval for the council pipeline.
"""

import logging
import os
import uuid as uuid_mod
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# RAG-optimized chunk sizes (smaller than default for better retrieval precision)
RAG_CHUNK_TOKENS = 512
RAG_OVERLAP_TOKENS = 64

# File extensions that use code-aware chunking
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".rb", ".c", ".cpp", ".h", ".cs", ".sql",
}


def _get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    if "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ""


async def embed_document(
    db: AsyncSession,
    project_id,
    document_id: str,
    filename: str,
    content: str,
    file_type: str,
    user_id,
    layer_id=None,
) -> dict:
    """Chunk and embed a single document for RAG retrieval.

    Returns dict with chunk_count and total_tokens.
    """
    from . import files, embeddings
    from .database.crud import document_chunks as dc_crud

    # Ensure project_id is a UUID
    if isinstance(project_id, str):
        project_id = uuid_mod.UUID(project_id)

    # 1. Chunk the content
    ext = _get_file_extension(filename)
    if ext in CODE_EXTENSIONS:
        chunks = files.chunk_code_aware(
            content, ext,
            max_tokens_per_chunk=RAG_CHUNK_TOKENS,
            overlap_tokens=RAG_OVERLAP_TOKENS,
        )
    else:
        chunks = files._chunk_generic(
            content, RAG_CHUNK_TOKENS, RAG_OVERLAP_TOKENS
        )

    if not chunks:
        logger.info(f"No chunks produced for {filename}")
        return {"chunk_count": 0, "total_tokens": 0}

    # 2. Get API key
    api_key = await embeddings.get_openai_key(db, user_id)
    if not api_key:
        raise ValueError("No OpenAI API key available for embeddings")

    # 3. Generate embeddings
    texts = [c["content"] for c in chunks]
    vectors = await embeddings.generate_embeddings_batch(texts, api_key)

    # 4. Delete existing chunks for this document
    await dc_crud.delete_chunks_for_document(db, project_id, document_id)

    # 5. Build chunk records
    chunk_records = []
    total_tokens = 0
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        chunk_records.append({
            "project_id": str(project_id),
            "document_id": document_id,
            "filename": filename,
            "chunk_index": i,
            "content": chunk["content"],
            "embedding": vector,
            "start_line": chunk.get("start_line"),
            "end_line": chunk.get("end_line"),
            "tokens": chunk.get("tokens", 0),
            "metadata": {
                "boundary_type": chunk.get("boundary_type"),
                "definitions": chunk.get("definitions", []),
            },
            "layer_id": str(layer_id) if layer_id else None,
        })
        total_tokens += chunk.get("tokens", 0)

    # 6. Insert
    await dc_crud.create_chunks_batch(db, chunk_records)
    await db.commit()

    logger.info(
        f"Embedded {filename}: {len(chunk_records)} chunks, {total_tokens} tokens"
    )
    return {"chunk_count": len(chunk_records), "total_tokens": total_tokens}


async def search_project(
    db: AsyncSession,
    project_id,
    query: str,
    user_id,
    top_k: int = 5,
    layer_id=None,
) -> list[dict]:
    """Search project knowledge base using semantic similarity.

    Optionally filter by layer_id to search within a specific knowledge layer.
    """
    from . import embeddings
    from .database.crud import document_chunks as dc_crud

    if isinstance(project_id, str):
        project_id = uuid_mod.UUID(project_id)

    api_key = await embeddings.get_openai_key(db, user_id)
    if not api_key:
        logger.warning("No OpenAI API key for RAG search")
        return []

    query_embedding = await embeddings.generate_embedding(query, api_key)
    results = await dc_crud.search_similar(
        db, project_id, query_embedding, top_k, layer_id=layer_id
    )
    return results


async def search_layers(
    db: AsyncSession,
    project_id,
    query: str,
    user_id,
    layer_ids: list,
    top_k: int = 5,
) -> list[dict]:
    """Search across specific knowledge layers, merging results by similarity."""
    from . import embeddings
    from .database.crud import document_chunks as dc_crud

    if isinstance(project_id, str):
        project_id = uuid_mod.UUID(project_id)

    api_key = await embeddings.get_openai_key(db, user_id)
    if not api_key:
        logger.warning("No OpenAI API key for RAG search")
        return []

    query_embedding = await embeddings.generate_embedding(query, api_key)

    all_results = []
    for lid in layer_ids:
        results = await dc_crud.search_similar(
            db, project_id, query_embedding, top_k, layer_id=lid
        )
        all_results.extend(results)

    # Sort by similarity descending and return top_k
    all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return all_results[:top_k]


def format_rag_context(chunks: list[dict], layer_name: str = None) -> str:
    """Format retrieved chunks for injection into the council prompt."""
    if not chunks:
        return ""

    sections = ["**Relevant Knowledge Base Context (RAG):**\n"]
    for chunk in chunks:
        similarity_pct = int(chunk.get("similarity", 0) * 100)
        prefix = f"[{layer_name} Layer] " if layer_name else ""
        header = f"--- {prefix}{chunk['filename']}"
        if chunk.get("start_line") and chunk.get("end_line"):
            header += f" (lines {chunk['start_line']}-{chunk['end_line']}"
            header += f", relevance: {similarity_pct}%) ---"
        else:
            header += f" (relevance: {similarity_pct}%) ---"
        sections.append(header)
        sections.append(chunk["content"])
        sections.append("")

    return "\n".join(sections)


def format_layer_context(chunks: list[dict], layer) -> str:
    """Format chunks with layer persona framing for expert-domain context."""
    if not chunks:
        return ""

    persona = layer.persona_prompt or f"As a {layer.name} domain expert"
    sections = [
        f"**[{layer.name} Expert] Knowledge Context:**",
        f"{persona}, here are the relevant findings:\n",
    ]

    for chunk in chunks:
        similarity_pct = int(chunk.get("similarity", 0) * 100)
        header = f"--- {chunk['filename']}"
        if chunk.get("start_line") and chunk.get("end_line"):
            header += f" (lines {chunk['start_line']}-{chunk['end_line']}"
            header += f", relevance: {similarity_pct}%) ---"
        else:
            header += f" (relevance: {similarity_pct}%) ---"
        sections.append(header)
        sections.append(chunk["content"])
        sections.append("")

    if layer.methodology_prompt:
        sections.append(f"**Analysis methodology:** {layer.methodology_prompt}")

    return "\n".join(sections)


async def remove_document_embeddings(
    db: AsyncSession, project_id, document_id: str
) -> int:
    """Remove all embeddings for a specific document."""
    from .database.crud import document_chunks as dc_crud

    if isinstance(project_id, str):
        project_id = uuid_mod.UUID(project_id)

    count = await dc_crud.delete_chunks_for_document(db, project_id, document_id)
    await db.commit()
    return count


async def get_project_rag_status(db: AsyncSession, project_id) -> dict:
    """Get RAG embedding status for a project."""
    from .database.crud import document_chunks as dc_crud

    if isinstance(project_id, str):
        project_id = uuid_mod.UUID(project_id)

    doc_counts = await dc_crud.get_document_chunk_counts(db, project_id)
    total = await dc_crud.count_chunks(db, project_id)
    layer_counts = await dc_crud.get_layer_chunk_counts(db, project_id)

    return {
        "documents": doc_counts,
        "total_chunks": total,
        "is_active": total > 0,
        "layers": layer_counts,
    }
