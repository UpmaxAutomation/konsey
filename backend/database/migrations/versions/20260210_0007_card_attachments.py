"""V20: Card attachments table

Revision ID: 0007
Revises: 0006
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'card_attachments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('card_id', UUID(as_uuid=True), sa.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(30), nullable=False, server_default='file'),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('url', sa.Text, nullable=True),
        sa.Column('embed_url', sa.Text, nullable=True),
        sa.Column('content_text', sa.Text, nullable=True),
        sa.Column('rag_indexed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('metadata', sa.JSON, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_card_attachments_card', 'card_attachments', ['card_id'])
    op.create_index('idx_card_attachments_user', 'card_attachments', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_card_attachments_user', 'card_attachments')
    op.drop_index('idx_card_attachments_card', 'card_attachments')
    op.drop_table('card_attachments')
