from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import cv2
import numpy as np

from ..config import BranchesConfig, RiskRegionConfig
from ..models.base import DetectionModel, SegmentationModel
from ..video.types import FramePacket
from .types import DetectionEvidence, FrameProcessingResult, SegmentationEvidence
from .regions import RiskRegionAnalyzer


class SharedDetectionRunner:
    def __init__(self, model: DetectionModel, model_version: str = "unregistered") -> None:
        self.model = model
        self.model_version = model_version
        self._lock = threading.Lock()

    def predict(self, frame: np.ndarray):
        with self._lock:
            return self.model.predict(frame)

    def close(self) -> None:
        self.model.close()


class SharedSegmentationRunner:
    def __init__(self, model: SegmentationModel, model_version: str = "unregistered") -> None:
        self.model = model
        self.model_version = model_version
        self._lock = threading.Lock()

    def predict(self, frame: np.ndarray):
        with self._lock:
            return self.model.predict(frame)

    def close(self) -> None:
        self.model.close()


class Mog2MotionCandidates:
    def __init__(self, branches: BranchesConfig) -> None:
        config = branches.motion_crop_detection
        self.config = config
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=config.history,
            varThreshold=config.variance_threshold,
            detectShadows=False,
        )

    def find(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        mask = self.subtractor.apply(frame)
        kernel = np.ones((3, 3), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.dilate(mask, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        height, width = frame.shape[:2]
        candidates: list[tuple[int, tuple[int, int, int, int]]] = []
        for contour in contours:
            area = int(cv2.contourArea(contour))
            if area < self.config.min_area_pixels:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            pad_x = int(w * self.config.padding_ratio)
            pad_y = int(h * self.config.padding_ratio)
            candidates.append(
                (
                    area,
                    (
                        max(0, x - pad_x),
                        max(0, y - pad_y),
                        min(width, x + w + pad_x),
                        min(height, y + h + pad_y),
                    ),
                )
            )
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [bbox for _, bbox in candidates[: self.config.max_crops_per_frame]]


class BranchScheduler:
    def __init__(
        self,
        camera_id: str,
        config: BranchesConfig,
        detector: SharedDetectionRunner,
        *,
        segmenter: SharedSegmentationRunner | None = None,
        risk_regions: list[RiskRegionConfig] | None = None,
        config_revision: str = "unversioned",
        draw_annotations: bool = True,
    ) -> None:
        self.camera_id = camera_id
        self.config = config
        self.detector = detector
        self.segmenter = segmenter
        self.config_revision = config_revision
        self.draw_annotations = draw_annotations
        self.regions = RiskRegionAnalyzer(risk_regions or [])
        self.motion = Mog2MotionCandidates(config) if config.motion_crop_detection.enabled else None
        self._last_run_ms: dict[str, float] = {}

    def _due(self, branch: str, timestamp_ms: float, interval_ms: int) -> bool:
        previous = self._last_run_ms.get(branch)
        if previous is not None and timestamp_ms - previous < interval_ms:
            return False
        self._last_run_ms[branch] = timestamp_ms
        return True

    @staticmethod
    def _captured_at(packet: FramePacket) -> datetime:
        return packet.captured_at or datetime.now(timezone.utc)

    def _detect(
        self,
        packet: FramePacket,
        frame: np.ndarray,
        source_branch: str,
        offset: tuple[int, int] = (0, 0),
    ) -> list[DetectionEvidence]:
        offset_x, offset_y = offset
        evidence = []
        for item in self.detector.predict(frame):
            bbox = (item.xyxy[0] + offset_x, item.xyxy[1] + offset_y, item.xyxy[2] + offset_x, item.xyxy[3] + offset_y)
            region_ids = self.regions.regions_for_bbox(bbox, packet.frame.shape) or (None,)
            evidence.extend(DetectionEvidence(
                camera_id=self.camera_id,
                frame_index=packet.frame_index,
                captured_at=self._captured_at(packet),
                label=item.label,
                confidence=item.confidence,
                bbox=bbox,
                source_branch=source_branch,
                model_version=self.detector.model_version,
                config_revision=self.config_revision,
                risk_region_id=region_id,
            )
                for region_id in region_ids
            )
        return evidence

    def process(self, packet: FramePacket) -> FrameProcessingResult:
        timestamp_ms = packet.timestamp_seconds * 1000.0
        result = FrameProcessingResult(frame=packet)
        full = self.config.full_frame_detection
        if full.enabled and self._due("full_frame_detection", timestamp_ms, full.interval_ms):
            started = time.perf_counter()
            result.detections.extend(self._detect(packet, packet.frame, "full_frame"))
            result.branch_latencies_ms["full_frame_detection"] = (time.perf_counter() - started) * 1000

        motion_config = self.config.motion_crop_detection
        if self.motion is not None and self._due("motion_crop_detection", timestamp_ms, motion_config.interval_ms):
            started = time.perf_counter()
            for x1, y1, x2, y2 in self.motion.find(packet.frame):
                crop = packet.frame[y1:y2, x1:x2]
                if crop.size:
                    result.detections.extend(self._detect(packet, crop, "motion_crop", (x1, y1)))
            result.branch_latencies_ms["motion_crop_detection"] = (time.perf_counter() - started) * 1000

        segment_config = self.config.water_surface_segmentation
        has_required_roi = not segment_config.roi_required or self.regions.configured
        if segment_config.enabled and self.segmenter is not None and has_required_roi and self._due(
            "water_surface_segmentation", timestamp_ms, segment_config.interval_ms
        ):
            started = time.perf_counter()
            for segment in self.segmenter.predict(packet.frame):
                area = int(cv2.contourArea(np.asarray(segment.polygon, dtype=np.float32)))
                overlaps = self.regions.segment_overlaps(
                    segment.polygon,
                    packet.frame.shape,
                    min_intersection_area_pixels=segment_config.min_intersection_area_pixels,
                    min_area_ratio_in_risk_region=segment_config.min_area_ratio_in_risk_region,
                )
                if not self.regions.configured:
                    overlaps = (None,)
                for overlap in overlaps:
                    result.segments.append(SegmentationEvidence(
                        camera_id=self.camera_id,
                        frame_index=packet.frame_index,
                        captured_at=self._captured_at(packet),
                        class_name=segment.label,
                        confidence=segment.confidence,
                        polygon=segment.polygon,
                        bbox=segment.xyxy,
                        mask_area_pixels=area if overlap is None else overlap.intersection_area_pixels,
                        area_ratio_in_risk_region=None if overlap is None else overlap.area_ratio_in_risk_region,
                        risk_region_id=None if overlap is None else overlap.region_id,
                        model_version=self.segmenter.model_version,
                        config_revision=self.config_revision,
                    ))
            result.branch_latencies_ms["water_surface_segmentation"] = (time.perf_counter() - started) * 1000

        if self.draw_annotations:
            annotated = packet.frame.copy()
            for detection in result.detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated, f"{detection.label} {detection.confidence:.2f}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            for segment in result.segments:
                cv2.polylines(annotated, [np.asarray(segment.polygon, dtype=np.int32)], True, (255, 255, 0), 2)
            result.annotated_frame = annotated
        return result
