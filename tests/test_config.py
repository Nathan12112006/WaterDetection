import os
import unittest
from unittest.mock import patch

from config import AppConfig, ServiceConfig
from utils import ConfigurationError


class ServiceConfigTests(unittest.TestCase):
    def test_service_limits_are_loaded_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "YOLO_DEVICE": "cpu",
                "YOLO_MAX_UPLOAD_BYTES": "1024",
                "YOLO_MAX_IMAGE_PIXELS": "2048",
                "YOLO_REQUEST_TIMEOUT_SECONDS": "3.5",
                "YOLO_MAX_CONCURRENT_DETECTIONS": "4",
            },
            clear=True,
        ):
            config = ServiceConfig.from_environment()

        self.assertEqual(config.device, "cpu")
        self.assertEqual(config.max_upload_bytes, 1024)
        self.assertEqual(config.max_image_pixels, 2048)
        self.assertEqual(config.request_timeout_seconds, 3.5)
        self.assertEqual(config.max_concurrent_detections, 4)

    def test_invalid_service_limit_is_rejected_at_startup(self) -> None:
        with patch.dict(
            os.environ,
            {"YOLO_MAX_UPLOAD_BYTES": "not-an-integer"},
            clear=True,
        ):
            with self.assertRaisesRegex(
                ConfigurationError,
                "YOLO_MAX_UPLOAD_BYTES must be an integer",
            ):
                ServiceConfig.from_environment()

    def test_app_config_exposes_only_image_confidence_and_device(self) -> None:
        config = AppConfig(image="input.png", confidence=0.6, device="cuda:0")

        self.assertEqual(config.image, "input.png")
        self.assertEqual(config.confidence, 0.6)
        self.assertEqual(config.device, "cuda:0")
        self.assertFalse(hasattr(config, "backend"))
        self.assertFalse(hasattr(config, "checkpoint"))

    def test_app_config_accepts_last_checkpoint_selection(self) -> None:
        self.assertEqual(
            AppConfig(model="water_detection_last").model,
            "water_detection_last",
        )

    def test_app_config_validates_confidence_and_device(self) -> None:
        with self.assertRaisesRegex(
            ConfigurationError,
            "Confidence must be between 0.0 and 1.0",
        ):
            AppConfig(confidence=1.1)

        with self.assertRaisesRegex(ConfigurationError, "Device must not be empty"):
            AppConfig(device=" ")


if __name__ == "__main__":
    unittest.main()
