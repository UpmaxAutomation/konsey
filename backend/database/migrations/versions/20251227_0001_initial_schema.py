"""Initial database schema

Revision ID: 0001
Revises:
Create Date: 2025-12-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('google_id', sa.String(255), unique=True, nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('is_admin', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # User settings table
    op.create_table(
        'user_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True),
        sa.Column('council_models', postgresql.JSON, default=list),
        sa.Column('chairman_model', sa.String(255), nullable=True),
        sa.Column('enhanced_features', postgresql.JSON, default=dict),
        sa.Column('personas', postgresql.JSON, default=dict),
        sa.Column('custom_personas', postgresql.JSON, default=dict),
        sa.Column('budget_config', postgresql.JSON, default=dict),
        sa.Column('theme', sa.String(20), default='light'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # User API keys table
    op.create_table(
        'user_api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('encrypted_key', sa.Text, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_provider'),
    )

    # Projects table (before conversations for FK)
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('system_prompt', sa.Text, nullable=True),
        sa.Column('council_config', postgresql.JSON, nullable=True),
        sa.Column('knowledge_base', postgresql.JSON, default=list),
        sa.Column('memory', postgresql.JSON, default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Folders table
    op.create_table(
        'folders',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('color', sa.String(10), default='#4a90e2'),
        sa.Column('icon', sa.String(50), default='folder'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True),
        sa.Column('title', sa.String(500), default='New Conversation'),
        sa.Column('folder_id', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text), default=list),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_conversations_user_created', 'conversations', ['user_id', 'created_at'])

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), index=True),
        sa.Column('message_index', sa.Integer, nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('message_type', sa.String(20), default='council'),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('stage1', postgresql.JSON, nullable=True),
        sa.Column('stage2', postgresql.JSON, nullable=True),
        sa.Column('stage3', postgresql.JSON, nullable=True),
        sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.Column('thinking', sa.Text, nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('usage_info', postgresql.JSON, nullable=True),
        sa.Column('attached_files', postgresql.ARRAY(sa.Text), default=list),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_messages_conversation_index', 'messages', ['conversation_id', 'message_index'])

    # Refresh tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_info', sa.Text, nullable=True),
        sa.Column('is_revoked', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Ratings table
    op.create_table(
        'ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE')),
        sa.Column('message_index', sa.Integer, nullable=False),
        sa.Column('model_id', sa.String(100), nullable=False),
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('feedback_text', sa.Text, nullable=True),
        sa.Column('query_category', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'conversation_id', 'message_index', 'model_id', name='uq_user_conv_msg_model'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='ck_rating_range'),
    )

    # Usage analytics table
    op.create_table(
        'usage_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('input_tokens', sa.Integer, default=0),
        sa.Column('output_tokens', sa.Integer, default=0),
        sa.Column('cost', sa.Float, default=0.0),
        sa.Column('request_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_usage_user_date', 'usage_analytics', ['user_id', 'request_date'])

    # System config table
    op.create_table(
        'system_config',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('encrypted', sa.Boolean, default=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('system_config')
    op.drop_table('usage_analytics')
    op.drop_table('ratings')
    op.drop_table('refresh_tokens')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('folders')
    op.drop_table('projects')
    op.drop_table('user_api_keys')
    op.drop_table('user_settings')
    op.drop_table('users')
