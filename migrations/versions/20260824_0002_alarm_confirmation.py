"""Add temporal confirmation fields to alarms."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260824_0002"
down_revision: Union[str, None] = "20260824_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("alarms", sa.Column("consecutive_count", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("alarms", sa.Column("required_confirmations", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("alarms", sa.Column("last_frame_index", sa.Integer(), nullable=True))
    op.alter_column("alarms", "consecutive_count", server_default=None)
    op.alter_column("alarms", "required_confirmations", server_default=None)


def downgrade() -> None:
    op.drop_column("alarms", "last_frame_index")
    op.drop_column("alarms", "required_confirmations")
    op.drop_column("alarms", "consecutive_count")
