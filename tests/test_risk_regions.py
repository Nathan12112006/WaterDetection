from __future__ import annotations

import unittest

import numpy as np

from water_workflow.config import RiskRegionConfig
from water_workflow.monitoring.regions import RiskRegionAnalyzer


class RiskRegionAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = RiskRegionAnalyzer([
            RiskRegionConfig(
                region_id="floor",
                coordinate_space="pixels",
                polygon=[[0, 0], [9, 0], [9, 9], [0, 9]],
                exclude_polygons=[[[0, 0], [3, 0], [3, 3], [0, 3]]],
            )
        ])
        self.shape = np.zeros((10, 10, 3), dtype=np.uint8).shape

    def test_bbox_center_is_assigned_but_exclusion_zone_is_not(self) -> None:
        self.assertEqual(self.analyzer.regions_for_bbox((6, 6, 8, 8), self.shape), ("floor",))
        self.assertEqual(self.analyzer.regions_for_bbox((0, 0, 2, 2), self.shape), ())

    def test_segment_overlap_excludes_normal_water_area(self) -> None:
        overlap = self.analyzer.segment_overlaps(((0, 0), (9, 0), (9, 9), (0, 9)), self.shape)[0]
        self.assertEqual(overlap.region_id, "floor")
        self.assertEqual(overlap.intersection_area_pixels, 84)
        self.assertAlmostEqual(overlap.area_ratio_in_risk_region, 1.0)

    def test_overlap_threshold_filters_small_segment(self) -> None:
        overlaps = self.analyzer.segment_overlaps(
            ((8, 8), (9, 8), (9, 9), (8, 9)),
            self.shape,
            min_intersection_area_pixels=5,
        )
        self.assertEqual(overlaps, ())


if __name__ == "__main__":
    unittest.main()
