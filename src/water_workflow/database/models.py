from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Camera(TimestampMixin, Base):
    __tablename__ = "cameras"
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    camera_name: Mapped[str] = mapped_column(String(128), nullable=False)
    area_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="rtsp", nullable=False)
    rtsp_url: Mapped[str | None] = mapped_column(String(1024))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    roi_config: Mapped[dict | None] = mapped_column(JSON)


class ModelVersion(TimestampMixin, Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    weights_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_threshold: Mapped[float | None] = mapped_column(Float)
    iou_threshold: Mapped[float | None] = mapped_column(Float)
    device: Mapped[str | None] = mapped_column(String(32))
    image_size: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DetectionEvent(Base):
    __tablename__ = "detection_events"
    __table_args__ = (Index("ix_detection_events_camera_time", "camera_id", "event_time"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False)
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id"))
    frame_index: Mapped[int | None] = mapped_column(Integer)
    event_time: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    x1: Mapped[float] = mapped_column(Float, nullable=False)
    y1: Mapped[float] = mapped_column(Float, nullable=False)
    x2: Mapped[float] = mapped_column(Float, nullable=False)
    y2: Mapped[float] = mapped_column(Float, nullable=False)
    source_branch: Mapped[str] = mapped_column(String(32), default="full_frame", nullable=False)
    area_pixels: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Alarm(TimestampMixin, Base):
    __tablename__ = "alarms"
    __table_args__ = (Index("ix_alarms_camera_status", "camera_id", "status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False)
    alarm_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="warning", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    frame_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    consecutive_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    required_confirmations: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_frame_index: Mapped[int | None] = mapped_column(Integer)
    area_pixels: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)


class AlarmMedia(Base):
    __tablename__ = "alarm_media"
    id: Mapped[int] = mapped_column(primary_key=True)
    alarm_id: Mapped[int] = mapped_column(ForeignKey("alarms.id"), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024))
    file_url: Mapped[str | None] = mapped_column(String(1024))
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class VisionEventRecord(Base):
    """Versioned visual events owned by the vision service."""

    __tablename__ = "vision_events"
    __table_args__ = (
        UniqueConstraint("event_id", "event_revision", name="uq_vision_events_event_revision"),
        Index("ix_vision_events_camera_time", "camera_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    event_status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    camera_id: Mapped[str] = mapped_column(String(128), nullable=False)
    risk_region_id: Mapped[str | None] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source_branches: Mapped[list] = mapped_column(JSON, nullable=False)
    model_versions: Mapped[list] = mapped_column(JSON, nullable=False)
    config_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    bbox: Mapped[list | None] = mapped_column(JSON)
    area_ratio_in_risk_region: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class VisionEventOutbox(Base):
    """Durable delivery record for retryable backend notifications."""

    __tablename__ = "vision_event_outbox"
    __table_args__ = (
        UniqueConstraint("event_id", "event_revision", name="uq_vision_outbox_event_revision"),
        Index("ix_vision_outbox_status_next_attempt", "status", "next_attempt_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
