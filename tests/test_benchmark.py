import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import benchmark
from models import Detection


class BenchmarkTests(unittest.TestCase):
    def test_model_selection_is_supported_and_legacy_options_are_rejected(
        self,
    ) -> None:
        self.assertEqual(
            benchmark.parse_args(["--model", "water_detection"]).model,
            "water_detection",
        )
        for option in ("--backend", "--checkpoint"):
            with self.subTest(option=option):
                with redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as exit_context:
                        benchmark.parse_args([option, "custom"])

                self.assertEqual(exit_context.exception.code, 2)

    def test_benchmark_reports_cold_and_cached_detection_through_runtime(
        self,
    ) -> None:
        calls: list[tuple[str, float]] = []

        class FakeRuntime:
            def detect(
                self,
                image: str,
                *,
                model: str,
                confidence: float,
            ) -> list[Detection]:
                calls.append((image, confidence))
                return [
                    Detection(
                        class_name="water accumulation",
                        confidence=0.9,
                        bbox=[1.0, 2.0, 3.0, 4.0],
                    )
                ]

        args = SimpleNamespace(
            image="sample.jpg",
            model="water_detection",
            conf=0.6,
            warmup=1,
            runs=2,
        )
        result = benchmark.benchmark_runtime(FakeRuntime(), args)

        self.assertEqual(len(calls), 4)
        self.assertEqual(calls, [("sample.jpg", 0.6)] * 4)
        self.assertEqual(len(result.cached_inference_times_ms), 2)
        self.assertEqual(len(result.detections), 1)

    def test_main_uses_fixed_runtime_and_prints_summary(self) -> None:
        output = io.StringIO()
        with patch("benchmark.DetectionRuntime") as runtime_type:
            runtime_type.return_value.detect.return_value = []
            with redirect_stdout(output):
                exit_code = benchmark.main(
                    ["--warmup", "0", "--runs", "1"]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Fixed ensemble", output.getvalue())
        self.assertNotIn("ONNX", output.getvalue())
        runtime_type.assert_called_once_with(device="cpu")


if __name__ == "__main__":
    unittest.main()
