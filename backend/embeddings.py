"""OpenAI embedding service for RAG."""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


async def get_openai_key(db, user_id) -> Optional[str]:
    """Get OpenAI API key — user key first, then system key, then env."""
    if db and user_id:
        try:
            from .database.crud import api_keys as ak_crud
            key = await ak_crud.resolve_api_key(
                db, user_id, "openai", allow_system_fallback=True
            )
            if key:
                return key
        except Exception as e:
            logger.warning(f"Failed to resolve OpenAI key from DB: {e}")

    # Final fallback: environment variable
    return os.environ.get("OPENAI_API_KEY")


async def generate_embedding(text: str, api_key: str) -> list[float]:
    """Generate a single embedding vector for the given text."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            OPENAI_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": EMBEDDING_MODEL, "input": text},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


async def generate_embeddings_batch(
    texts: list[str], api_key: str, batch_size: int = 100
) -> list[list[float]]:
    """Generate embeddings for a batch of texts.

    Chunks into groups of batch_size to stay within API limits.
    """
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                OPENAI_EMBEDDINGS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": EMBEDDING_MODEL, "input": batch},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            # Sort by index to maintain order
            data.sort(key=lambda x: x["index"])
            all_embeddings.extend([d["embedding"] for d in data])
    return all_embeddings
