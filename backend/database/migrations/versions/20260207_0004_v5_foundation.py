"""V5 foundation: sections, nested boards, inbox/journal cards, edge styles

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Sections table ---
    op.create_table(
        'sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('board_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('boards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.Text, nullable=False, server_default=''),
        sa.Column('color', sa.Text, nullable=False, server_default='gray'),
        sa.Column('x', sa.Float, nullable=False, server_default='0'),
        sa.Column('y', sa.Float, nullable=False, server_default='0'),
        sa.Column('width', sa.Float, nullable=False, server_default='400'),
        sa.Column('height', sa.Float, nullable=False, server_default='300'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_sections_board', 'sections', ['board_id'])

    # --- Edges: add style column ---
    op.add_column('edges', sa.Column('style', postgresql.JSONB, server_default='{}'))

    # --- Boards: nested boards support ---
    op.add_column('boards', sa.Column('parent_board_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_boards_parent_board_id',
        'boards', 'boards',
        ['parent_board_id'], ['id'],
        ondelete='SET NULL',
    )
    op.add_column('boards', sa.Column('depth', sa.Integer, server_default='0'))
    op.add_column('boards', sa.Column('icon', sa.Text, nullable=True))
    op.create_index('idx_boards_parent', 'boards', ['parent_board_id'])

    # --- Cards: drop old ck_card_type, re-create with 'board_ref' ---
    op.drop_constraint('ck_card_type', 'cards', type_='check')
    op.create_check_constraint(
        'ck_card_type',
        'cards',
        "card_type IN ('note', 'query', 'council_response', 'council_synthesis', 'file_ref', 'link', 'board_ref')",
    )

    # --- Cards: inbox / journal columns ---
    op.add_column('cards', sa.Column('is_inbox', sa.Boolean, server_default='false'))
    op.add_column('cards', sa.Column('is_journal', sa.Boolean, server_default='false'))
    op.add_column('cards', sa.Column('journal_date', sa.Date, nullable=True))

    # Partial indexes for inbox and journal queries
    op.create_index(
        'idx_cards_journal',
        'cards',
        ['board_id', 'journal_date'],
        postgresql_where=sa.text('is_journal = true'),
    )
    op.create_index(
        'idx_cards_inbox',
        'cards',
        ['board_id', 'created_at'],
        postgresql_where=sa.text('is_inbox = true'),
    )


def downgrade() -> None:
    # --- Cards: remove partial indexes ---
    op.drop_index('idx_cards_inbox', table_name='cards')
    op.drop_index('idx_cards_journal', table_name='cards')

    # --- Cards: remove inbox / journal columns ---
    op.drop_column('cards', 'journal_date')
    op.drop_column('cards', 'is_journal')
    op.drop_column('cards', 'is_inbox')

    # --- Cards: revert ck_card_type to original ---
    op.drop_constraint('ck_card_type', 'cards', type_='check')
    op.create_check_constraint(
        'ck_card_type',
        'cards',
        "card_type IN ('note', 'query', 'council_response', 'council_synthesis', 'file_ref', 'link')",
    )

    # --- Boards: remove nested board columns ---
    op.drop_index('idx_boards_parent', table_name='boards')
    op.drop_column('boards', 'icon')
    op.drop_column('boards', 'depth')
    op.drop_constraint('fk_boards_parent_board_id', 'boards', type_='foreignkey')
    op.drop_column('boards', 'parent_board_id')

    # --- Edges: remove style ---
    op.drop_column('edges', 'style')

    # --- Sections table ---
    op.drop_index('idx_sections_board', table_name='sections')
    op.drop_table('sections')
