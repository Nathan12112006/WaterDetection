from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import AlarmConfig
from ..services.detection_service import DetectionRecord, ingest_detection_records
from .schemas import DetectionEventCreate


def ingest_detection_event(
    db: Session,
    payload: DetectionEventCreate,
    alarm_config: AlarmConfig | None = None,
) -> tuple[list[int], list[int]]:
    try:
        records = [
            DetectionRecord(
                label=item.label,
                confidence=item.confidence,
                bbox=tuple(item.bbox),
                source_branch=item.source_branch,
                area_pixels=item.area_pixels,
                metadata=item.metadata,
            )
            for item in payload.detections
        ]
        return ingest_detection_records(
            db,
            payload.camera_id,
            records,
            model_version_id=payload.model_version_id,
            frame_index=payload.frame_index,
            event_time=payload.event_time,
            alarm_config=alarm_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
