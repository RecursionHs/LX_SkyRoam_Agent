"""Remove traveler specific columns; preferences JSON now stores them

Revision ID: 2025012801
Revises: 5e917d2b7820
Create Date: 2025-01-28 00:00:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2025012801"
down_revision = "5e917d2b7820"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("travel_plans") as batch_op:
        batch_op.drop_column("dietaryRestrictions")
        batch_op.drop_column("foodPreferences")
        batch_op.drop_column("ageGroups")
        batch_op.drop_column("travelers")


def downgrade() -> None:
    with op.batch_alter_table("travel_plans") as batch_op:
        batch_op.add_column(sa.Column("travelers", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("ageGroups", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("foodPreferences", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("dietaryRestrictions", sa.JSON(), nullable=True))
