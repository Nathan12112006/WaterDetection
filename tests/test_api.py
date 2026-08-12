import io
import os
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from api.app import app
from models import Detection
from utils import DetectionError


def make_png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(output, format="PNG")
    return output.getvalue()


class DetectionApiTests(unittest.TestCase):
    def test_health_reports_ready_after_startup(self) -> None:
        with patch("api.app.DetectionRuntime"):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_upload_size_limit_rejects_large_file_before_inference(self) -> None:
        with patch.dict(os.environ, {"YOLO_MAX_UPLOAD_BYTES": "10"}):
            with patch("api.app.DetectionRuntime") as runtime_type:
                with TestClient(app) as client:
                    response = client.post(
                        "/detect",
                        files={"file": ("sample.png", make_png(), "image/png")},
                    )

        self.assertEqual(response.status_code, 413)
        self.assertIn("file is too large", response.json()["detail"])
        runtime_type.return_value.detect.assert_not_called()

    def test_pixel_limit_rejects_large_dimensions_before_inference(self) -> None:
        with patch.dict(os.environ, {"YOLO_MAX_IMAGE_PIXELS": "15"}):
            with patch("api.app.DetectionRuntime") as runtime_type:
                with TestClient(app) as client:
                    response = client.post(
                        "/detect",
                        files={"file": ("sample.png", make_png(), "image/png")},
                    )

        self.assertEqual(response.status_code, 413)
        self.assertIn("too many pixels", response.json()["detail"])
        runtime_type.return_value.detect.assert_not_called()

    def test_detection_timeout_returns_504_without_closing_worker_image(
        self,
    ) -> None:
        worker_saw_open_image = False

        def slow_detect(image: Image.Image, *, confidence: float) -> list[Detection]:
            nonlocal worker_saw_open_image
            time.sleep(0.08)
            image.getpixel((0, 0))
            worker_saw_open_image = True
            return []

        with patch.dict(os.environ, {"YOLO_REQUEST_TIMEOUT_SECONDS": "0.01"}):
            with patch("api.app.DetectionRuntime") as runtime_type:
                runtime_type.return_value.detect.side_effect = slow_detect
                with TestClient(app) as client:
                    response = client.post(
                        "/detect",
                        files={"file": ("sample.png", make_png(), "image/png")},
                    )

        self.assertEqual(response.status_code, 504)
        self.assertIn("Detection timed out", response.json()["detail"])
        self.assertTrue(worker_saw_open_image)

    def test_concurrency_limit_rejects_excess_detection(self) -> None:
        inference_started = threading.Event()
        finish_inference = threading.Event()

        def blocking_detect(image: Image.Image, *, confidence: float) -> list[Detection]:
            inference_started.set()
            finish_inference.wait(timeout=2)
            return []

        def post_detection(client: TestClient):
            return client.post(
                "/detect",
                files={"file": ("sample.png", make_png(), "image/png")},
            )

        with patch.dict(
            os.environ,
            {
                "YOLO_MAX_CONCURRENT_DETECTIONS": "1",
                "YOLO_REQUEST_TIMEOUT_SECONDS": "2",
            },
        ):
            with patch("api.app.DetectionRuntime") as runtime_type:
                runtime_type.return_value.detect.side_effect = blocking_detect
                with TestClient(app) as client:
                    with ThreadPoolExecutor(max_workers=1) as callers:
                        first_request = callers.submit(post_detection, client)
                        self.assertTrue(inference_started.wait(timeout=1))
                        excess_response = post_detection(client)
                        finish_inference.set()
                        first_response = first_request.result(timeout=2)

        self.assertEqual(excess_response.status_code, 429)
        self.assertIn(
            "maximum number of detections",
            excess_response.json()["detail"],
        )
        self.assertEqual(first_response.status_code, 200)

    def test_detection_failure_returns_503_without_backend_suggestions(self) -> None:
        with patch("api.app.DetectionRuntime") as runtime_type:
            runtime_type.return_value.detect.side_effect = DetectionError(
                "ensemble unavailable"
            )
            with TestClient(app) as client:
                response = client.post(
                    "/detect",
                    files={"file": ("sample.png", make_png(), "image/png")},
                )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "ensemble unavailable")
        self.assertNotIn("onnx", response.text.lower())

    def test_openapi_exposes_only_confidence_control(self) -> None:
        with patch("api.app.DetectionRuntime"):
            with TestClient(app) as client:
                response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        request_schema = schema["paths"]["/detect"]["post"]["requestBody"][
            "content"
        ]["multipart/form-data"]["schema"]
        schema_name = request_schema["$ref"].split("/")[-1]
        form_schema = schema["components"]["schemas"][schema_name]

        self.assertEqual(set(form_schema["required"]), {"file"})
        self.assertNotIn("backend", form_schema["properties"])
        self.assertNotIn("checkpoint", form_schema["properties"])
        self.assertEqual(
            form_schema["properties"]["model"]["default"],
            "water_detection",
        )
        self.assertEqual(
            form_schema["properties"]["model"]["enum"],
            ["water_accumulation", "water_detection"],
        )
        self.assertEqual(form_schema["properties"]["confidence"]["default"], 0.25)
        self.assertEqual(form_schema["properties"]["confidence"]["minimum"], 0.0)
        self.assertEqual(form_schema["properties"]["confidence"]["maximum"], 1.0)

    def test_http_validation_rejects_missing_file_and_bad_confidence(self) -> None:
        image_file = {"file": ("sample.png", make_png(), "image/png")}

        with patch("api.app.DetectionRuntime"):
            with TestClient(app) as client:
                missing_file = client.post("/detect")
                low_confidence = client.post(
                    "/detect",
                    files=image_file,
                    data={"confidence": "-0.1"},
                )
                high_confidence = client.post(
                    "/detect",
                    files=image_file,
                    data={"confidence": "1.1"},
                )

        self.assertEqual(missing_file.status_code, 422)
        self.assertEqual(low_confidence.status_code, 422)
        self.assertEqual(high_confidence.status_code, 422)

    def test_uploaded_image_uses_fixed_runtime_and_confidence(self) -> None:
        detections = [
            Detection(
                class_name="water accumulation",
                confidence=0.9,
                bbox=[1.0, 2.0, 3.0, 4.0],
            )
        ]
        with patch("api.app.DetectionRuntime") as runtime_type:
            runtime_type.return_value.detect.return_value = detections
            with TestClient(app) as client:
                response = client.post(
                    "/detect",
                    files={"file": ("sample.png", make_png(), "image/png")},
                    data={"confidence": "0.6"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["class"], "water accumulation")
        detect = runtime_type.return_value.detect
        detect.assert_called_once()
        self.assertEqual(detect.call_args.kwargs["confidence"], 0.6)
        self.assertIsInstance(detect.call_args.args[0], Image.Image)

    def test_annotated_detection_returns_downloadable_full_size_png(self) -> None:
        detections = [
            Detection(
                class_name="water damage",
                confidence=0.875,
                bbox=[0.0, 0.0, 3.0, 3.0],
            )
        ]
        with patch("api.app.DetectionRuntime") as runtime_type:
            runtime_type.return_value.detect.return_value = detections
            with TestClient(app) as client:
                response = client.post(
                    "/detect/annotated",
                    files={"file": ("sample.png", make_png(), "image/png")},
                    data={"confidence": "0.4"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(
            response.headers["content-disposition"],
            'attachment; filename="annotated.png"',
        )
        self.assertEqual(response.headers["cache-control"], "no-store")
        with Image.open(io.BytesIO(response.content)) as annotated:
            self.assertEqual(annotated.size, (4, 4))
            self.assertEqual(annotated.format, "PNG")
            self.assertNotEqual(annotated.getpixel((0, 0)), (255, 255, 255))


if __name__ == "__main__":
    unittest.main()
