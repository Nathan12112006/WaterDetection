"""Run the fixed general, optional last, and accumulation Torch models."""

from __future__ import annotations

from threading import Lock
from typing import Literal, Protocol

from PIL import Image

from config.settings import ModelSelection
from models import Detection
from service.model_manifest import (
    MODEL_PATHS,
    canonical_class_name,
    validate_loaded_class_names,
    verify_runtime_models,
)
from utils import ConfigurationError, DetectionError, ModelManifestError

ModelRole = Literal["general", "last", "specialist"]
ImageInput = str | Image.Image

_ACCUMULATION_CLASS = "water accumulation"
_SPECIALIST_CLASS = "water damage"
_REQUIRED_MODEL_ROLES: tuple[ModelRole, ...] = ("general", "specialist")
_MODEL_ROLE_FOR_SELECTION: dict[ModelSelection, ModelRole] = {
    "water_detection": "general",
    "water_detection_last": "last",
}
_SUPPORTED_MODEL_SELECTIONS: frozenset[str] = frozenset(
    (*_MODEL_ROLE_FOR_SELECTION, "water_accumulation")
)


class _InferenceAdapter(Protocol):
    def detect(
        self,
        image: Image.Image,
        confidence: float,
    ) -> list[Detection]: ...


def _extract_loaded_class_map(adapter: object) -> object:
    """Read an indexed class map from a loaded Torch adapter."""

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


def _create_adapter(
    role: ModelRole,
    device: str,
) -> _InferenceAdapter:
    """Load one fixed Torch model and validate its embedded class map."""

    from service.backends.torch_backend import TorchBackend

    adapter = TorchBackend(model_path=str(MODEL_PATHS[role]), device=device)
    validate_loaded_class_names(role, _extract_loaded_class_map(adapter))
    return adapter


class DetectionRuntime:
    """Expose one fixed-model detection interface with verified model reuse."""

    def __init__(self, *, device: str = "cpu") -> None:
        if not isinstance(device, str) or not device.strip():
            raise ConfigurationError("Device must not be empty.")

        # This checks the two required paths and never consults
        # model-manifest.json. The optional last checkpoint is loaded lazily
        # when selected.
        verify_runtime_models()
        self.device = device
        self._adapters: dict[ModelRole, _InferenceAdapter] = {}
        self._load_locks: dict[ModelRole, Lock] = {
            "general": Lock(),
            "last": Lock(),
            "specialist": Lock(),
        }
        # Load and validate required models before the runtime becomes
        # available. The optional last checkpoint is loaded on first use.
        for role in _REQUIRED_MODEL_ROLES:
            try:
                self._get_adapter(role)
            except (DetectionError, ModelManifestError):
                raise
            except Exception as error:
                raise DetectionError(
                    f"{role} model loading failed: {error}"
                ) from error

    def detect(
        self,
        image: ImageInput,
        *,
        model: ModelSelection = "water_detection",
        confidence: float = 0.25,
        accumulation_confidence: float | None = None,
        class_confidences: dict[str, float] | None = None,
    ) -> list[Detection]:
        """Return detections from exactly one selected fixed model."""

        if model not in _SUPPORTED_MODEL_SELECTIONS:
            raise ConfigurationError(
                "Model must be water_accumulation, water_detection, "
                "or water_detection_last."
            )
        self._validate_confidence(confidence, "Confidence")
        if accumulation_confidence is None:
            accumulation_confidence = confidence
        self._validate_confidence(
            accumulation_confidence,
            "Accumulation confidence",
        )

        normalized_image, owns_image = self._normalize_image(image)
        try:
            if model == "water_accumulation":
                return [
                    Detection(
                        class_name=_ACCUMULATION_CLASS,
                        confidence=detection.confidence,
                        bbox=detection.bbox,
                    )
                    for detection in self._detect_with_adapter(
                        "specialist",
                        normalized_image,
                        accumulation_confidence,
                    )
                    if canonical_class_name(detection.class_name)
                    == _SPECIALIST_CLASS
                ]

            role = _MODEL_ROLE_FOR_SELECTION[model]
            return self._detect_with_adapter(
                role,
                normalized_image,
                confidence,
                class_confidences=class_confidences,
            )
        finally:
            if owns_image:
                normalized_image.close()

    def _detect_with_adapter(
        self,
        role: ModelRole,
        image: Image.Image,
        confidence: float,
        class_confidences: dict[str, float] | None = None,
    ) -> list[Detection]:
        try:
            adapter = self._get_adapter(role)
            detections = adapter.detect(image=image, confidence=confidence)
            if class_confidences is None:
                return detections
            return [
                detection
                for detection in detections
                if detection.confidence
                >= class_confidences.get(detection.class_name, confidence)
            ]
        except DetectionError:
            raise
        except Exception as error:
            raise DetectionError(f"{role} model inference failed: {error}") from error

    @staticmethod
    def _validate_confidence(value: float, label: str) -> None:
        if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
            raise ConfigurationError(f"{label} must be between 0.0 and 1.0.")

    @staticmethod
    def _normalize_image(image: ImageInput) -> tuple[Image.Image, bool]:
        if isinstance(image, Image.Image):
            if image.mode == "RGB":
                return image, False
            return image.convert("RGB"), True

        try:
            with Image.open(image) as opened_image:
                return opened_image.convert("RGB"), True
        except (OSError, ValueError) as error:
            raise DetectionError(f"Unable to read image: {error}") from error

    def _get_adapter(self, role: ModelRole) -> _InferenceAdapter:
        adapter = self._adapters.get(role)
        if adapter is not None:
            return adapter

        with self._load_locks[role]:
            adapter = self._adapters.get(role)
            if adapter is None:
                adapter = _create_adapter(role, self.device)
                self._adapters[role] = adapter
            return adapter
