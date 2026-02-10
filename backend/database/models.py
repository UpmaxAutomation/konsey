"""SQLAlchemy models for LLM Council."""

import uuid
from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import (
    String, Text, Boolean, Integer, Float, DateTime, Date, ForeignKey,
    JSON, ARRAY, Index, UniqueConstraint, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Null for OAuth-only
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    api_keys: Mapped[List["UserAPIKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    folders: Mapped[List["Folder"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    ratings: Mapped[List["Rating"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    boards: Mapped[List["Board"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    """Per-user settings and configuration."""
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    council_models: Mapped[dict] = mapped_column(JSON, default=list)
    chairman_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    enhanced_features: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "web_search": True,
            "deep_search": False,
            "code_execution": True,
            "memory": True,
            "auto_preference": "quality",
        },
    )
    personas: Mapped[dict] = mapped_column(JSON, default=dict)
    custom_personas: Mapped[dict] = mapped_column(JSON, default=dict)
    budget_config: Mapped[dict] = mapped_column(JSON, default=dict)
    custom_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # User's custom system prompt
    theme: Mapped[str] = mapped_column(String(20), default="light")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="settings")


class UserAPIKey(Base):
    """Per-user API keys for providers (encrypted)."""
    __tablename__ = "user_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # openai, anthropic, google, etc.
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
        Index("idx_user_provider_active", "user_id", "provider", "is_active"),  # Performance: API key lookups
    )


class Conversation(Base):
    """Conversation model."""
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500), default="New Conversation")
    folder_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan", order_by="Message.message_index")
    project: Mapped[Optional["Project"]] = relationship(back_populates="conversations")

    __table_args__ = (
        Index("idx_conversations_user_created", "user_id", "created_at"),
    )


class Message(Base):
    """Message model (normalized from embedded JSON)."""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    message_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant
    message_type: Mapped[str] = mapped_column(String(20), default="council")  # council, quick, debate
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For user messages
    stage1: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of model responses
    stage2: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Rankings
    stage3: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Final synthesis
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # label_to_model, aggregate_rankings
    thinking: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For reasoning models
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # For quick mode
    usage_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Token usage
    attached_files: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conversation_index", "conversation_id", "message_index"),
    )


class Folder(Base):
    """Folder for organizing conversations."""
    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(10), default="#4a90e2")
    icon: Mapped[str] = mapped_column(String(50), default="folder")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="folders")


class Project(Base):
    """Project with knowledge base and memory."""
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    council_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    knowledge_base: Mapped[list] = mapped_column(JSON, default=list)
    memory: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="projects")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="project")
    boards: Mapped[List["Board"]] = relationship(back_populates="project")


class RefreshToken(Base):
    """Refresh tokens for session management."""
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Rating(Base):
    """User ratings for model responses."""
    __tablename__ = "ratings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"))
    message_index: Mapped[int] = mapped_column(Integer, nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    query_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("user_id", "conversation_id", "message_index", "model_id", name="uq_user_conv_msg_model"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
    )


class UsageAnalytics(Base):
    """Per-user usage tracking."""
    __tablename__ = "usage_analytics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    request_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_usage_user_date", "user_id", "request_date"),
    )


class SystemConfig(Base):
    """System-wide configuration (admin-level)."""
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Team(Base):
    """Team/Workspace for collaboration."""
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)  # Team-wide council config
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    members: Mapped[List["TeamMembership"]] = relationship(back_populates="team", cascade="all, delete-orphan")
    shared_conversations: Mapped[List["TeamConversation"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class TeamMembership(Base):
    """User membership in a team."""
    __tablename__ = "team_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # owner, admin, member
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_user"),
    )


class TeamConversation(Base):
    """Conversation shared with a team."""
    __tablename__ = "team_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"))
    shared_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    shared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="shared_conversations")

    __table_args__ = (
        UniqueConstraint("team_id", "conversation_id", name="uq_team_conversation"),
    )


class APIKey(Base):
    """Public API keys for external access."""
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)  # First 8 chars for identification
    scopes: Mapped[list] = mapped_column(ARRAY(Text), default=list)  # chat, export, read, etc.
    rate_limit: Mapped[int] = mapped_column(Integer, default=100)  # Requests per minute
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromptTemplate(Base):
    """Reusable prompt templates."""
    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # Null = system template
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list] = mapped_column(JSON, default=list)  # [{name, description, default}]
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # coding, writing, analysis, etc.
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_templates_user_category", "user_id", "category"),
    )


class UserMemory(Base):
    """Per-user memory storage for facts, decisions, and preferences."""
    __tablename__ = "user_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    memory_type: Mapped[str] = mapped_column(String(20), nullable=False)  # fact, decision, preference
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # general, technical, etc.
    content: Mapped[str] = mapped_column(Text, nullable=False)  # JSON for complex data
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_user_memory_type", "user_id", "memory_type"),
    )


class EmailVerificationToken(Base):
    """Email verification tokens for user registration."""
    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User")


class Board(Base):
    """Canvas board for visual organization of council artifacts."""
    __tablename__ = "boards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Board")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    viewport: Mapped[dict] = mapped_column(JSON, default=lambda: {"x": 0, "y": 0, "zoom": 1})
    parent_board_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="SET NULL"), nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    memory: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="boards")
    project: Mapped[Optional["Project"]] = relationship(back_populates="boards")
    cards: Mapped[List["Card"]] = relationship(back_populates="board", cascade="all, delete-orphan")
    edges: Mapped[List["Edge"]] = relationship(back_populates="board", cascade="all, delete-orphan")
    sections: Mapped[List["Section"]] = relationship(back_populates="board", cascade="all, delete-orphan")
    workflows: Mapped[List["Workflow"]] = relationship(back_populates="board", cascade="all, delete-orphan")
    children: Mapped[List["Board"]] = relationship(back_populates="parent", foreign_keys="[Board.parent_board_id]")
    parent: Mapped[Optional["Board"]] = relationship(back_populates="children", remote_side="[Board.id]", foreign_keys="[Board.parent_board_id]")

    __table_args__ = (
        Index("idx_boards_user_updated", "user_id", "updated_at"),
        Index("idx_boards_project", "project_id"),
        Index("idx_boards_parent", "parent_board_id"),
    )


class Section(Base):
    """A visual grouping section on a canvas board."""
    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    color: Mapped[str] = mapped_column(Text, nullable=False, default="gray")
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=400.0)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=300.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    board: Mapped["Board"] = relationship(back_populates="sections")
    cards: Mapped[List["Card"]] = relationship(back_populates="section", foreign_keys="[Card.section_id]")

    __table_args__ = (
        Index("idx_sections_board", "board_id"),
    )


class Card(Base):
    """A card/node on a canvas board."""
    __tablename__ = "cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    card_type: Mapped[str] = mapped_column(String(30), nullable=False, default="note")
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=280.0)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=200.0)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    source_conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    is_inbox: Mapped[bool] = mapped_column(Boolean, default=False)
    is_journal: Mapped[bool] = mapped_column(Boolean, default=False)
    journal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    board: Mapped["Board"] = relationship(back_populates="cards")
    section: Mapped[Optional["Section"]] = relationship(back_populates="cards", foreign_keys=[section_id])

    __table_args__ = (
        CheckConstraint(
            "card_type IN ('note', 'query', 'council_response', 'council_synthesis', 'file_ref', 'link', 'board_ref', 'workflow_output')",
            name="ck_card_type"
        ),
        Index("idx_cards_journal", "board_id", "journal_date", postgresql_where=text("is_journal = true")),
        Index("idx_cards_inbox", "board_id", "created_at", postgresql_where=text("is_inbox = true")),
    )


class Edge(Base):
    """An edge/connection between two cards on a board."""
    __tablename__ = "edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    from_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"))
    to_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"))
    edge_type: Mapped[str] = mapped_column(String(30), nullable=False, default="related")
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    style: Mapped[dict] = mapped_column(JSON, default=dict)
    source_handle: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_handle: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    board: Mapped["Board"] = relationship(back_populates="edges")

    __table_args__ = (
        UniqueConstraint("from_card_id", "to_card_id", "edge_type", name="uq_edge_from_to_type"),
        CheckConstraint(
            "edge_type IN ('derived_from', 'ranks_above', 'synthesizes', 'related', 'workflow_step')",
            name="ck_edge_type"
        ),
    )


class Workflow(Base):
    """A multi-step AI pipeline on a canvas board."""
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    template_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    board: Mapped["Board"] = relationship(back_populates="workflows")
    steps: Mapped[List["WorkflowStep"]] = relationship(back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowStep.step_index")

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'running', 'paused', 'completed', 'failed', 'cancelled')",
            name="ck_workflow_status"
        ),
        Index("idx_workflows_board", "board_id"),
    )


class WorkflowStep(Base):
    """A single step in a workflow pipeline."""
    __tablename__ = "workflow_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    input_card_ids: Mapped[list] = mapped_column(JSON, default=list)
    output_card_ids: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="steps")

    __table_args__ = (
        CheckConstraint(
            "step_type IN ('council_query', 'ai_transform', 'combine', 'human_review')",
            name="ck_step_type"
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'waiting_review', 'completed', 'failed', 'skipped')",
            name="ck_step_status"
        ),
        Index("idx_workflow_steps_workflow", "workflow_id"),
    )


class AgentRun(Base):
    """An autonomous agent run that populates a board."""
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    iteration_count: Mapped[int] = mapped_column(Integer, default=0)
    max_iterations: Mapped[int] = mapped_column(Integer, default=20)
    thoughts_log: Mapped[list] = mapped_column(JSON, default=list)
    created_card_ids: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'paused', 'completed', 'failed', 'cancelled')",
            name="ck_agent_run_status"
        ),
        Index("idx_agent_runs_board", "board_id"),
    )
