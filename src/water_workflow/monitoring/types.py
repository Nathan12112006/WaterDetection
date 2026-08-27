from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

import numpy as np

from ..video.types import FramePacket


class WorkerState(str, Enum):
    CONFIGURED = "CONFIGURED"
    WARMING_UP = "WARMING_UP"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    STOPPED = "STOPPED"


class ServiceState(str, Enum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    NOT_READY = "NOT_READY"


class EventLifecycleState(str, Enum):
    NORMAL = "NORMAL"
    SUSPECTED = "SUSPECTED"
    CONFIRMED = "CONFIRMED"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True)
class DetectionEvidence:
    camera_id: str
    frame_index: int
    captured_at: datetime
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    source_branch: str
    model_version: str = "unregistered"
    config_revision: str = "unversioned"
    risk_region_id: str | None = None


@dataclass(frozen=True)
class SegmentationEvidence:
    camera_id: str
    frame_index: int
    captured_at: datetime
    class_name: str
    confidence: float
    polygon: tuple[tuple[int, int], ...]
    bbox: tuple[int, int, int, int]
    source_branch: str = "water_surface_segmentation"
    mask_area_pixels: int | None = None
    area_ratio_in_risk_region: float | None = None
    risk_region_id: str | None = None
    model_version: str = "unregistered"
    config_revision: str = "unversioned"


@dataclass(frozen=True)
class VisionEvent:
    event_id: str
    event_revision: int
    event_status: str
    event_type: str
    camera_id: str
    risk_region_id: str | None
    occurred_at: datetime
    confidence: float
    source_branches: tuple[str, ...]
    model_versions: tuple[str, ...]
    config_revision: str
    bbox: tuple[int, int, int, int] | None = None
    area_ratio_in_risk_region: float | None = None


@dataclass
class FrameProcessingResult:
    frame: FramePacket
    detections: list[DetectionEvidence] = field(default_factory=list)
    segments: list[SegmentationEvidence] = field(default_factory=list)
    annotated_frame: np.ndarray | None = None
    branch_latencies_ms: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkerSnapshot:
    camera_id: str
    state: WorkerState
    started_at: datetime | None
    last_frame_at: datetime | None
    last_inference_at: datetime | None
    frames_received: int
    frames_processed: int
    frames_dropped: int
    last_frame_age_ms: float | None
    last_error: str | None
    last_inference_latency_ms: float | None = None
    inference_timeout_count: int = 0


class FrameSource(Protocol):
    is_live: bool

    def open(self) -> None: ...

    def read(self) -> FramePacket | None: ...

    def close(self) -> None: ...


class FrameProcessor(Protocol):
    def process(self, packet: FramePacket) -> FrameProcessingResult: ...


class FrameResultSink(Protocol):
    def publish(self, result: FrameProcessingResult) -> None: ...

    def close(self) -> None: ...


class VisionEventSink(Protocol):
    def publish(self, event: VisionEvent) -> None: ...

    def close(self) -> None: ...


class NullFrameResultSink:
    def publish(self, result: FrameProcessingResult) -> None:
        return None

    def close(self) -> None:
        return None


class NullVisionEventSink:
    def publish(self, event: VisionEvent) -> None:
        return None

    def close(self) -> None:
        return None
