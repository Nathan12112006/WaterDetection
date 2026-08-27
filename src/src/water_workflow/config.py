from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class VideoConfig:
    source: str = "camera"
    camera_index: int = 0
    file_path: str = ""
    width: int | None = None
    height: int | None = None
    fps_limit: float | None = None
    loop_file: bool = False


@dataclass
class SourceConfig:
    type: str = "camera"
    camera_index: int = 0
    uri: str = ""
    path: str = ""
    width: int | None = None
    height: int | None = None
    fps_limit: float | None = None
    loop: bool = False
    reconnect: bool = True
    reconnect_delay_seconds: float = 1.0
    max_reconnect_attempts: int = 0


@dataclass
class RiskRegionConfig:
    region_id: str = ""
    coordinate_space: str = "normalized"
    polygon: list[list[float]] = field(default_factory=list)
    exclude_polygons: list[list[list[float]]] = field(default_factory=list)


@dataclass
class CameraMonitoringConfig:
    camera_id: str = ""
    name: str = ""
    enabled: bool = True
    source: SourceConfig = field(default_factory=SourceConfig)
    risk_regions: list[RiskRegionConfig] = field(default_factory=list)


@dataclass
class ScheduledBranchConfig:
    enabled: bool = True
    interval_ms: int = 1000


@dataclass
class MotionCropBranchConfig(ScheduledBranchConfig):
    interval_ms: int = 200
    max_crops_per_frame: int = 2
    padding_ratio: float = 0.2
    min_area_pixels: int = 64
    history: int = 120
    variance_threshold: float = 16.0


@dataclass
class SegmentationBranchConfig(ScheduledBranchConfig):
    interval_ms: int = 2000
    roi_required: bool = True
    min_intersection_area_pixels: int = 16
    min_area_ratio_in_risk_region: float = 0.0


@dataclass
class BranchesConfig:
    full_frame_detection: ScheduledBranchConfig = field(default_factory=ScheduledBranchConfig)
    motion_crop_detection: MotionCropBranchConfig = field(
        default_factory=lambda: MotionCropBranchConfig(enabled=False)
    )
    water_surface_segmentation: SegmentationBranchConfig = field(
        default_factory=lambda: SegmentationBranchConfig(enabled=False)
    )


@dataclass
class MonitoringRuntimeConfig:
    queue_size: int = 2
    max_frame_age_ms: int = 1000
    warmup_timeout_seconds: float = 30.0
    inference_timeout_ms: int = 1000


@dataclass
class EventRuleConfig:
    confirm_hits: int = 3
    confirm_window_seconds: float = 5.0
    recovery_quiet_seconds: float = 10.0
    min_confidence: float = 0.25
    update_interval_seconds: float = 1.0


@dataclass
class EventRulesConfig:
    water_drop: EventRuleConfig = field(default_factory=lambda: EventRuleConfig(confirm_hits=2, confirm_window_seconds=2.0))
    pipe_burst: EventRuleConfig = field(default_factory=lambda: EventRuleConfig(confirm_hits=2, confirm_window_seconds=2.0))
    water_accumulation: EventRuleConfig = field(default_factory=lambda: EventRuleConfig(confirm_hits=3, confirm_window_seconds=10.0))
    default: EventRuleConfig = field(default_factory=EventRuleConfig)


@dataclass
class MonitoringConfig:
    enabled: bool = False
    cameras: list[CameraMonitoringConfig] = field(default_factory=list)
    runtime: MonitoringRuntimeConfig = field(default_factory=MonitoringRuntimeConfig)
    branches: BranchesConfig = field(default_factory=BranchesConfig)
    events: EventRulesConfig = field(default_factory=EventRulesConfig)


@dataclass
class ModelConfig:
    backend: str = "noop"
    weights: str = ""
    confidence: float = 0.25
    iou: float = 0.45
    device: str = "0"
    image_size: int = 640


@dataclass
class ModelsConfig:
    detector: ModelConfig = field(default_factory=ModelConfig)
    water_surface_seg: ModelConfig = field(default_factory=ModelConfig)


@dataclass
class DisplayConfig:
    enabled: bool = True
    window_name: str = "Water Workflow"
    draw_boxes: bool = True


@dataclass
class DatabaseConfig:
    enabled: bool = False
    camera_id: int | None = None
    write_detection_events: bool = True


