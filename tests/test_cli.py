import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from models import Detection

from cli import parse_args
from main import main


class CommandLineTests(unittest.TestCase):
    def test_cli_prints_detections_from_the_fixed_runtime(self) -> None:
        detections = [
            Detection(
                class_name="water accumulation",
                confidence=0.9,
                bbox=[1.0, 2.0, 3.0, 4.0],
            )
        ]
        output = io.StringIO()
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "sample.png"

            with patch("main.DetectionRuntime") as runtime_type:
                runtime_type.return_value.detect.return_value = detections
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "--image",
                            str(image_path),
                            "--conf",
                            "0.6",
                            "--device",
                            "cpu",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        runtime_type.assert_called_once_with(device="cpu")
        runtime_type.return_value.detect.assert_called_once_with(
            str(image_path),
            model="water_detection",
            confidence=0.6,
        )
        self.assertEqual(
            json.loads(output.getvalue()),
            [
                {
                    "class": "water accumulation",
                    "confidence": 0.9,
                    "bbox": [1.0, 2.0, 3.0, 4.0],
                }
            ],
        )

    def test_model_option_accepts_the_public_modes(self) -> None:
        self.assertEqual(
            parse_args(["--model", "water_accumulation"]).model,
            "water_accumulation",
        )
        self.assertEqual(
            parse_args(["--model", "water_detection_last"]).model,
            "water_detection_last",
        )
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exit_context:
                parse_args(["--model", "custom"])
        self.assertEqual(exit_context.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
