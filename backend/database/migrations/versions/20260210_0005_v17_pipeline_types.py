"""V17: Add pipeline card types and pipeline edge type

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old ck_card_type and re-create with pipeline node types
    op.drop_constraint('ck_card_type', 'cards', type_='check')
    op.create_check_constraint(
        'ck_card_type',
        'cards',
        "card_type IN ('note', 'query', 'council_response', 'council_synthesis', "
        "'file_ref', 'link', 'board_ref', 'workflow_output', 'knowledge', "
        "'pl_input', 'pl_llm', 'pl_council', 'pl_transform', 'pl_output', 'pl_conditional')",
    )

    # Drop old ck_edge_type and re-create with 'pipeline'
    op.drop_constraint('ck_edge_type', 'edges', type_='check')
    op.create_check_constraint(
        'ck_edge_type',
        'edges',
        "edge_type IN ('derived_from', 'ranks_above', 'synthesizes', 'related', "
        "'workflow_step', 'pipeline')",
    )


def downgrade() -> None:
    # Revert ck_edge_type to pre-v17 values
    op.drop_constraint('ck_edge_type', 'edges', type_='check')
    op.create_check_constraint(
        'ck_edge_type',
        'edges',
        "edge_type IN ('derived_from', 'ranks_above', 'synthesizes', 'related', 'workflow_step')",
    )

    # Revert ck_card_type to pre-v17 values
    op.drop_constraint('ck_card_type', 'cards', type_='check')
    op.create_check_constraint(
        'ck_card_type',
        'cards',
        "card_type IN ('note', 'query', 'council_response', 'council_synthesis', "
        "'file_ref', 'link', 'board_ref', 'workflow_output', 'knowledge')",
    )
