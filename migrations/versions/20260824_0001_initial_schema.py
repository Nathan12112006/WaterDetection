"""Initial workflow database schema."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260824_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("cameras", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("camera_code", sa.String(64), nullable=False, unique=True), sa.Column("camera_name", sa.String(128), nullable=False), sa.Column("area_name", sa.String(255), nullable=False), sa.Column("source_type", sa.String(32), nullable=False), sa.Column("rtsp_url", sa.String(1024)), sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("roi_config", sa.JSON()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("model_versions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("model_name", sa.String(128), nullable=False), sa.Column("model_type", sa.String(32), nullable=False), sa.Column("weights_path", sa.String(1024), nullable=False), sa.Column("version", sa.String(64), nullable=False), sa.Column("confidence_threshold", sa.Float()), sa.Column("iou_threshold", sa.Float()), sa.Column("device", sa.String(32)), sa.Column("image_size", sa.Integer()), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("detection_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False), sa.Column("model_version_id", sa.Integer(), sa.ForeignKey("model_versions.id")), sa.Column("frame_index", sa.Integer()), sa.Column("event_time", sa.DateTime(), nullable=False), sa.Column("label", sa.String(64), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("x1", sa.Float(), nullable=False), sa.Column("y1", sa.Float(), nullable=False), sa.Column("x2", sa.Float(), nullable=False), sa.Column("y2", sa.Float(), nullable=False), sa.Column("source_branch", sa.String(32), nullable=False), sa.Column("area_pixels", sa.Integer()), sa.Column("metadata_json", sa.JSON()), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_detection_events_camera_time", "detection_events", ["camera_id", "event_time"])
    op.create_table("alarms", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False), sa.Column("alarm_type", sa.String(64), nullable=False), sa.Column("severity", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("first_detected_at", sa.DateTime(), nullable=False), sa.Column("last_detected_at", sa.DateTime(), nullable=False), sa.Column("acknowledged_at", sa.DateTime()), sa.Column("resolved_at", sa.DateTime()), sa.Column("frame_count", sa.Integer(), nullable=False), sa.Column("area_pixels", sa.Integer()), sa.Column("message", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_alarms_camera_status", "alarms", ["camera_id", "status"])
    op.create_table("alarm_media", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("alarm_id", sa.Integer(), sa.ForeignKey("alarms.id"), nullable=False), sa.Column("media_type", sa.String(32), nullable=False), sa.Column("file_path", sa.String(1024)), sa.Column("file_url", sa.String(1024)), sa.Column("captured_at", sa.DateTime(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))


def downgrade() -> None:
    op.drop_table("alarm_media")
    op.drop_index("ix_alarms_camera_status", table_name="alarms")
    op.drop_table("alarms")
    op.drop_index("ix_detection_events_camera_time", table_name="detection_events")
    op.drop_table("detection_events")
    op.drop_table("model_versions")
    op.drop_table("cameras")
