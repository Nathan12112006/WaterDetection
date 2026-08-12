from ast import literal_eval

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image

from models import Detection
from service.box_suppression import suppress_contained_lower_confidence
from utils import DetectionError


class OnnxBackend:
    _NMS_IOU_THRESHOLD = 0.40
    _MAX_DETECTIONS = 300

    def __init__(self, model_path: str, device: str) -> None:
        try:
            providers = self._get_providers(device)
            self.session = ort.InferenceSession(
                model_path,
                providers=providers,
            )

            model_input = self.session.get_inputs()[0]
            input_shape = model_input.shape

            if len(input_shape) != 4:
                raise DetectionError(
                    f"Expected a four-dimensional model input, got {input_shape}."
                )
            if not isinstance(input_shape[2], int) or not isinstance(
                input_shape[3], int
            ):
                raise DetectionError(
                    f"Expected a fixed model input size, got {input_shape}."
                )

            self.input_name = model_input.name
            self.input_height = input_shape[2]
            self.input_width = input_shape[3]
            self.class_names = self._get_class_names()
        except DetectionError:
            raise
        except Exception as error:
            raise DetectionError(
                f"ONNX model loading failed: {error}"
            ) from error

    @staticmethod
    def _get_providers(device: str) -> list[str]:
        if device.lower() == "cpu":
            return ["CPUExecutionProvider"]

        available_providers = ort.get_available_providers()
        if "CUDAExecutionProvider" not in available_providers:
            raise DetectionError(
                "CUDA was requested, but CUDAExecutionProvider is unavailable."
            )
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]

    def _get_class_names(self) -> dict[int, str]:
        metadata = self.session.get_modelmeta().custom_metadata_map
        names_text = metadata.get("names")

        if names_text is None:
            raise DetectionError("The ONNX model does not contain class names.")

        try:
            names = literal_eval(names_text)
        except (SyntaxError, ValueError) as error:
            raise DetectionError("The ONNX class names are invalid.") from error

        if not isinstance(names, dict):
            raise DetectionError("The ONNX class names must be a dictionary.")

        try:
            return {
                int(class_id): str(class_name)
                for class_id, class_name in names.items()
            }
        except (TypeError, ValueError) as error:
            raise DetectionError("The ONNX class names are invalid.") from error

    @staticmethod
    def _open_image(image: str | Image.Image) -> Image.Image:
        if isinstance(image, Image.Image):
            return image.convert("RGB")

        try:
            with Image.open(image) as opened_image:
                return opened_image.convert("RGB")
        except (OSError, ValueError) as error:
            raise DetectionError(f"Unable to read image: {error}") from error

    def _prepare_image(
        self,
        image: Image.Image,
    ) -> tuple[np.ndarray, float, int, int]:
        original_width, original_height = image.size

        width_scale = self.input_width / original_width
        height_scale = self.input_height / original_height
        scale = min(width_scale, height_scale)

        # Calculate the resized image dimensions and padding
        resized_width = round(original_width * scale)
        resized_height = round(original_height * scale)

        horizontal_padding = self.input_width - resized_width
        vertical_padding = self.input_height - resized_height
        left_padding = round(horizontal_padding / 2 - 0.1)
        right_padding = round(horizontal_padding / 2 + 0.1)
        top_padding = round(vertical_padding / 2 - 0.1)
        bottom_padding = round(vertical_padding / 2 + 0.1)

        resized_image = cv2.resize(
            np.asarray(image),
            (resized_width, resized_height),
            interpolation=cv2.INTER_LINEAR,
        )

        padded_image = cv2.copyMakeBorder(
            resized_image,
            top_padding,
            bottom_padding,
            left_padding,
            right_padding,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )

        input_tensor = padded_image.astype(np.float32) / 255.0
        input_tensor = input_tensor.transpose(2, 0, 1)
        input_tensor = np.expand_dims(input_tensor, axis=0)
        input_tensor = np.ascontiguousarray(input_tensor)

        return input_tensor, scale, left_padding, top_padding

    @staticmethod
    def _restore_bounding_box(
        model_box: np.ndarray,
        scale: float,
        left_padding: int,
        top_padding: int,
        original_width: int,
        original_height: int,
    ) -> list[float]:
        x1 = (float(model_box[0]) - left_padding) / scale
        y1 = (float(model_box[1]) - top_padding) / scale
        x2 = (float(model_box[2]) - left_padding) / scale
        y2 = (float(model_box[3]) - top_padding) / scale

        x1 = max(0.0, min(x1, float(original_width)))
        y1 = max(0.0, min(y1, float(original_height)))
        x2 = max(0.0, min(x2, float(original_width)))
        y2 = max(0.0, min(y2, float(original_height)))

        return [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]

    @staticmethod
    def _non_maximum_suppression(
        boxes: np.ndarray,
        scores: np.ndarray,
        iou_threshold: float,
    ) -> list[int]:
        if boxes.size == 0:
            return []

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
        order = np.argsort(scores)[::-1]
        kept: list[int] = []

        while order.size > 0:
            current = int(order[0])
            kept.append(current)
            if order.size == 1:
                break

            remaining = order[1:]
            intersection_x1 = np.maximum(x1[current], x1[remaining])
            intersection_y1 = np.maximum(y1[current], y1[remaining])
            intersection_x2 = np.minimum(x2[current], x2[remaining])
            intersection_y2 = np.minimum(y2[current], y2[remaining])
            intersection_width = np.maximum(
                0.0,
                intersection_x2 - intersection_x1,
            )
            intersection_height = np.maximum(
                0.0,
                intersection_y2 - intersection_y1,
            )
            intersection = intersection_width * intersection_height
            union = areas[current] + areas[remaining] - intersection
            iou = np.divide(
                intersection,
                union,
                out=np.zeros_like(intersection),
                where=union > 0.0,
            )
            order = remaining[iou <= iou_threshold]

        return kept

    def _decode_output(
        self,
        model_output: np.ndarray,
        confidence: float,
    ) -> list[tuple[np.ndarray, float, int]]:
        if model_output.ndim != 3 or model_output.shape[0] != 1:
            raise DetectionError(
                f"Unexpected ONNX output shape: {model_output.shape}."
            )

        output_matrix = model_output[0]
        raw_channel_count = 4 + len(self.class_names)

        if (
            output_matrix.shape[0] == raw_channel_count
            and output_matrix.shape[1] > raw_channel_count
        ):
            rows = output_matrix.transpose()
            class_scores = rows[:, 4:]
            class_ids = np.argmax(class_scores, axis=1)
            scores = class_scores[
                np.arange(class_scores.shape[0]),
                class_ids,
            ]
            accepted = scores >= confidence
            rows = rows[accepted]
            scores = scores[accepted]
            class_ids = class_ids[accepted]

            boxes = np.empty((rows.shape[0], 4), dtype=np.float32)
            boxes[:, 0] = rows[:, 0] - rows[:, 2] / 2.0
            boxes[:, 1] = rows[:, 1] - rows[:, 3] / 2.0
            boxes[:, 2] = rows[:, 0] + rows[:, 2] / 2.0
            boxes[:, 3] = rows[:, 1] + rows[:, 3] / 2.0

            kept_indices: list[int] = []
            for class_id in np.unique(class_ids):
                class_indices = np.flatnonzero(class_ids == class_id)
                class_kept = self._non_maximum_suppression(
                    boxes[class_indices],
                    scores[class_indices],
                    self._NMS_IOU_THRESHOLD,
                )
                kept_indices.extend(
                    int(class_indices[index]) for index in class_kept
                )

            kept_indices.sort(key=lambda index: float(scores[index]), reverse=True)
            return [
                (boxes[index], float(scores[index]), int(class_ids[index]))
                for index in kept_indices[: self._MAX_DETECTIONS]
            ]

        if output_matrix.shape[1] == 6:
            detections: list[tuple[np.ndarray, float, int]] = []
            for row in output_matrix:
                score = float(row[4])
                if score < confidence:
                    continue
                detections.append((row[:4], score, int(row[5])))
            return detections[: self._MAX_DETECTIONS]

        raise DetectionError(
            f"Unexpected ONNX output shape: {model_output.shape}."
        )

    def detect(
        self,
        image: str | Image.Image,
        confidence: float,
    ) -> list[Detection]:
        rgb_image = self._open_image(image)
        try:
            original_width, original_height = rgb_image.size
            prepared = self._prepare_image(rgb_image)
            input_tensor, scale, left_padding, top_padding = prepared
        finally:
            rgb_image.close()

        try:
            model_outputs = self.session.run(
                None,
                {self.input_name: input_tensor},
            )
            decoded_detections = self._decode_output(
                model_outputs[0],
                confidence,
            )

            detections: list[Detection] = []

            for model_box, score, class_id in decoded_detections:
                class_name = self.class_names.get(class_id, str(class_id))

                bounding_box = self._restore_bounding_box(
                    model_box=model_box,
                    scale=scale,
                    left_padding=left_padding,
                    top_padding=top_padding,
                    original_width=original_width,
                    original_height=original_height,
                )

                detections.append(
                    Detection(
                        class_name=class_name,
                        confidence=round(score, 4),
                        bbox=bounding_box,
                    )
                )

            return suppress_contained_lower_confidence(detections)
        except Exception as error:
            raise DetectionError(f"ONNX inference failed: {error}") from error
