"""V19: Cross-board linked cards, library flag, linked edge type

Revision ID: 0006
Revises: 0005
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source_card_id FK for linked cards
    op.add_column('cards', sa.Column('source_card_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_cards_source_card', 'cards', 'cards',
        ['source_card_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('idx_cards_source', 'cards', ['source_card_id'],
                    postgresql_where=sa.text('source_card_id IS NOT NULL'))

    # Add is_library flag
    op.add_column('cards', sa.Column('is_library', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('idx_cards_library', 'cards', ['board_id', 'is_library'],
                    postgresql_where=sa.text('is_library = true'))

    # Update ck_card_type to include 'linked_card'
    op.drop_constraint('ck_card_type', 'cards', type_='check')
    op.create_check_constraint(
        'ck_card_type',
        'cards',
        "card_type IN ('note', 'query', 'council_response', 'council_synthesis', "
        "'file_ref', 'link', 'board_ref', 'workflow_output', 'knowledge', "
        "'pl_input', 'pl_llm', 'pl_council', 'pl_transform', 'pl_output', 'pl_conditional', "
        "'linked_card')",
    )

    # Update ck_edge_type to include 'linked'
    op.drop_constraint('ck_edge_type', 'edges', type_='check')
    op.create_check_constraint(
        'ck_edge_type',
        'edges',
        "edge_type IN ('derived_from', 'ranks_above', 'synthesizes', 'related', "
        "'workflow_step', 'pipeline', 'linked')",
    )


def downgrade() -> None:
    # Revert ck_edge_type
    op.drop_constraint('ck_edge_type', 'edges', type_='check')
    op.create_check_constraint(
        'ck_edge_type',
        'edges',
        "edge_type IN ('derived_from', 'ranks_above', 'synthesizes', 'related', "
        "'workflow_step', 'pipeline')",
    )

    # Revert ck_card_type
    op.drop_constraint('ck_card_type', 'cards', type_='check')
    op.create_check_constraint(
        'ck_card_type',
        'cards',
        "card_type IN ('note', 'query', 'council_response', 'council_synthesis', "
        "'file_ref', 'link', 'board_ref', 'workflow_output', 'knowledge', "
        "'pl_input', 'pl_llm', 'pl_council', 'pl_transform', 'pl_output', 'pl_conditional')",
    )

    # Drop is_library
    op.drop_index('idx_cards_library', 'cards')
    op.drop_column('cards', 'is_library')

    # Drop source_card_id
    op.drop_index('idx_cards_source', 'cards')
    op.drop_constraint('fk_cards_source_card', 'cards', type_='foreignkey')
    op.drop_column('cards', 'source_card_id')
