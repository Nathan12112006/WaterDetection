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


class AlarmPage(BaseModel):
    items: list[AlarmRead]
    page: int
    page_size: int
    total: int
