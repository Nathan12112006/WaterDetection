from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import AlarmConfig, ModelConfig
from ..database.models import Alarm, Camera, DetectionEvent, ModelVersion
from ..models.base import Detection


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def alarm_severity(label: str) -> str:
    normalized = label.lower().replace("_", " ")
    return "critical" if "burst" in normalized or "爆" in label or "喷" in label else "warning"


def normalize_label(label: str) -> str:
    return " ".join(label.lower().replace("_", " ").replace("-", " ").split())


def required_confirmations(label: str, policy: AlarmConfig) -> int:
    """Return the number of consecutive frames required for a label."""
    water_drop_labels = {normalize_label(item) for item in policy.water_drop_labels}
    if normalize_label(label) in water_drop_labels:
        return 1
    return max(1, int(policy.confirmation_frames))


@dataclass(frozen=True)
class DetectionRecord:
    label: str
    confidence: float
    bbox: tuple[float, float, float, float]
    source_branch: str = "full_frame"
    area_pixels: int | None = None
    metadata: dict | None = None


def register_model_version(db: Session, config: ModelConfig) -> int:
    """Register the model configuration once and return its database id."""
    weights_path = str(Path(config.weights).resolve()) if config.weights else "builtin://noop"
    path = Path(config.weights) if config.weights else None
    version = f"{config.backend}:{path.stat().st_mtime_ns if path and path.is_file() else 'builtin'}"
    existing = db.scalar(
        select(ModelVersion)
        .where(ModelVersion.weights_path == weights_path, ModelVersion.version == version)
        .limit(1)
    )
    if existing is not None:
        return existing.id
    model_version = ModelVersion(
        model_name=f"water-{config.backend}",
        model_type="detection" if config.backend in ("yolo", "noop") else config.backend,
        weights_path=weights_path,
        version=version,
        confidence_threshold=config.confidence,
        iou_threshold=config.iou,
        device=config.device,
        image_size=config.image_size,
        is_active=True,
    )
    db.add(model_version)
    db.commit()
    db.refresh(model_version)
    return model_version.id


def ingest_detection_records(
    db: Session,
    camera_id: int,
    records: list[DetectionRecord],
    *,
    model_version_id: int | None = None,
    frame_index: int | None = None,
    event_time: datetime | None = None,
    alarm_config: AlarmConfig | None = None,
) -> tuple[list[int], list[int]]:
    """Persist one frame and apply temporal alarm confirmation.

    Every detection box is retained as an event. Alarm state is updated once
    per label and frame, so multiple boxes of the same class do not
    accidentally count as multiple consecutive frames. ``frame_index`` is
    used to decide whether two observations are consecutive; when it is not
    supplied (for example by a simple API client), observations are treated
    as consecutive.
    """
    policy = alarm_config or AlarmConfig()
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise ValueError(f"Camera {camera_id} does not exist")
    if not records:
        return [], []
    detected_at = event_time or utcnow()
    event_ids: list[int] = []
    alarm_ids: set[int] = set()
    grouped: dict[str, list[DetectionRecord]] = {}
    for record in records:
        x1, y1, x2, y2 = record.bbox
        event = DetectionEvent(
            camera_id=camera_id,
            model_version_id=model_version_id,
            frame_index=frame_index,
            event_time=detected_at,
            label=record.label,
            confidence=record.confidence,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            source_branch=record.source_branch,
            area_pixels=record.area_pixels,
            metadata_json=record.metadata,
        )
        db.add(event)
        db.flush()
        event_ids.append(event.id)
        grouped.setdefault(normalize_label(record.label), []).append(record)

    open_alarms = list(
        db.scalars(
            select(Alarm)
            .where(Alarm.camera_id == camera_id, Alarm.status.in_(("candidate", "active", "acknowledged")))
            .order_by(Alarm.id.desc())
        ).all()
    )
    for normalized, label_records in grouped.items():
        representative = max(label_records, key=lambda item: item.confidence)
        alarm = next((item for item in open_alarms if normalize_label(item.alarm_type) == normalized), None)
        required = required_confirmations(representative.label, policy)
        if alarm is None:
            alarm = Alarm(
                camera_id=camera_id,
                alarm_type=representative.label,
                severity=alarm_severity(representative.label),
                status="active" if required == 1 else "candidate",
                confidence=representative.confidence,
                first_detected_at=detected_at,
                last_detected_at=detected_at,
                frame_count=1,
                consecutive_count=1,
                required_confirmations=required,
                last_frame_index=frame_index,
                area_pixels=representative.area_pixels,
                message=f"Detected {representative.label} at {camera.camera_name}",
            )
            db.add(alarm)
            db.flush()
            open_alarms.append(alarm)
        else:
            if frame_index is None or alarm.last_frame_index is None:
                is_consecutive = True
            else:
                is_consecutive = frame_index == alarm.last_frame_index + 1
            alarm.consecutive_count = alarm.consecutive_count + 1 if is_consecutive else 1
            alarm.last_frame_index = frame_index
            alarm.last_detected_at = detected_at
            alarm.confidence = max(alarm.confidence, representative.confidence)
            alarm.frame_count += 1
            alarm.required_confirmations = required
            if representative.area_pixels is not None:
                alarm.area_pixels = representative.area_pixels
            if alarm.status == "candidate" and alarm.consecutive_count >= required:
                alarm.status = "active"
            elif alarm.status == "acknowledged":
                alarm.status = "active"
        alarm_ids.add(alarm.id)
    db.commit()
    return event_ids, sorted(alarm_ids)


class DetectionPersistence:
    """Workflow-owned database writer; one session per running workflow."""

    def __init__(self, camera_id: int, model_config: ModelConfig, session_factory, alarm_config: AlarmConfig | None = None) -> None:
        self.camera_id = camera_id
        self.alarm_config = alarm_config or AlarmConfig()
        self.session = session_factory()
        self.model_version_id = register_model_version(self.session, model_config)

    def write(self, frame_index: int, video_timestamp_seconds: float, detections: list[Detection]) -> tuple[list[int], list[int]]:
        records = [
            DetectionRecord(
                label=d.label,
                confidence=d.confidence,
                bbox=tuple(float(value) for value in d.xyxy),
                metadata={"video_timestamp_seconds": video_timestamp_seconds},
            )
            for d in detections
        ]
        return ingest_detection_records(
            self.session,
            self.camera_id,
            records,
            model_version_id=self.model_version_id,
            frame_index=frame_index,
            alarm_config=self.alarm_config,
        )

    def close(self) -> None:
        self.session.close()
