"""Add vision event history and notification outbox."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260827_0003"
down_revision: Union[str, None] = "20260824_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vision_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("event_revision", sa.Integer(), nullable=False),
        sa.Column("event_status", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("camera_id", sa.String(128), nullable=False),
        sa.Column("risk_region_id", sa.String(128)),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_branches", sa.JSON(), nullable=False),
        sa.Column("model_versions", sa.JSON(), nullable=False),
        sa.Column("config_revision", sa.String(128), nullable=False),
        sa.Column("bbox", sa.JSON()),
        sa.Column("area_ratio_in_risk_region", sa.Float()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("event_id", "event_revision", name="uq_vision_events_event_revision"),
    )
    op.create_index("ix_vision_events_camera_time", "vision_events", ["camera_id", "occurred_at"])
    op.create_table(
        "vision_event_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("event_revision", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("event_id", "event_revision", name="uq_vision_outbox_event_revision"),
    )
    op.create_index("ix_vision_outbox_status_next_attempt", "vision_event_outbox", ["status", "next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_vision_outbox_status_next_attempt", table_name="vision_event_outbox")
    op.drop_table("vision_event_outbox")
    op.drop_index("ix_vision_events_camera_time", table_name="vision_events")
    op.drop_table("vision_events")
