import os
from threading import Lock

from PIL import Image
from ultralytics import YOLO

from models import Detection
from service.box_suppression import suppress_contained_lower_confidence
from utils import DetectionError


_MODEL_LOAD_LOCK = Lock()
_TRUSTED_CHECKPOINT_ENVIRONMENT_VARIABLE = (
    "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"
)


class TorchBackend:
    def __init__(self, model_path: str, device: str) -> None:
        self.device = device
        self._inference_lock = Lock()

        try:
            with _MODEL_LOAD_LOCK:
                previous_setting = os.environ.get(
                    _TRUSTED_CHECKPOINT_ENVIRONMENT_VARIABLE
                )
                os.environ[
                    _TRUSTED_CHECKPOINT_ENVIRONMENT_VARIABLE
                ] = "1"
                try:
                    # Runtime model paths are fixed by DetectionRuntime and
                    # cannot be supplied by HTTP or CLI callers. Older
                    # Ultralytics releases require full checkpoint loading
                    # with PyTorch 2.6 and newer.
                    self.model = YOLO(model_path)
                finally:
                    if previous_setting is None:
                        os.environ.pop(
                            _TRUSTED_CHECKPOINT_ENVIRONMENT_VARIABLE,
                            None,
                        )
                    else:
                        os.environ[
                            _TRUSTED_CHECKPOINT_ENVIRONMENT_VARIABLE
                        ] = previous_setting
        except Exception as error:
            raise DetectionError(
                f"PyTorch model loading failed: {error}"
            ) from error

    def detect(
        self,
        image: str | Image.Image,
        confidence: float,
    ) -> list[Detection]:
        try:
            with self._inference_lock:
                results = self.model.predict(
                    source=image,
                    conf=confidence,
                    iou=0.4,
                    device=self.device,
                    rect=False,
                    verbose=False,
                )

            detections: list[Detection] = []

            for result in results:
                boxes = result.boxes

                if boxes is None:
                    continue

                for class_id, score, bbox in zip(
                    boxes.cls.cpu().tolist(),
                    boxes.conf.cpu().tolist(),
                    boxes.xyxy.cpu().tolist(),
                ):
                    detections.append(
                        Detection(
                            class_name=result.names[int(class_id)],
                            confidence=round(float(score), 4),
                            bbox=[round(float(value), 2) for value in bbox],
                        )
                    )

            return suppress_contained_lower_confidence(detections)
        except Exception as error:
            raise DetectionError(f"PyTorch inference failed: {error}") from error
