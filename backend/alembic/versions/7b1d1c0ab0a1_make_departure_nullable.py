"""Make departure column nullable on travel_plans

Revision ID: 7b1d1c0ab0a1
Revises: 5e917d2b7820
Create Date: 2025-11-06 09:50:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b1d1c0ab0a1'
down_revision: Union[str, None] = '5e917d2b7820'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make departure column nullable
    op.alter_column(
        'travel_plans',
        'departure',
        existing_type=sa.String(length=100),
        nullable=True
    )


def downgrade() -> None:
    # Backfill NULLs with a placeholder before making column NOT NULL again
    op.execute("UPDATE travel_plans SET departure = '未知' WHERE departure IS NULL")
    op.alter_column(
        'travel_plans',
        'departure',
        existing_type=sa.String(length=100),
        nullable=False
    )