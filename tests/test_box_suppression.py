import unittest

from models import Detection
from service.box_suppression import suppress_contained_lower_confidence


def detection(
    confidence: float,
    bbox: list[float],
    class_name: str = "water damage",
) -> Detection:
    return Detection(
        class_name=class_name,
        confidence=confidence,
        bbox=bbox,
    )


class ContainedBoxSuppressionTests(unittest.TestCase):
    def test_discards_lower_confidence_smaller_box(self) -> None:
        higher = detection(0.9, [0.0, 0.0, 100.0, 100.0])
        lower = detection(0.6, [25.0, 25.0, 75.0, 75.0])

        result = suppress_contained_lower_confidence([higher, lower])

        self.assertEqual(result, [higher])

    def test_discards_lower_confidence_larger_box(self) -> None:
        lower_larger = detection(0.6, [0.0, 0.0, 100.0, 100.0])
        higher_smaller = detection(0.9, [25.0, 25.0, 75.0, 75.0])

        result = suppress_contained_lower_confidence(
            [lower_larger, higher_smaller]
        )

        self.assertEqual(result, [higher_smaller])

    def test_keeps_partially_overlapping_boxes(self) -> None:
        left = detection(0.9, [0.0, 0.0, 100.0, 100.0])
        right = detection(0.6, [60.0, 0.0, 160.0, 100.0])

        result = suppress_contained_lower_confidence([left, right])

        self.assertEqual(result, [left, right])

    def test_keeps_contained_boxes_of_different_classes(self) -> None:
        damage = detection(0.9, [0.0, 0.0, 100.0, 100.0])
        pipe = detection(0.6, [25.0, 25.0, 75.0, 75.0], "pipe")

        result = suppress_contained_lower_confidence([damage, pipe])

        self.assertEqual(result, [damage, pipe])

    def test_keeps_equal_confidence_contained_boxes(self) -> None:
        outer = detection(0.8, [0.0, 0.0, 100.0, 100.0])
        inner = detection(0.8, [25.0, 25.0, 75.0, 75.0])

        result = suppress_contained_lower_confidence([outer, inner])

        self.assertEqual(result, [outer, inner])

    def test_discarded_box_cannot_suppress_an_unrelated_box(self) -> None:
        discarded_outer = detection(0.8, [0.0, 0.0, 100.0, 100.0])
        higher_left = detection(0.9, [0.0, 0.0, 40.0, 100.0])
        lower_right = detection(0.7, [60.0, 0.0, 100.0, 100.0])

        result = suppress_contained_lower_confidence(
            [discarded_outer, higher_left, lower_right]
        )

        self.assertEqual(result, [higher_left, lower_right])


if __name__ == "__main__":
    unittest.main()
