"""Legacy helper for the retired combined-model experiment.

The application runtime no longer imports this module. Public inference uses
one fixed model role at a time through :mod:`service.detection_runtime`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PIL import Image

from models import Detection
from service.model_manifest import (
    MODEL_PATHS,
    validate_loaded_class_names,
    verify_runtime_models,
)
from utils import ConfigurationError, DetectionError, ModelManifestError

_ACCUMULATION_CLASS = "water accumulation"
_SPECIALIST_CLASS = "water damage"


class DetectionAdapter(Protocol):
    """Small inference interface used by the ensemble."""

    def detect(
        self,
        image: Image.Image,
        confidence: float,
    ) -> list[Detection]: ...


def _extract_loaded_class_map(adapter: object) -> object:
    """Read the class map exposed by a loaded Torch adapter."""

    for owner in (
        adapter,
        getattr(adapter, "model", None),
    ):
        if owner is None:
            continue
        for attribute in ("class_names", "names"):
            names = getattr(owner, attribute, None)
            if names is not None:
                return names
    raise ModelManifestError("Loaded Torch model does not expose class names.")


def _create_torch_adapter(role: str, device: str) -> DetectionAdapter:
    """Load and validate one fixed Torch model."""

    from service.backends.torch_backend import TorchBackend

    adapter = TorchBackend(model_path=str(MODEL_PATHS[role]), device=device)
    validate_loaded_class_names(role, _extract_loaded_class_map(adapter))
    return adapter


class WaterDetectionEnsemble:
    """Run the general model and conditionally add specialist accumulation.

    Model paths are fixed to the project root.  Optional path arguments are
    accepted only for the old CLI's call shape and must resolve to those exact
    roots; injected adapters may use placeholder paths in unit tests without
    loading a caller-provided checkpoint.
    """

    def __init__(
        self,
        *,
        three_class_model: str | Path | None = None,
        accumulation_model: str | Path | None = None,
        device: str = "cpu",
        three_class_adapter: DetectionAdapter | None = None,
        accumulation_adapter: DetectionAdapter | None = None,
    ) -> None:
        if not device.strip():
            raise ConfigurationError("Device must not be empty.")

        verify_runtime_models()
        if three_class_adapter is None:
            self._validate_fixed_path(three_class_model, "general")
            self._general_adapter = _create_torch_adapter("general", device)
        else:
            self._general_adapter = three_class_adapter

        if accumulation_adapter is None:
            self._validate_fixed_path(accumulation_model, "specialist")
            self._specialist_adapter = _create_torch_adapter("specialist", device)
        else:
            self._specialist_adapter = accumulation_adapter

    @staticmethod
    def _validate_fixed_path(path: str | Path | None, role: str) -> None:
        if path is None:
            return
        try:
            supplied = Path(path).resolve()
            expected = Path(MODEL_PATHS[role]).resolve()
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            raise ConfigurationError(
                f"{role.title()} model path is invalid."
            ) from error
        if supplied != expected:
            raise ConfigurationError(
                f"{role.title()} model path is fixed to {expected}."
            )

    def detect(
        self,
        image: str | Path | Image.Image,
        *,
        confidence: float = 0.25,
        accumulation_confidence: float | None = None,
        three_class_confidence: float | None = None,
    ) -> list[Detection]:
        """Return every general detection and conditional specialist boxes.

        ``three_class_confidence`` is retained as a keyword alias for the
        earlier ensemble call shape.  The public runtime uses ``confidence``;
        when no specialist threshold is supplied it uses the same value.
        """

        if three_class_confidence is not None:
            if confidence != 0.25 and confidence != three_class_confidence:
                raise ConfigurationError(
                    "Specify only one general confidence threshold."
                )
            confidence = three_class_confidence
        self._validate_confidence(confidence, "Confidence")
        if accumulation_confidence is None:
            accumulation_confidence = confidence
        self._validate_confidence(
            accumulation_confidence,
            "Accumulation confidence",
        )

        normalized_image, owns_image = self._normalize_image(image)
        try:
            general_detections = self._general_adapter.detect(
                normalized_image,
                confidence,
            )
            general_detected_accumulation = any(
                _normalized_class_name(detection.class_name)
                == _ACCUMULATION_CLASS
                for detection in general_detections
            )
            if general_detected_accumulation:
                return general_detections

            specialist_detections = self._specialist_adapter.detect(
                normalized_image,
                accumulation_confidence,
            )
            specialist_accumulation_detections = [
                Detection(
                    class_name=_ACCUMULATION_CLASS,
                    confidence=detection.confidence,
                    bbox=detection.bbox,
                )
                for detection in specialist_detections
                if _normalized_class_name(detection.class_name)
                == _SPECIALIST_CLASS
            ]
            return general_detections + specialist_accumulation_detections
        except (DetectionError, ConfigurationError):
            raise
        except Exception as error:
            raise DetectionError(f"Ensemble inference failed: {error}") from error
        finally:
            if owns_image:
                normalized_image.close()

    @staticmethod
    def _validate_confidence(value: float, label: str) -> None:
        if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
            raise ConfigurationError(f"{label} must be between 0.0 and 1.0.")

    @staticmethod
    def _normalize_image(
        image: str | Path | Image.Image,
    ) -> tuple[Image.Image, bool]:
        if isinstance(image, Image.Image):
            if image.mode == "RGB":
                return image, False
            return image.convert("RGB"), True

        try:
            with Image.open(image) as opened_image:
                return opened_image.convert("RGB"), True
        except (OSError, ValueError) as error:
            raise DetectionError(f"Unable to read image: {error}") from error


def _normalized_class_name(name: str) -> str:
    """Normalize labels for fallback decisions without changing public output."""

    return " ".join(name.strip().lower().replace("_", " ").split())
