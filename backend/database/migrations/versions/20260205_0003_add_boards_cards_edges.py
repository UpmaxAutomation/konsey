"""Add boards, cards, edges tables for canvas feature

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Boards table
    op.create_table(
        'boards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False, server_default='Untitled Board'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('viewport', sa.JSON, server_default='{"x": 0, "y": 0, "zoom": 1}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_boards_user_updated', 'boards', ['user_id', 'updated_at'])
    op.create_index('idx_boards_project', 'boards', ['project_id'])

    # Cards table
    op.create_table(
        'cards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('board_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('boards.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('card_type', sa.String(30), nullable=False, server_default='note'),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('position_x', sa.Float, nullable=False, server_default='0'),
        sa.Column('position_y', sa.Float, nullable=False, server_default='0'),
        sa.Column('width', sa.Float, nullable=False, server_default='280'),
        sa.Column('height', sa.Float, nullable=False, server_default='200'),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('source_message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('extra', sa.JSON, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "card_type IN ('note', 'query', 'council_response', 'council_synthesis', 'file_ref', 'link')",
            name='ck_card_type'
        ),
    )

    # Edges table
    op.create_table(
        'edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('board_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('boards.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('from_card_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('to_card_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('edge_type', sa.String(30), nullable=False, server_default='related'),
        sa.Column('label', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('from_card_id', 'to_card_id', 'edge_type', name='uq_edge_from_to_type'),
        sa.CheckConstraint(
            "edge_type IN ('derived_from', 'ranks_above', 'synthesizes', 'related')",
            name='ck_edge_type'
        ),
    )


def downgrade() -> None:
    op.drop_table('edges')
    op.drop_table('cards')
    op.drop_table('boards')
