import unittest
import inspect

import service
from api.app import detect_annotated_image, detect_image
from config import AppConfig
from utils import ConfigurationError


class PublicSurfaceTests(unittest.TestCase):
    def test_detection_service_is_not_part_of_the_public_service_package(self) -> None:
        self.assertFalse(hasattr(service, "DetectionService"))

    def test_application_configuration_accepts_only_named_models(self) -> None:
        with self.assertRaises(ConfigurationError):
            AppConfig(model="custom.pt")

    def test_public_contract_has_no_backend_or_checkpoint_choices(self) -> None:
        self.assertFalse(hasattr(AppConfig(), "backend"))
        self.assertFalse(hasattr(AppConfig(), "checkpoint"))
        for endpoint in (detect_image, detect_annotated_image):
            parameters = inspect.signature(endpoint).parameters
            self.assertNotIn("backend", parameters)
            self.assertNotIn("checkpoint", parameters)


if __name__ == "__main__":
    unittest.main()
