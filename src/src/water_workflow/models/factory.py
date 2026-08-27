from __future__ import annotations

from ..config import ModelConfig
from .base import DetectionModel, SegmentationModel
from .noop import NoOpModel


def create_model(config: ModelConfig) -> DetectionModel:
    if config.backend == "noop":
        return NoOpModel()
    if config.backend == "yolo":
        from .yolo import UltralyticsYOLOModel

        return UltralyticsYOLOModel(config.weights, config.confidence, config.iou, config.device, config.image_size)
    raise ValueError(f"Unsupported model backend: {config.backend}")


def create_segmentation_model(config: ModelConfig) -> SegmentationModel:
    if config.backend == "noop":
        from .noop import NoOpSegmentationModel

        return NoOpSegmentationModel()
    if config.backend in {"yolo", "yolo-seg"}:
        from .yolo_seg import UltralyticsYOLOSegmentationModel

        return UltralyticsYOLOSegmentationModel(
            config.weights,
            config.confidence,
            config.iou,
            config.device,
            config.image_size,
        )
    raise ValueError(f"Unsupported segmentation backend: {config.backend}")
