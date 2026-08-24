from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import load_config
from ..database import Alarm, Camera, DetectionEvent, ModelVersion, get_db
from ..database.models import utcnow
from ..database.init_db import init_database
from .schemas import (
    AlarmPage,
    AlarmRead,
    CameraCreate,
    CameraRead,
    CameraStatusRead,
    CameraUpdate,
    DetectionEventCreate,
    DetectionEventPage,
    DetectionEventResponse,
    ModelVersionRead,
)
from .services import ingest_detection_event

app = FastAPI(title="Water Leak Workflow API", version="0.1.0")
_config_path = os.environ.get("WATER_WORKFLOW_CONFIG", "configs/default.yaml")
API_ALARM_CONFIG = load_config(_config_path).alarm


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"status": "degraded", "database": str(exc)}) from exc


@app.post("/api/v1/cameras", response_model=CameraRead, status_code=201)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)) -> Camera:
    if db.scalar(select(Camera).where(Camera.camera_code == payload.camera_code)) is not None:
        raise HTTPException(status_code=409, detail="camera_code already exists")
    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@app.get("/api/v1/cameras", response_model=list[CameraRead])
def list_cameras(db: Session = Depends(get_db)) -> list[Camera]:
    return list(db.scalars(select(Camera).order_by(Camera.id)).all())


@app.get("/api/v1/cameras/{camera_id}/status", response_model=CameraStatusRead)
def get_camera_status(camera_id: int, db: Session = Depends(get_db)) -> CameraStatusRead:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="camera not found")
    active_alarm_count = db.scalar(
        select(func.count()).select_from(Alarm).where(
            Alarm.camera_id == camera_id,
            Alarm.status.in_(("active", "acknowledged")),
        )
    ) or 0
    latest_event_time = db.scalar(
        select(DetectionEvent.event_time)
        .where(DetectionEvent.camera_id == camera_id)
        .order_by(DetectionEvent.event_time.desc())
        .limit(1)
    )
    return CameraStatusRead(
        camera=camera,
        active_alarm_count=active_alarm_count,
        latest_event_time=latest_event_time,
    )


@app.get("/api/v1/cameras/{camera_id}", response_model=CameraRead)
def get_camera(camera_id: int, db: Session = Depends(get_db)) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="camera not found")
    return camera


@app.patch("/api/v1/cameras/{camera_id}", response_model=CameraRead)
def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="camera not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, key, value)
    db.commit()
    db.refresh(camera)
    return camera


@app.get("/api/v1/alarms", response_model=AlarmPage)
def list_alarms(status: str | None = None, camera_id: int | None = None, alarm_type: str | None = None, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> AlarmPage:
    filters = []
    if status:
        filters.append(Alarm.status == status)
    if camera_id is not None:
        filters.append(Alarm.camera_id == camera_id)
    if alarm_type:
        filters.append(Alarm.alarm_type == alarm_type)
    query = select(Alarm).where(*filters).order_by(Alarm.last_detected_at.desc()).offset((page - 1) * page_size).limit(page_size)
    total = db.scalar(select(func.count()).select_from(Alarm).where(*filters)) or 0
    return AlarmPage(items=list(db.scalars(query).all()), page=page, page_size=page_size, total=total)


@app.get("/api/v1/detection-events", response_model=DetectionEventPage)
def list_detection_events(
    camera_id: int | None = None,
    label: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> DetectionEventPage:
    filters = []
    if camera_id is not None:
        filters.append(DetectionEvent.camera_id == camera_id)
    if label:
        filters.append(DetectionEvent.label == label)
    query = (
        select(DetectionEvent)
        .where(*filters)
        .order_by(DetectionEvent.event_time.desc(), DetectionEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    total = db.scalar(select(func.count()).select_from(DetectionEvent).where(*filters)) or 0
    return DetectionEventPage(
        items=list(db.scalars(query).all()),
        page=page,
        page_size=page_size,
        total=total,
    )


@app.get("/api/v1/model-versions", response_model=list[ModelVersionRead])
def list_model_versions(db: Session = Depends(get_db)) -> list[ModelVersion]:
    return list(db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())).all())


@app.get("/api/v1/alarms/{alarm_id}", response_model=AlarmRead)
def get_alarm(alarm_id: int, db: Session = Depends(get_db)) -> Alarm:
    alarm = db.get(Alarm, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="alarm not found")
    return alarm


def _change_alarm_status(alarm_id: int, status: str, db: Session) -> Alarm:
    alarm = db.get(Alarm, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="alarm not found")
    if status == "acknowledged" and alarm.status == "resolved":
        raise HTTPException(status_code=409, detail="resolved alarm cannot be acknowledged")
    if status == "resolved" and alarm.status == "resolved":
        raise HTTPException(status_code=409, detail="alarm is already resolved")
    now = utcnow()
    if status == "acknowledged":
        alarm.status = status
        alarm.acknowledged_at = now
    else:
        alarm.status = "resolved"
        alarm.resolved_at = now
    db.commit()
    db.refresh(alarm)
    return alarm


@app.post("/api/v1/alarms/{alarm_id}/acknowledge", response_model=AlarmRead)
def acknowledge_alarm(alarm_id: int, db: Session = Depends(get_db)) -> Alarm:
    return _change_alarm_status(alarm_id, "acknowledged", db)


@app.post("/api/v1/alarms/{alarm_id}/resolve", response_model=AlarmRead)
def resolve_alarm(alarm_id: int, db: Session = Depends(get_db)) -> Alarm:
    return _change_alarm_status(alarm_id, "resolved", db)


@app.post("/api/v1/internal/detection-events", response_model=DetectionEventResponse, status_code=201)
def create_detection_event(payload: DetectionEventCreate, db: Session = Depends(get_db)) -> DetectionEventResponse:
    event_ids, alarm_ids = ingest_detection_event(db, payload, API_ALARM_CONFIG)
    return DetectionEventResponse(event_ids=event_ids, alarm_ids=alarm_ids)


def main() -> None:
    import uvicorn
    uvicorn.run("water_workflow.api.app:app", host="127.0.0.1", port=8000, reload=False)
