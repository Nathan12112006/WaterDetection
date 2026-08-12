import os
import sys
import unittest
from types import ModuleType
from unittest.mock import MagicMock, patch

from PIL import Image


class BackendInferenceSettingsTests(unittest.TestCase):
    def test_torch_backend_allows_trusted_runtime_checkpoint_loading(self) -> None:
        observed_setting: list[str | None] = []
        model = MagicMock()

        def load_model(model_path: str) -> MagicMock:
            observed_setting.append(
                os.getenv("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD")
            )
            return model

        fake_ultralytics = ModuleType("ultralytics")
        fake_ultralytics.YOLO = load_model  # type: ignore[attr-defined]
        module_name = "service.backends.torch_backend"
        previous_module = sys.modules.pop(module_name, None)
        previous_setting = os.environ.pop(
            "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD",
            None,
        )

        try:
            with patch.dict(sys.modules, {"ultralytics": fake_ultralytics}):
                from service.backends.torch_backend import TorchBackend

                TorchBackend(model_path="best.pt", device="cpu")
        finally:
            sys.modules.pop(module_name, None)
            if previous_module is not None:
                sys.modules[module_name] = previous_module
            if previous_setting is not None:
                os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = previous_setting
            else:
                os.environ.pop("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", None)

        self.assertEqual(observed_setting, ["1"])
        self.assertNotIn("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", os.environ)

    def test_torch_backend_owns_iou_threshold(self) -> None:
        model = MagicMock()
        model.predict.return_value = []
        yolo = MagicMock(return_value=model)
        fake_ultralytics = ModuleType("ultralytics")
        fake_ultralytics.YOLO = yolo  # type: ignore[attr-defined]
        module_name = "service.backends.torch_backend"
        previous_module = sys.modules.pop(module_name, None)

        try:
            with patch.dict(sys.modules, {"ultralytics": fake_ultralytics}):
                from service.backends.torch_backend import TorchBackend

                backend = TorchBackend(model_path="best.pt", device="cpu")
                backend.detect(Image.new("RGB", (4, 4)), confidence=0.25)
        finally:
            sys.modules.pop(module_name, None)
            if previous_module is not None:
                sys.modules[module_name] = previous_module

        model.predict.assert_called_once()
        self.assertEqual(model.predict.call_args.kwargs["iou"], 0.4)
        self.assertTrue(model.predict.call_args.kwargs["agnostic_nms"])

    def test_onnx_backend_owns_same_iou_threshold(self) -> None:
        from service.backends.onnx_backend import OnnxBackend

        self.assertEqual(OnnxBackend._NMS_IOU_THRESHOLD, 0.4)


if __name__ == "__main__":
    unittest.main()
