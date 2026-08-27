from __future__ import annotations

from pathlib import Path

import numpy as np
from ultralytics import YOLO

from .base import Detection


class UltralyticsYOLOModel:
    def __init__(self, weights: str, confidence: float, iou: float, device: str, image_size: int) -> None:
        if not weights:
            raise ValueError("model.weights is required when model.backend is 'yolo'")
        if not Path(weights).is_file():
            raise FileNotFoundError(f"YOLO weights do not exist: {weights}")
        self.model = YOLO(weights)
        self.confidence = confidence
        self.iou = iou
        self.device = device
        self.image_size = image_size

    def predict(self, frame: np.ndarray) -> list[Detection]:
        result = self.model.predict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            imgsz=self.image_size,
            device=self.device,
            verbose=False,
        )[0]
        names = result.names
        detections: list[Detection] = []
        if result.boxes is None:
            return detections
        for box, confidence, class_id in zip(result.boxes.xyxy, result.boxes.conf, result.boxes.cls):
            coords = tuple(int(value) for value in box.tolist())
            detections.append(Detection(names[int(class_id)], float(confidence), coords))
        return detections

    def close(self) -> None:
        return None