@dataclass
class AlarmConfig:
    """Temporal confirmation policy for database alarms.

    Water drops are intentionally immediate because a drop can be brief and
    may disappear between sampled frames.  More persistent-looking classes
    use consecutive-frame confirmation to reduce one-frame false positives.
    """

    confirmation_frames: int = 3
    water_drop_labels: list[str] = field(default_factory=lambda: ["water drop", "water_drop", "滴水", "水滴"])


@dataclass
class AppConfig:
    video: VideoConfig = field(default_factory=VideoConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    alarm: AlarmConfig = field(default_factory=AlarmConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    models: ModelsConfig = field(default_factory=ModelsConfig)


def _merge_dataclass(instance: Any, values: dict[str, Any]) -> Any:
    for key, value in values.items():
        if not hasattr(instance, key):
            raise ValueError(f"Unknown configuration key: {key}")
        current = getattr(instance, key)
        if hasattr(current, "__dataclass_fields__") and isinstance(value, dict):
            _merge_dataclass(current, value)
        else:
            setattr(instance, key, value)
    return instance


def _parse_source(values: dict[str, Any]) -> SourceConfig:
    source = SourceConfig()
    aliases = {"file_path": "path", "rtsp_url": "uri", "loop_file": "loop"}
    normalized = {aliases.get(key, key): value for key, value in values.items()}
    _merge_dataclass(source, normalized)
    if source.type not in {"camera", "rtsp", "file"}:
        raise ValueError(f"Unsupported monitoring source type: {source.type}")
    if source.type == "file" and not source.path:
        raise ValueError("monitoring file source requires source.path")
    if source.type == "rtsp" and not source.uri:
        raise ValueError("monitoring RTSP source requires source.uri")
    if source.fps_limit is not None and source.fps_limit <= 0:
        raise ValueError("source.fps_limit must be greater than zero")
    if source.reconnect_delay_seconds < 0:
        raise ValueError("source.reconnect_delay_seconds cannot be negative")
    if source.max_reconnect_attempts < 0:
        raise ValueError("source.max_reconnect_attempts cannot be negative")
    return source


def _parse_risk_region(values: dict[str, Any]) -> RiskRegionConfig:
    region = RiskRegionConfig()
    _merge_dataclass(region, values)
    if not region.region_id:
        raise ValueError("risk region requires region_id")
    if len(region.polygon) < 3:
        raise ValueError(f"risk region {region.region_id} requires at least three polygon points")
    if region.coordinate_space not in {"normalized", "pixels"}:
        raise ValueError(
            f"risk region {region.region_id} coordinate_space must be normalized or pixels"
        )
    polygons = [region.polygon, *region.exclude_polygons]
    if any(len(polygon) < 3 for polygon in polygons):
        raise ValueError(f"risk region {region.region_id} polygons require at least three points")
    if region.coordinate_space == "normalized":
        for polygon in polygons:
            for point in polygon:
                if len(point) != 2 or any(not 0 <= float(value) <= 1 for value in point):
                    raise ValueError(
                        f"risk region {region.region_id} normalized points must be [x, y] values between 0 and 1"
                    )
    return region


def _parse_monitoring_cameras(values: list[dict[str, Any]]) -> list[CameraMonitoringConfig]:
    cameras: list[CameraMonitoringConfig] = []
    seen: set[str] = set()
    for raw in values:
        if not isinstance(raw, dict):
            raise ValueError("monitoring.cameras entries must be mappings")
        camera = CameraMonitoringConfig()
        scalar_values = {key: value for key, value in raw.items() if key not in {"source", "risk_regions"}}
        _merge_dataclass(camera, scalar_values)
        camera.source = _parse_source(raw.get("source", {}))
        camera.risk_regions = [_parse_risk_region(item) for item in raw.get("risk_regions", [])]
        if not camera.camera_id:
            raise ValueError("monitoring camera requires camera_id")
        if camera.camera_id in seen:
            raise ValueError(f"Duplicate monitoring camera_id: {camera.camera_id}")
        seen.add(camera.camera_id)
        cameras.append(camera)
    return cameras


def _validate_monitoring(config: MonitoringConfig) -> None:
    if config.runtime.queue_size < 1:
        raise ValueError("monitoring.runtime.queue_size must be at least 1")
    if config.runtime.max_frame_age_ms < 1:
        raise ValueError("monitoring.runtime.max_frame_age_ms must be at least 1")
    if config.runtime.warmup_timeout_seconds <= 0:
        raise ValueError("monitoring.runtime.warmup_timeout_seconds must be greater than zero")
    branches = config.branches
    for name, branch in (
        ("full_frame_detection", branches.full_frame_detection),
        ("motion_crop_detection", branches.motion_crop_detection),
        ("water_surface_segmentation", branches.water_surface_segmentation),
    ):
        if branch.interval_ms < 1:
            raise ValueError(f"monitoring.branches.{name}.interval_ms must be at least 1")
    if branches.motion_crop_detection.max_crops_per_frame < 1:
        raise ValueError("motion_crop_detection.max_crops_per_frame must be at least 1")
    segmentation = branches.water_surface_segmentation
    if segmentation.min_intersection_area_pixels < 1:
        raise ValueError("water_surface_segmentation.min_intersection_area_pixels must be at least 1")
    if not 0 <= segmentation.min_area_ratio_in_risk_region <= 1:
        raise ValueError("water_surface_segmentation.min_area_ratio_in_risk_region must be between 0 and 1")
    for name, rule in (
        ("water_drop", config.events.water_drop),
        ("pipe_burst", config.events.pipe_burst),
        ("water_accumulation", config.events.water_accumulation),
        ("default", config.events.default),
    ):
        if rule.confirm_hits < 1:
            raise ValueError(f"monitoring.events.{name}.confirm_hits must be at least 1")
        if rule.confirm_window_seconds <= 0 or rule.recovery_quiet_seconds <= 0:
            raise ValueError(f"monitoring.events.{name} durations must be greater than zero")
        if not 0 <= rule.min_confidence <= 1:
            raise ValueError(f"monitoring.events.{name}.min_confidence must be between 0 and 1")
        if rule.update_interval_seconds < 0:
            raise ValueError(f"monitoring.events.{name}.update_interval_seconds cannot be negative")


def effective_monitoring_cameras(config: AppConfig) -> list[CameraMonitoringConfig]:
    """Return explicit monitoring cameras or one camera derived from legacy video config."""
    if config.monitoring.cameras:
        return [camera for camera in config.monitoring.cameras if camera.enabled]
    source_type = config.video.source
    source = SourceConfig(
        type=source_type,
        camera_index=config.video.camera_index,
        path=config.video.file_path,
        width=config.video.width,
        height=config.video.height,
        fps_limit=config.video.fps_limit,
        loop=config.video.loop_file,
    )
    camera_id = f"camera-{source.camera_index}" if source_type == "camera" else "local-file"
    return [CameraMonitoringConfig(camera_id=camera_id, name=camera_id, source=source)]


def load_config(path: str | Path) -> AppConfig:
    config = AppConfig()
    config_path = Path(path).resolve()
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("Configuration root must be a mapping")
        monitoring_values = raw.get("monitoring") or {}
        values_without_cameras = dict(raw)
        if isinstance(monitoring_values, dict):
            values_without_cameras["monitoring"] = {
                key: value for key, value in monitoring_values.items() if key != "cameras"
            }
        _merge_dataclass(config, values_without_cameras)
        if isinstance(monitoring_values, dict):
            config.monitoring.cameras = _parse_monitoring_cameras(monitoring_values.get("cameras", []))
        if "models" not in raw and "model" in raw:
            config.models.detector = ModelConfig(
                backend=config.model.backend,
                weights=config.model.weights,
                confidence=config.model.confidence,
                iou=config.model.iou,
                device=config.model.device,
                image_size=config.model.image_size,
            )
    if config.video.file_path and not Path(config.video.file_path).is_absolute():
        config.video.file_path = str((config_path.parent / config.video.file_path).resolve())
    if config.model.weights and not Path(config.model.weights).is_absolute():
        config.model.weights = str((config_path.parent / config.model.weights).resolve())
    for model in (config.models.detector, config.models.water_surface_seg):
        if model.weights and not Path(model.weights).is_absolute():
            model.weights = str((config_path.parent / model.weights).resolve())
    for camera in config.monitoring.cameras:
        if camera.source.type == "file" and camera.source.path and not Path(camera.source.path).is_absolute():
            camera.source.path = str((config_path.parent / camera.source.path).resolve())
    _validate_monitoring(config.monitoring)
    return config
