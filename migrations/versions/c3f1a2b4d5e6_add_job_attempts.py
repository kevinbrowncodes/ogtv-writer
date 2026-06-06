"""add job attempts

Revision ID: c3f1a2b4d5e6
Revises: 9b12e31396d0
Create Date: 2026-06-06 15:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f1a2b4d5e6"
down_revision: str | Sequence[str] | None = "9b12e31396d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("attempts", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_column("attempts")
