"""Database connection management for LLM Council."""

import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import select

# Load .env file before reading environment variables
from dotenv import load_dotenv
# Try multiple paths to find .env file
env_paths = [
    Path(__file__).parent.parent.parent / '.env',  # Project root
    Path(__file__).parent.parent / '.env',  # Backend directory
    Path('.env'),  # Current directory
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        break
else:
    # Fallback: try loading from current directory
    load_dotenv(override=True)

from .models import Base, User
from ..config import ANONYMOUS_USER_ID

# Check if database mode is enabled
USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://council:council@localhost:5432/llm_council"
)

# Only create engine and session factory if database mode is enabled
engine: Optional[any] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None

if USE_DATABASE:
    # Validate DATABASE_URL before creating engine
    if not DATABASE_URL or not DATABASE_URL.strip():
        raise ValueError(
            f"DATABASE_URL is not set or empty. "
            f"Current value: {repr(DATABASE_URL)}. "
            f"Please set DATABASE_URL in your .env file."
        )
    
    # Create async engine
    try:
        engine = create_async_engine(
            DATABASE_URL,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            poolclass=NullPool,  # Use NullPool for better async compatibility
        )
    except Exception as e:
        raise ValueError(
            f"Failed to create database engine with URL: {DATABASE_URL[:60]}... "
            f"Error: {e}. "
            f"Please check your DATABASE_URL format in .env file."
        ) from e

    # Create async session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def init_db() -> None:
    """Initialize database tables."""
    if not USE_DATABASE or engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_anonymous_user()


async def _ensure_anonymous_user() -> None:
    """Ensure the anonymous user exists for unauthenticated sessions."""
    if AsyncSessionLocal is None:
        return
    anonymous_id = uuid.UUID(ANONYMOUS_USER_ID)
    anonymous_email = f"anonymous-{ANONYMOUS_USER_ID}@local"
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == anonymous_id)
        )
        if result.scalar_one_or_none() is None:
            session.add(
                User(
                    id=anonymous_id,
                    email=anonymous_email,
                    name="Anonymous",
                    is_active=True,
                    is_verified=True,
                )
            )
            await session.commit()


async def close_db() -> None:
    """Close database connection."""
    if not USE_DATABASE or engine is None:
        return
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    if not USE_DATABASE or AsyncSessionLocal is None:
        raise RuntimeError("Database mode is not enabled. Set USE_DATABASE=true")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session (for use outside of FastAPI)."""
    if not USE_DATABASE or AsyncSessionLocal is None:
        raise RuntimeError("Database mode is not enabled. Set USE_DATABASE=true")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
