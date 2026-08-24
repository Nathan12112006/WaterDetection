from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.models import Alarm, Camera, DetectionEvent
from .schemas import DetectionEventCreate


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def alarm_severity(label: str) -> str:
    normalized = label.lower().replace("_", " ")
    return "critical" if "burst" in normalized or "爆" in label or "喷" in label else "warning"


def ingest_detection_event(db: Session, payload: DetectionEventCreate) -> tuple[list[int], list[int]]:
    camera = db.get(Camera, payload.camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail=f"Camera {payload.camera_id} does not exist")
    event_time = payload.event_time or utcnow()
    event_ids: list[int] = []
    alarm_ids: set[int] = set()
    for item in payload.detections:
        x1, y1, x2, y2 = item.bbox
        event = DetectionEvent(camera_id=payload.camera_id, model_version_id=payload.model_version_id, frame_index=payload.frame_index, event_time=event_time, label=item.label, confidence=item.confidence, x1=x1, y1=y1, x2=x2, y2=y2, source_branch=item.source_branch, area_pixels=item.area_pixels, metadata_json=item.metadata)
        db.add(event)
        db.flush()
        event_ids.append(event.id)
        active_alarm = db.scalar(select(Alarm).where(Alarm.camera_id == payload.camera_id, Alarm.alarm_type == item.label, Alarm.status.in_(("active", "acknowledged"))).order_by(Alarm.id.desc()).limit(1))
        if active_alarm is None:
            active_alarm = Alarm(camera_id=payload.camera_id, alarm_type=item.label, severity=alarm_severity(item.label), status="active", confidence=item.confidence, first_detected_at=event_time, last_detected_at=event_time, frame_count=1, area_pixels=item.area_pixels, message=f"Detected {item.label} at {camera.camera_name}")
            db.add(active_alarm)
            db.flush()
        else:
            active_alarm.last_detected_at = event_time
            active_alarm.confidence = max(active_alarm.confidence, item.confidence)
            active_alarm.frame_count += 1
            if item.area_pixels is not None:
                active_alarm.area_pixels = item.area_pixels
            if active_alarm.status == "acknowledged":
                active_alarm.status = "active"
        alarm_ids.add(active_alarm.id)
    db.commit()
    return event_ids, sorted(alarm_ids)
