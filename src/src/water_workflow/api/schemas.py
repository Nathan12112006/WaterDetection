from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CameraCreate(BaseModel):
    camera_code: str = Field(min_length=1, max_length=64)
    camera_name: str = Field(min_length=1, max_length=128)
    area_name: str = Field(min_length=1, max_length=255)
    source_type: str = Field(default="rtsp", max_length=32)
    rtsp_url: str | None = None
    enabled: bool = True
    roi_config: dict[str, Any] | None = None


class CameraUpdate(BaseModel):
    camera_name: str | None = None
    area_name: str | None = None
    rtsp_url: str | None = None
    enabled: bool | None = None
    roi_config: dict[str, Any] | None = None


class CameraRead(CameraCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class AlarmRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    camera_id: int
    alarm_type: str
    severity: str
    status: str
    confidence: float
    first_detected_at: datetime
    last_detected_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    frame_count: int
    consecutive_count: int
    required_confirmations: int
    last_frame_index: int | None
    area_pixels: int | None
    message: str | None
    created_at: datetime
    updated_at: datetime


class DetectionInput(BaseModel):
    label: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0, le=1)
    bbox: list[float] = Field(min_length=4, max_length=4)
    source_branch: str = Field(default="full_frame", max_length=32)
    area_pixels: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] | None = None


class DetectionEventCreate(BaseModel):
    camera_id: int
    model_version_id: int | None = None
    frame_index: int | None = Field(default=None, ge=0)
    event_time: datetime | None = None
    detections: list[DetectionInput] = Field(min_length=1)


class DetectionEventResponse(BaseModel):
    event_ids: list[int]
    alarm_ids: list[int]


class DetectionEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    camera_id: int
    model_version_id: int | None
    frame_index: int | None
    event_time: datetime
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    source_branch: str
    area_pixels: int | None
    metadata_json: dict[str, Any] | None
    created_at: datetime


class DetectionEventPage(BaseModel):
    items: list[DetectionEventRead]
    page: int
    page_size: int
    total: int


class ModelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    model_name: str
    model_type: str
    weights_path: str
    version: str
    confidence_threshold: float | None
    iou_threshold: float | None
    device: str | None
    image_size: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CameraStatusRead(BaseModel):
    camera: CameraRead
    active_alarm_count: int
    latest_event_time: datetime | None


class AlarmPage(BaseModel):
    items: list[AlarmRead]
    page: int
    page_size: int
    total: int
