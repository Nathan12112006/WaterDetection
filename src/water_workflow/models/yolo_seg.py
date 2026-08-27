from __future__ import annotations

from pathlib import Path

import numpy as np
from ultralytics import YOLO

from .base import Segmentation


class UltralyticsYOLOSegmentationModel:
    def __init__(self, weights: str, confidence: float, iou: float, device: str, image_size: int) -> None:
        if not weights:
            raise ValueError("model.weights is required for YOLO segmentation")
        if not Path(weights).is_file():
            raise FileNotFoundError(f"YOLO segmentation weights do not exist: {weights}")
        self.model = YOLO(weights)
        self.confidence = confidence
        self.iou = iou
        self.device = device
        self.image_size = image_size

    def predict(self, frame: np.ndarray) -> list[Segmentation]:
        result = self.model.predict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            imgsz=self.image_size,
            device=self.device,
            verbose=False,
        )[0]
        if result.masks is None or result.boxes is None:
            return []
        segments: list[Segmentation] = []
        for polygon, box, confidence, class_id in zip(
            result.masks.xy,
            result.boxes.xyxy,
            result.boxes.conf,
            result.boxes.cls,
        ):
            points = tuple((int(x), int(y)) for x, y in polygon.tolist())
            if len(points) < 3:
                continue
            segments.append(
                Segmentation(
                    label=result.names[int(class_id)],
                    confidence=float(confidence),
                    polygon=points,
                    xyxy=tuple(int(value) for value in box.tolist()),
                )
            )
        return segments

    def close(self) -> None:
        return None
