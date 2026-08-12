import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import call, patch

from PIL import Image

from models import Detection
from service.detection_runtime import DetectionRuntime, _create_adapter
from service.model_manifest import (
    GENERAL_MODEL_PATH,
    SPECIALIST_MODEL_PATH,
)
from utils import ConfigurationError, DetectionError, ModelManifestError


class FixedAdapter:
    def __init__(self, detections: list[Detection]) -> None:
        self.detections = detections
        self.confidences: list[float] = []

    def detect(self, image: Image.Image, confidence: float) -> list[Detection]:
        self.confidences.append(confidence)
        return self.detections


class DetectionRuntimeTests(unittest.TestCase):
    def test_runtime_verifies_fixed_files_before_available(self) -> None:
        adapters = {
            "general": FixedAdapter([]),
            "specialist": FixedAdapter([]),
        }

        with patch(
            "service.detection_runtime.verify_runtime_models"
        ) as verify_models:
            with patch(
                "service.detection_runtime._create_adapter",
                side_effect=lambda role, device: adapters[role],
            ) as create_adapter:
                DetectionRuntime(device="cpu")

        verify_models.assert_called_once_with()
        self.assertEqual(
            create_adapter.call_args_list,
            [call("general", "cpu"), call("specialist", "cpu")],
        )

    def test_empty_startup_device_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "Device must not be empty"):
            DetectionRuntime(device="   ")

    def test_create_adapter_loads_general_root_model_and_validates_names(self) -> None:
        class FakeBackend:
            calls: list[tuple[str, str]] = []

            def __init__(self, *, model_path: str, device: str) -> None:
                self.calls.append((model_path, device))
                self.model = type(
                    "LoadedModel",
                    (),
                    {
                        "names": {
                            0: "pipe burst",
                            1: "water accumulation",
                            2: "water drop",
                        }
                    },
                )()

        fake_backend_module = ModuleType("service.backends.torch_backend")
        fake_backend_module.TorchBackend = FakeBackend  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules,
            {"service.backends.torch_backend": fake_backend_module},
        ):
            _create_adapter("general", "cpu")

        self.assertEqual(FakeBackend.calls, [(str(GENERAL_MODEL_PATH), "cpu")])

    def test_create_adapter_loads_specialist_root_model_and_validates_names(self) -> None:
        class FakeBackend:
            calls: list[tuple[str, str]] = []

            def __init__(self, *, model_path: str, device: str) -> None:
                self.calls.append((model_path, device))
                self.model = type(
                    "LoadedModel",
                    (),
                    {"names": {0: "water damage"}},
                )()

        fake_backend_module = ModuleType("service.backends.torch_backend")
        fake_backend_module.TorchBackend = FakeBackend  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules,
            {"service.backends.torch_backend": fake_backend_module},
        ):
            _create_adapter("specialist", "cpu")

        self.assertEqual(FakeBackend.calls, [(str(SPECIALIST_MODEL_PATH), "cpu")])

    def test_create_adapter_rejects_wrong_loaded_class_map(self) -> None:
        class FakeBackend:
            def __init__(self, *, model_path: str, device: str) -> None:
                self.model = type(
                    "LoadedModel",
                    (),
                    {"names": {0: "water damage"}},
                )()

        fake_backend_module = ModuleType("service.backends.torch_backend")
        fake_backend_module.TorchBackend = FakeBackend  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules,
            {"service.backends.torch_backend": fake_backend_module},
        ):
            with self.assertRaises(ModelManifestError):
                _create_adapter("general", "cpu")

    def test_water_detection_uses_best_pt_without_specialist_fallback(self) -> None:
        burst = Detection("pipe burst", 0.8, [0.0, 0.0, 5.0, 5.0])
        specialist = Detection("water damage", 0.5, [1.0, 1.0, 7.0, 7.0])
        ignored = Detection("unexpected class", 0.9, [2.0, 2.0, 3.0, 3.0])
        general = FixedAdapter([burst])
        accumulation = FixedAdapter([specialist, ignored])

        with patch("service.detection_runtime.verify_runtime_models"):
            with patch(
                "service.detection_runtime._create_adapter",
                side_effect=lambda role, device: (
                    general if role == "general" else accumulation
                ),
            ) as create_adapter:
                runtime = DetectionRuntime(device="cpu")
                result = runtime.detect(
                    Image.new("RGB", (8, 8)),
                    confidence=0.2,
                    accumulation_confidence=0.1,
                )

        self.assertEqual(result, [burst])
        self.assertEqual(general.confidences, [0.2])
        self.assertEqual(accumulation.confidences, [])
        self.assertEqual(
            create_adapter.call_args_list,
            [
                unittest.mock.call("general", "cpu"),
                unittest.mock.call("specialist", "cpu"),
            ],
        )

    def test_specialist_is_not_called_when_general_has_normalized_accumulation(self) -> None:
        general = FixedAdapter(
            [Detection(" Water_Accumulation ", 0.7, [1.0, 1.0, 6.0, 6.0])]
        )
        accumulation = FixedAdapter(
            [Detection("water damage", 0.5, [1.0, 1.0, 7.0, 7.0])]
        )

        with patch("service.detection_runtime.verify_runtime_models"):
            with patch(
                "service.detection_runtime._create_adapter",
                side_effect=lambda role, device: (
                    general if role == "general" else accumulation
                ),
            ):
                runtime = DetectionRuntime(device="cpu")
                result = runtime.detect(Image.new("RGB", (8, 8)))

        self.assertEqual(result, general.detections)
        self.assertEqual(general.confidences, [0.25])
        self.assertEqual(accumulation.confidences, [])

    def test_adapters_are_loaded_at_startup_and_reused(self) -> None:
        general = FixedAdapter([])
        accumulation = FixedAdapter([])
        load_counts = {"general": 0, "specialist": 0}

        def load(role: str, device: str) -> FixedAdapter:
            load_counts[role] += 1
            return general if role == "general" else accumulation

        with patch("service.detection_runtime.verify_runtime_models"):
            with patch("service.detection_runtime._create_adapter", side_effect=load):
                runtime = DetectionRuntime(device="cpu")
                self.assertEqual(load_counts, {"general": 1, "specialist": 1})
                image = Image.new("RGB", (4, 4))
                runtime.detect(image)
                runtime.detect(image)

        self.assertEqual(load_counts, {"general": 1, "specialist": 1})
        self.assertEqual(general.confidences, [0.25, 0.25])
        self.assertEqual(accumulation.confidences, [])

    def test_invalid_confidence_is_rejected_before_backend_loading(self) -> None:
        adapters = {
            "general": FixedAdapter([]),
            "specialist": FixedAdapter([]),
        }
        with patch(
            "service.detection_runtime._create_adapter",
            side_effect=lambda role, device: adapters[role],
        ) as create_adapter:
            with patch("service.detection_runtime.verify_runtime_models"):
                runtime = DetectionRuntime(device="cpu")

                with self.assertRaisesRegex(
                    ConfigurationError,
                    "Confidence must be between 0.0 and 1.0",
                ):
                    runtime.detect(Image.new("RGB", (4, 4)), confidence=1.1)

        self.assertEqual(create_adapter.call_count, 2)

    def test_model_failure_is_reported_as_detection_error(self) -> None:
        with patch("service.detection_runtime.verify_runtime_models"):
            with patch(
                "service.detection_runtime._create_adapter",
                side_effect=RuntimeError("load failed"),
            ):
                with self.assertRaisesRegex(
                    DetectionError,
                    "general model loading failed",
                ):
                    DetectionRuntime(device="cpu")

    def test_path_image_is_normalized_to_rgb(self) -> None:
        received: list[Image.Image] = []

        class RecordingAdapter:
            def detect(self, image: Image.Image, confidence: float) -> list[Detection]:
                received.append(image)
                if image.mode != "RGB":
                    raise AssertionError("Runtime did not normalize the image.")
                return [Detection("water accumulation", confidence, [0.0] * 4)]

        with patch("service.detection_runtime.verify_runtime_models"):
            with patch(
                "service.detection_runtime._create_adapter",
                return_value=RecordingAdapter(),
            ):
                runtime = DetectionRuntime(device="cpu")
                runtime.detect(Image.new("RGBA", (4, 4)))

        self.assertEqual(len(received), 1)


if __name__ == "__main__":
    unittest.main()
