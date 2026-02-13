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
        # v7: boards.view_config for canvas/table/kanban view state
        ("boards.view_config", "ALTER TABLE boards ADD COLUMN IF NOT EXISTS view_config JSONB DEFAULT NULL"),
        # v7: property_definitions table
        ("property_definitions.create_table", """
            CREATE TABLE IF NOT EXISTS property_definitions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                property_type VARCHAR(20) NOT NULL,
                options JSONB,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT uq_board_property_name UNIQUE (board_id, name),
                CONSTRAINT ck_property_type CHECK (property_type IN ('text', 'number', 'select', 'multi_select', 'date', 'checkbox', 'url', 'email', 'relation'))
            )
        """),
        ("property_definitions.idx_board", "CREATE INDEX IF NOT EXISTS idx_property_defs_board ON property_definitions(board_id)"),
        # v7: card_property_values table
        ("card_property_values.create_table", """
            CREATE TABLE IF NOT EXISTS card_property_values (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                property_id UUID NOT NULL REFERENCES property_definitions(id) ON DELETE CASCADE,
                value JSONB,
                CONSTRAINT uq_card_property UNIQUE (card_id, property_id)
            )
        """),
        ("card_property_values.idx_card", "CREATE INDEX IF NOT EXISTS idx_card_prop_values_card ON card_property_values(card_id)"),
        ("card_property_values.idx_property", "CREATE INDEX IF NOT EXISTS idx_card_prop_values_property ON card_property_values(property_id)"),
        # v7: tags table
        ("tags.create_table", """
            CREATE TABLE IF NOT EXISTS tags (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(50) NOT NULL,
                color VARCHAR(20) NOT NULL DEFAULT '#4a90e2',
                collection VARCHAR(50),
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT uq_user_tag_name UNIQUE (user_id, name)
            )
        """),
        ("tags.idx_user", "CREATE INDEX IF NOT EXISTS idx_tags_user ON tags(user_id)"),
        # v7: card_tags junction table
        ("card_tags.create_table", """
            CREATE TABLE IF NOT EXISTS card_tags (
                card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (card_id, tag_id)
            )
        """),
        # v7: update card_type constraint to include 'knowledge'
        ("cards.ck_card_type_v7", """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_card_type') THEN
                    ALTER TABLE cards DROP CONSTRAINT ck_card_type;
                END IF;
                ALTER TABLE cards ADD CONSTRAINT ck_card_type CHECK (
                    card_type IN ('note', 'query', 'council_response', 'council_synthesis', 'file_ref', 'link', 'board_ref', 'workflow_output', 'knowledge')
                );
            END $$;
        """),
        # v8: pgvector extension
        ("pgvector.extension", "CREATE EXTENSION IF NOT EXISTS vector"),
        # v8: document_chunks table for RAG
        ("document_chunks.create_table", """
            CREATE TABLE IF NOT EXISTS document_chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                document_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector(1536),
                start_line INTEGER,
                end_line INTEGER,
                tokens INTEGER DEFAULT 0,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """),
        ("document_chunks.idx_project", "CREATE INDEX IF NOT EXISTS idx_doc_chunks_project ON document_chunks(project_id)"),
        ("document_chunks.idx_document", "CREATE INDEX IF NOT EXISTS idx_doc_chunks_document ON document_chunks(project_id, document_id)"),
        ("document_chunks.idx_hnsw", """
            CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding ON document_chunks
            USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
        """),
        # v8.1: knowledge_layers table
        ("knowledge_layers.create_table", """
            CREATE TABLE IF NOT EXISTS knowledge_layers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                persona_prompt TEXT,
                methodology_prompt TEXT,
                color TEXT DEFAULT 'blue',
                icon TEXT DEFAULT 'book',
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """),
        ("knowledge_layers.idx_project", "CREATE INDEX IF NOT EXISTS idx_layers_project ON knowledge_layers(project_id)"),
        # v8.1: add layer_id to document_chunks
        ("document_chunks.add_layer_id", """
            ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS layer_id UUID REFERENCES knowledge_layers(id) ON DELETE SET NULL
        """),
        ("document_chunks.idx_layer", "CREATE INDEX IF NOT EXISTS idx_doc_chunks_layer ON document_chunks(layer_id)"),
        # v9: board_snapshots table for version history
        ("board_snapshots.create_table", """
            CREATE TABLE IF NOT EXISTS board_snapshots (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255),
                description TEXT,
                trigger VARCHAR(30) NOT NULL DEFAULT 'auto',
                snapshot_data JSONB NOT NULL,
                card_count INTEGER DEFAULT 0,
                edge_count INTEGER DEFAULT 0,
                section_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """),
        ("board_snapshots.idx_board", "CREATE INDEX IF NOT EXISTS idx_board_snapshots_board ON board_snapshots(board_id, created_at DESC)"),
        # v9.1: card_mentions table for backlinks
        ("card_mentions.create_table", """
            CREATE TABLE IF NOT EXISTS card_mentions (
                source_card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                target_card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (source_card_id, target_card_id)
            )
        """),
        ("card_mentions.idx_target", "CREATE INDEX IF NOT EXISTS idx_card_mentions_target ON card_mentions(target_card_id)"),
        ("card_mentions.idx_board", "CREATE INDEX IF NOT EXISTS idx_card_mentions_board ON card_mentions(board_id)"),
        # v10: collaboration_sessions tracking
        ("collaboration_sessions.create_table", """
            CREATE TABLE IF NOT EXISTS collaboration_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                connected_at TIMESTAMPTZ DEFAULT now(),
                disconnected_at TIMESTAMPTZ,
                duration_seconds INTEGER
            )
        """),
        ("collaboration_sessions.idx_board", "CREATE INDEX IF NOT EXISTS idx_collab_sessions_board ON collaboration_sessions(board_id)"),
        # v11: user flow templates
        ("user_flow_templates.create_table", """
            CREATE TABLE IF NOT EXISTS user_flow_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                icon VARCHAR(50) DEFAULT 'zap',
                category VARCHAR(50) DEFAULT 'custom',
                steps JSONB NOT NULL,
                config JSONB DEFAULT '{}',
                is_public BOOLEAN DEFAULT false,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """),
        ("user_flow_templates.idx_user", "CREATE INDEX IF NOT EXISTS idx_user_flow_templates_user ON user_flow_templates(user_id)"),
        # v11: workflow execution log
        ("workflow_runs.create_table", """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                status VARCHAR(30) NOT NULL DEFAULT 'running',
                initial_input TEXT,
                started_at TIMESTAMPTZ DEFAULT now(),
                completed_at TIMESTAMPTZ,
                duration_seconds INTEGER,
                step_count INTEGER DEFAULT 0,
                output_card_ids JSONB DEFAULT '[]',
                error TEXT
            )
        """),
        ("workflow_runs.idx_workflow", "CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow ON workflow_runs(workflow_id)"),
        # v11: per-step model selection
        ("workflow_steps.add_model", "ALTER TABLE workflow_steps ADD COLUMN IF NOT EXISTS model VARCHAR(100)"),
        # v11: update step_type check constraint to include 'conditional'
        ("workflow_steps.update_step_type_check", """
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_step_type') THEN
                    ALTER TABLE workflow_steps DROP CONSTRAINT ck_step_type;
                END IF;
                ALTER TABLE workflow_steps ADD CONSTRAINT ck_step_type CHECK (
                    step_type IN ('council_query', 'ai_transform', 'combine', 'human_review', 'conditional')
                );
            END $$;
        """),
        # ============ v12: AI Images + Asset Library ============
        ("generated_images.create_table", """
            CREATE TABLE IF NOT EXISTS generated_images (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                prompt TEXT NOT NULL,
                revised_prompt TEXT,
                provider VARCHAR(30) NOT NULL,
                model VARCHAR(50),
                size VARCHAR(20),
                quality VARCHAR(20),
                style VARCHAR(20),
                image_url TEXT,
                image_data TEXT,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """),
        ("generated_images.idx_project", "CREATE INDEX IF NOT EXISTS idx_gen_images_project ON generated_images(project_id)"),
        ("generated_images.idx_user", "CREATE INDEX IF NOT EXISTS idx_gen_images_user ON generated_images(user_id)"),
        ("asset_library.create_table", """
            CREATE TABLE IF NOT EXISTS asset_library (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                asset_type VARCHAR(30) NOT NULL DEFAULT 'image',
                source VARCHAR(30) NOT NULL DEFAULT 'generated',
                url TEXT,
                thumbnail_url TEXT,
                file_size INTEGER,
                mime_type VARCHAR(100),
                tags TEXT[] DEFAULT '{}',
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT ck_asset_type CHECK (asset_type IN ('image', 'document', 'video', 'audio', 'other')),
                CONSTRAINT ck_asset_source CHECK (source IN ('generated', 'uploaded', 'exported', 'external'))
            )
        """),
        ("asset_library.idx_project", "CREATE INDEX IF NOT EXISTS idx_asset_lib_project ON asset_library(project_id)"),
        ("cards.ck_card_type_v12", """
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_card_type') THEN
                    ALTER TABLE cards DROP CONSTRAINT ck_card_type;
                END IF;
                ALTER TABLE cards ADD CONSTRAINT ck_card_type CHECK (
                    card_type IN ('note','query','council_response','council_synthesis','file_ref','link','board_ref','workflow_output','knowledge','image')
                );
            END $$;
        """),
        # ============ v13: Templates & Marketplace ============
        ("board_templates.create_table", """
            CREATE TABLE IF NOT EXISTS board_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(50) DEFAULT 'general',
                icon VARCHAR(50) DEFAULT 'layout',
                preview_data JSONB DEFAULT '{}',
                template_data JSONB NOT NULL,
                is_public BOOLEAN DEFAULT false,
                use_count INTEGER DEFAULT 0,
                avg_rating FLOAT DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """),
        ("board_templates.idx_user", "CREATE INDEX IF NOT EXISTS idx_board_templates_user ON board_templates(user_id)"),
        ("board_templates.idx_public", "CREATE INDEX IF NOT EXISTS idx_board_templates_public ON board_templates(is_public) WHERE is_public = true"),
        ("template_ratings.create_table", """
            CREATE TABLE IF NOT EXISTS template_ratings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                template_type VARCHAR(30) NOT NULL,
                template_id UUID NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                review TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT ck_template_type CHECK (template_type IN ('board', 'workflow', 'prompt')),
                CONSTRAINT uq_user_template_rating UNIQUE (user_id, template_type, template_id)
            )
        """),
        ("template_ratings.idx_template", "CREATE INDEX IF NOT EXISTS idx_template_ratings_template ON template_ratings(template_type, template_id)"),
        ("user_flow_templates.add_use_count", "ALTER TABLE user_flow_templates ADD COLUMN IF NOT EXISTS use_count INTEGER DEFAULT 0"),
        ("user_flow_templates.add_avg_rating", "ALTER TABLE user_flow_templates ADD COLUMN IF NOT EXISTS avg_rating FLOAT DEFAULT 0"),
        ("user_flow_templates.add_rating_count", "ALTER TABLE user_flow_templates ADD COLUMN IF NOT EXISTS rating_count INTEGER DEFAULT 0"),
        # ============ v16: Card Attachments ============
        ("card_attachments.create_table", """
            CREATE TABLE IF NOT EXISTS card_attachments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                file_type VARCHAR(30) NOT NULL DEFAULT 'file',
                mime_type VARCHAR(100),
                file_size INTEGER,
                url TEXT,
                embed_url TEXT,
                content_text TEXT,
                rag_indexed BOOLEAN DEFAULT false,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT ck_attachment_file_type CHECK (file_type IN ('file', 'image', 'pdf', 'video', 'audio', 'embed'))
            )
        """),
        ("card_attachments.idx_card", "CREATE INDEX IF NOT EXISTS idx_card_attachments_card ON card_attachments(card_id)"),
        ("card_attachments.idx_user", "CREATE INDEX IF NOT EXISTS idx_card_attachments_user ON card_attachments(user_id)"),
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
