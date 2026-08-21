from __future__ import annotations

from ..config import ModelConfig
from .base import DetectionModel
from .noop import NoOpModel


def create_model(config: ModelConfig) -> DetectionModel:
    if config.backend == "noop":
        return NoOpModel()
    if config.backend == "yolo":
        from .yolo import UltralyticsYOLOModel

        return UltralyticsYOLOModel(config.weights, config.confidence, config.iou, config.device, config.image_size)
    raise ValueError(f"Unsupported model backend: {config.backend}")
