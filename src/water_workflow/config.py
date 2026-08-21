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
class ModelConfig:
    backend: str = "noop"
    weights: str = ""
    confidence: float = 0.25
    iou: float = 0.45
    device: str = "0"
    image_size: int = 640


@dataclass
class DisplayConfig:
    enabled: bool = True
    window_name: str = "Water Workflow"
    draw_boxes: bool = True


@dataclass
class AppConfig:
    video: VideoConfig = field(default_factory=VideoConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)


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


def load_config(path: str | Path) -> AppConfig:
    config = AppConfig()
    config_path = Path(path)
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("Configuration root must be a mapping")
        _merge_dataclass(config, raw)
    return config
