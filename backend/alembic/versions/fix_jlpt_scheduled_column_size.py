"""fix_jlpt_scheduled_column_size

Revision ID: fix_jlpt_scheduled
Revises: initial_baseline
Create Date: 2025-11-07

Fixes the jlpt_scheduled column size from String(10) to String(30) to accommodate
ISO datetime strings like '2021-12-01T00:00:00' (19 characters).

This resolves the StringDataRightTruncation error that was preventing 13 candidates
from being imported.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_jlpt_scheduled'
down_revision: Union[str, None] = 'initial_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade: Change jlpt_scheduled column from VARCHAR(10) to VARCHAR(30)
    """
    # Alter the jlpt_scheduled column in candidates table
    op.alter_column(
        'candidates',
        'jlpt_scheduled',
        type_=sa.String(30),
        existing_type=sa.String(10),
        existing_nullable=True
    )


def downgrade() -> None:
    """
    Downgrade: Revert jlpt_scheduled column back to VARCHAR(10)
    WARNING: This may truncate data if values exceed 10 characters!
    """
    op.alter_column(
        'candidates',
        'jlpt_scheduled',
        type_=sa.String(10),
        existing_type=sa.String(30),
        existing_nullable=True
    )
