from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..config import RiskRegionConfig


@dataclass(frozen=True)
class SegmentRegionOverlap:
    region_id: str
    intersection_area_pixels: int
    area_ratio_in_risk_region: float


class RiskRegionAnalyzer:
    """Resolve evidence against configured risk polygons and exclusion zones."""

    def __init__(self, regions: list[RiskRegionConfig]) -> None:
        self._regions = tuple(regions)
        self._mask_cache: dict[tuple[int, int], tuple[tuple[RiskRegionConfig, np.ndarray, int], ...]] = {}

    @property
    def configured(self) -> bool:
        return bool(self._regions)

    @staticmethod
    def _points(region: RiskRegionConfig, polygon: list[list[float]], width: int, height: int) -> np.ndarray:
        points = np.asarray(polygon, dtype=np.float64)
        if region.coordinate_space == "normalized":
            points = points * np.asarray([max(0, width - 1), max(0, height - 1)])
        points[:, 0] = np.clip(points[:, 0], 0, max(0, width - 1))
        points[:, 1] = np.clip(points[:, 1], 0, max(0, height - 1))
        return np.rint(points).astype(np.int32)

    def _masks(self, shape: tuple[int, ...]) -> tuple[tuple[RiskRegionConfig, np.ndarray, int], ...]:
        height, width = shape[:2]
        key = (height, width)
        cached = self._mask_cache.get(key)
        if cached is not None:
            return cached
        built = []
        for region in self._regions:
            mask = np.zeros((height, width), dtype=np.uint8)
            cv2.fillPoly(mask, [self._points(region, region.polygon, width, height)], 1)
            for excluded in region.exclude_polygons:
                cv2.fillPoly(mask, [self._points(region, excluded, width, height)], 0)
            built.append((region, mask, int(np.count_nonzero(mask))))
        result = tuple(built)
        self._mask_cache[key] = result
        return result

    def regions_for_bbox(self, bbox: tuple[int, int, int, int], frame_shape: tuple[int, ...]) -> tuple[str, ...]:
        x1, y1, x2, y2 = bbox
        center_x = min(max((x1 + x2) // 2, 0), frame_shape[1] - 1)
        center_y = min(max((y1 + y2) // 2, 0), frame_shape[0] - 1)
        return tuple(region.region_id for region, mask, _ in self._masks(frame_shape) if mask[center_y, center_x])

    def segment_overlaps(
        self,
        polygon: tuple[tuple[int, int], ...],
        frame_shape: tuple[int, ...],
        *,
        min_intersection_area_pixels: int = 1,
        min_area_ratio_in_risk_region: float = 0.0,
    ) -> tuple[SegmentRegionOverlap, ...]:
        segment_mask = np.zeros(frame_shape[:2], dtype=np.uint8)
        cv2.fillPoly(segment_mask, [np.asarray(polygon, dtype=np.int32)], 1)
        overlaps = []
        for region, region_mask, region_area in self._masks(frame_shape):
            if region_area == 0:
                continue
            intersection = int(np.count_nonzero(segment_mask & region_mask))
            ratio = intersection / region_area
            if intersection >= min_intersection_area_pixels and ratio >= min_area_ratio_in_risk_region:
                overlaps.append(SegmentRegionOverlap(region.region_id, intersection, ratio))
        return tuple(overlaps)
