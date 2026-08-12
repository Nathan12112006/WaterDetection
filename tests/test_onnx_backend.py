import unittest

import numpy as np

from service.backends.onnx_backend import OnnxBackend
from utils import DetectionError


class OnnxBackendOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = OnnxBackend.__new__(OnnxBackend)
        self.backend.class_names = {
            0: "pipe burst",
            1: "water accumulation",
            2: "water drop",
        }

    def test_raw_yolov8_output_is_transposed_filtered_and_suppressed(self) -> None:
        output = np.zeros((1, 7, 10), dtype=np.float32)
        output[0, :, 0] = [100.0, 100.0, 40.0, 40.0, 0.90, 0.05, 0.02]
        output[0, :, 1] = [102.0, 102.0, 40.0, 40.0, 0.80, 0.10, 0.03]
        output[0, :, 2] = [300.0, 300.0, 20.0, 20.0, 0.10, 0.70, 0.05]

        detections = self.backend._decode_output(output, confidence=0.25)

        self.assertEqual(len(detections), 2)
        first_box, first_score, first_class = detections[0]
        second_box, second_score, second_class = detections[1]
        np.testing.assert_allclose(first_box, [80.0, 80.0, 120.0, 120.0])
        np.testing.assert_allclose(second_box, [290.0, 290.0, 310.0, 310.0])
        self.assertAlmostEqual(first_score, 0.90)
        self.assertAlmostEqual(second_score, 0.70)
        self.assertEqual((first_class, second_class), (0, 1))

    def test_unexpected_output_shape_is_rejected(self) -> None:
        with self.assertRaisesRegex(DetectionError, "Unexpected ONNX output shape"):
            self.backend._decode_output(
                np.zeros((1, 4, 10), dtype=np.float32),
                confidence=0.25,
            )


if __name__ == "__main__":
    unittest.main()
