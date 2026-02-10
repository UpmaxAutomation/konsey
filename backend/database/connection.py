"""Database connection management for LLM Council."""

import os
import uuid
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger("llm_council.db")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import select, text

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
engine: Optional[Any] = None
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
        # Detect if using external connection pooler (pgbouncer/Supabase)
        is_using_pooler = "pooler.supabase.com" in DATABASE_URL or "pooler" in DATABASE_URL.lower()

        # For connection poolers (pgbouncer), disable prepared statement cache
        # pgbouncer in transaction/statement mode doesn't support prepared statements
        connect_args = {}
        if is_using_pooler:
            connect_args["statement_cache_size"] = 0

        # Pool configuration
        # - If using external pooler (pgbouncer): NullPool (pooler handles it)
        # - If direct connection: AsyncAdaptedQueuePool with proper settings
        pool_config = {}
        if is_using_pooler:
            pool_config["poolclass"] = NullPool
        else:
            pool_config["poolclass"] = AsyncAdaptedQueuePool
            pool_config["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
            pool_config["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
            pool_config["pool_recycle"] = 3600  # Recycle connections after 1 hour

        engine = create_async_engine(
            DATABASE_URL,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            pool_pre_ping=True,  # Validate connections before use
            connect_args=connect_args,
            **pool_config,
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

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        raise

    # Run lightweight migrations for new columns on existing tables
    await _run_column_migrations()

    try:
        await _ensure_anonymous_user()
    except Exception as e:
        raise


async def _run_column_migrations() -> None:
    """Add missing columns to existing tables (idempotent)."""
    if AsyncSessionLocal is None:
        return

    migrations = [
        ("boards.memory", "ALTER TABLE boards ADD COLUMN IF NOT EXISTS memory JSONB DEFAULT NULL"),
        # v5 foundation: nested boards
        ("boards.parent_board_id", "ALTER TABLE boards ADD COLUMN IF NOT EXISTS parent_board_id UUID REFERENCES boards(id) ON DELETE SET NULL"),
        ("boards.depth", "ALTER TABLE boards ADD COLUMN IF NOT EXISTS depth INTEGER DEFAULT 0"),
        ("boards.icon", "ALTER TABLE boards ADD COLUMN IF NOT EXISTS icon TEXT DEFAULT NULL"),
        # v5 foundation: edge styles
        ("edges.style", "ALTER TABLE edges ADD COLUMN IF NOT EXISTS style JSONB DEFAULT '{}'"),
        # v5.5: edge handle persistence
        ("edges.source_handle", "ALTER TABLE edges ADD COLUMN IF NOT EXISTS source_handle VARCHAR(50) DEFAULT NULL"),
        ("edges.target_handle", "ALTER TABLE edges ADD COLUMN IF NOT EXISTS target_handle VARCHAR(50) DEFAULT NULL"),
        # v5 foundation: card inbox/journal
        ("cards.is_inbox", "ALTER TABLE cards ADD COLUMN IF NOT EXISTS is_inbox BOOLEAN DEFAULT false"),
        ("cards.is_journal", "ALTER TABLE cards ADD COLUMN IF NOT EXISTS is_journal BOOLEAN DEFAULT false"),
        ("cards.journal_date", "ALTER TABLE cards ADD COLUMN IF NOT EXISTS journal_date DATE DEFAULT NULL"),
        # v5 foundation: update card_type check constraint to include board_ref
        ("cards.ck_card_type_v5", """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_card_type') THEN
                    ALTER TABLE cards DROP CONSTRAINT ck_card_type;
                END IF;
                ALTER TABLE cards ADD CONSTRAINT ck_card_type CHECK (
                    card_type IN ('note', 'query', 'council_response', 'council_synthesis', 'file_ref', 'link', 'board_ref')
                );
            END $$;
        """),
        # v6: workflow_output card type
        ("cards.ck_card_type_v6", """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_card_type') THEN
                    ALTER TABLE cards DROP CONSTRAINT ck_card_type;
                END IF;
                ALTER TABLE cards ADD CONSTRAINT ck_card_type CHECK (
                    card_type IN ('note', 'query', 'council_response', 'council_synthesis', 'file_ref', 'link', 'board_ref', 'workflow_output')
                );
            END $$;
        """),
        # v6: workflow_step edge type
        ("edges.ck_edge_type_v6", """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_edge_type') THEN
                    ALTER TABLE edges DROP CONSTRAINT ck_edge_type;
                END IF;
                ALTER TABLE edges ADD CONSTRAINT ck_edge_type CHECK (
                    edge_type IN ('derived_from', 'ranks_above', 'synthesizes', 'related', 'workflow_step')
                );
            END $$;
        """),
        # v6: workflows table
        ("workflows.create_table", """
            CREATE TABLE IF NOT EXISTS workflows (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                template_id VARCHAR(50),
                config JSONB DEFAULT '{}',
                current_step_index INTEGER DEFAULT 0,
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT ck_workflow_status CHECK (status IN ('draft', 'running', 'paused', 'completed', 'failed', 'cancelled'))
            )
        """),
        # v6: workflow_steps table
        ("workflow_steps.create_table", """
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                step_index INTEGER NOT NULL,
                step_type VARCHAR(30) NOT NULL,
                name VARCHAR(200) NOT NULL,
                prompt_template TEXT,
                config JSONB DEFAULT '{}',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                input_card_ids JSONB DEFAULT '[]',
                output_card_ids JSONB DEFAULT '[]',
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT ck_step_type CHECK (step_type IN ('council_query', 'ai_transform', 'combine', 'human_review')),
                CONSTRAINT ck_step_status CHECK (status IN ('pending', 'running', 'waiting_review', 'completed', 'failed', 'skipped'))
            )
        """),
        # v6: agent_runs table
        ("agent_runs.create_table", """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                goal TEXT NOT NULL,
                model VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'running',
                iteration_count INTEGER DEFAULT 0,
                max_iterations INTEGER DEFAULT 20,
                thoughts_log JSONB DEFAULT '[]',
                created_card_ids JSONB DEFAULT '[]',
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT ck_agent_run_status CHECK (status IN ('running', 'paused', 'completed', 'failed', 'cancelled'))
            )
        """),
        # v6: indexes for new tables
        ("workflows.idx_board", "CREATE INDEX IF NOT EXISTS idx_workflows_board ON workflows(board_id)"),
        ("workflow_steps.idx_workflow", "CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow ON workflow_steps(workflow_id)"),
        ("agent_runs.idx_board", "CREATE INDEX IF NOT EXISTS idx_agent_runs_board ON agent_runs(board_id)"),
        # v7: section grouping — cards can belong to a section
        ("cards.section_id", "ALTER TABLE cards ADD COLUMN IF NOT EXISTS section_id UUID REFERENCES sections(id) ON DELETE SET NULL"),
        ("cards.idx_section", "CREATE INDEX IF NOT EXISTS idx_cards_section ON cards(section_id)"),
    ]

    async with AsyncSessionLocal() as session:
        for name, sql in migrations:
            try:
                await session.execute(text(sql))
                await session.commit()
                logger.info(f"Migration OK: {name}")
            except Exception as e:
                await session.rollback()
                logger.warning(f"Migration skipped ({name}): {e}")


async def _ensure_anonymous_user() -> None:
    """Ensure the anonymous user exists for unauthenticated sessions."""
    if AsyncSessionLocal is None:
        return
    anonymous_id = uuid.UUID(ANONYMOUS_USER_ID)
    anonymous_email = f"anonymous-{ANONYMOUS_USER_ID}@local"
    try:
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
    except Exception as e:
        raise


async def close_db() -> None:
    """Close database connection."""
    if not USE_DATABASE or engine is None:
        return
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    if not USE_DATABASE or AsyncSessionLocal is None:
        raise RuntimeError("Database mode is not enabled. Set USE_DATABASE=true")

    # AsyncSessionLocal context manager handles session lifecycle
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        # Note: Do NOT call session.close() - the context manager handles it


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session (for use outside of FastAPI)."""
    if not USE_DATABASE or AsyncSessionLocal is None:
        raise RuntimeError("Database mode is not enabled. Set USE_DATABASE=true")

    # AsyncSessionLocal context manager handles session lifecycle
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        # Note: Do NOT call session.close() - the context manager handles it
