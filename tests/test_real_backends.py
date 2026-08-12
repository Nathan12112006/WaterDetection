"""Opt-in integration coverage for the checked-in Torch model roles."""

import os
import unittest

from models import Detection
from service import DetectionRuntime


def intersection_over_union(left: Detection, right: Detection) -> float:
    """Return the overlap ratio for two detection boxes."""

    left_x1, left_y1, left_x2, left_y2 = left.bbox
    right_x1, right_y1, right_x2, right_y2 = right.bbox
    intersection_width = max(0.0, min(left_x2, right_x2) - max(left_x1, right_x1))
    intersection_height = max(
        0.0,
        min(left_y2, right_y2) - max(left_y1, right_y1),
    )
    intersection = intersection_width * intersection_height
    left_area = max(0.0, left_x2 - left_x1) * max(0.0, left_y2 - left_y1)
    right_area = max(0.0, right_x2 - right_x1) * max(
        0.0,
        right_y2 - right_y1,
    )
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


@unittest.skipUnless(
    os.getenv("YOLO_RUN_REAL_MODEL_TESTS") == "1",
    "Set YOLO_RUN_REAL_MODEL_TESTS=1 to run real-model integration tests.",
)
class RealBackendTests(unittest.TestCase):
    def test_runtime_supports_all_public_model_roles(self) -> None:
        runtime = DetectionRuntime(device="cpu")

        for model in ("water_accumulation", "water_detection"):
            with self.subTest(model=model):
                detections = runtime.detect(
                    "test1.jpg", model=model, confidence=0.25
                )
                self.assertIsInstance(detections, list)
                self.assertTrue(
                    all(detection.class_name for detection in detections)
                )


if __name__ == "__main__":
    unittest.main()
