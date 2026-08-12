import unittest

from PIL import Image

from models import Detection
from service.ensemble_runtime import WaterDetectionEnsemble
from utils import ConfigurationError


class FixedAdapter:
    def __init__(self, detections: list[Detection]) -> None:
        self.detections = detections
        self.confidences: list[float] = []

    def detect(
        self,
        image: Image.Image,
        confidence: float,
    ) -> list[Detection]:
        self.confidences.append(confidence)
        return self.detections


class WaterDetectionEnsembleTests(unittest.TestCase):
    def test_keeps_general_accumulation_without_adding_specialist_boxes(
        self,
    ) -> None:
        burst = Detection("pipe burst", 0.8, [0.0, 0.0, 5.0, 5.0])
        general_accumulation = Detection(
            "water accumulation",
            0.7,
            [1.0, 1.0, 6.0, 6.0],
        )
        drop = Detection("water drop", 0.6, [2.0, 2.0, 3.0, 3.0])
        specialist_accumulation = Detection(
            "water damage",
            0.5,
            [1.0, 1.0, 7.0, 7.0],
        )
        general = FixedAdapter([burst, general_accumulation, drop])
        specialist = FixedAdapter([specialist_accumulation])
        ensemble = WaterDetectionEnsemble(
            three_class_model="unused.pt",
            accumulation_model="unused.pt",
            three_class_adapter=general,
            accumulation_adapter=specialist,
        )

        result = ensemble.detect(
            Image.new("RGB", (8, 8)),
            three_class_confidence=0.2,
            accumulation_confidence=0.1,
        )

        self.assertEqual(result, [burst, general_accumulation, drop])
        self.assertEqual(general.confidences, [0.2])
        self.assertEqual(specialist.confidences, [])

    def test_adds_specialist_boxes_when_general_misses_accumulation(self) -> None:
        burst = Detection("pipe burst", 0.8, [0.0, 0.0, 5.0, 5.0])
        specialist_accumulation = Detection(
            "water damage",
            0.5,
            [1.0, 1.0, 7.0, 7.0],
        )
        ensemble = WaterDetectionEnsemble(
            three_class_model="unused.pt",
            accumulation_model="unused.pt",
            three_class_adapter=FixedAdapter([burst]),
            accumulation_adapter=FixedAdapter([specialist_accumulation]),
        )

        result = ensemble.detect(Image.new("RGB", (8, 8)))

        self.assertEqual(result[0], burst)
        self.assertEqual(result[1].class_name, "water accumulation")
        self.assertEqual(result[1].bbox, specialist_accumulation.bbox)

    def test_different_class_overlap_is_preserved(self) -> None:
        burst = Detection("pipe burst", 0.8, [0.0, 0.0, 8.0, 8.0])
        accumulation = Detection("water damage", 0.7, [0.0, 0.0, 8.0, 8.0])
        ensemble = WaterDetectionEnsemble(
            three_class_model="unused.pt",
            accumulation_model="unused.pt",
            three_class_adapter=FixedAdapter([burst]),
            accumulation_adapter=FixedAdapter([accumulation]),
        )

        result = ensemble.detect(Image.new("RGB", (8, 8)))

        self.assertEqual(len(result), 2)
        self.assertEqual(
            [detection.class_name for detection in result],
            ["pipe burst", "water accumulation"],
        )

    def test_rejects_invalid_confidence(self) -> None:
        ensemble = WaterDetectionEnsemble(
            three_class_model="unused.pt",
            accumulation_model="unused.pt",
            three_class_adapter=FixedAdapter([]),
            accumulation_adapter=FixedAdapter([]),
        )

        with self.assertRaisesRegex(
            ConfigurationError,
            "Accumulation confidence",
        ):
            ensemble.detect(
                Image.new("RGB", (8, 8)),
                accumulation_confidence=1.1,
            )


if __name__ == "__main__":
    unittest.main()
