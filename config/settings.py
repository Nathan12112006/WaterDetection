import os
from dataclasses import dataclass
from utils import ConfigurationError

ModelSelection = str


@dataclass(frozen=True)
class AppConfig:
    """Immutable settings for one object-detection run.

    Attributes:
        image: Image location passed to the fixed ensemble runtime.
        confidence: Minimum accepted detection confidence from 0.0 to 1.0.
        device: Inference device such as ``cpu``, ``0``, or ``cuda:0``.
    """

    image: str = "test1.jpg"
    model: ModelSelection = "water_detection"
    confidence: float = 0.25
    device: str = "cpu"

    def __post_init__(self) -> None:
        """Validate configuration immediately after construction.

        Raises:
            ConfigurationError: If a required string is empty or confidence is
                outside the supported range.
        """
        if not self.image.strip():
            raise ConfigurationError("Image must not be empty.")
        if self.model not in {"water_accumulation", "water_detection"}:
            raise ConfigurationError(
                "Model must be water_accumulation or water_detection."
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ConfigurationError("Confidence must be between 0.0 and 1.0.")
        if not self.device.strip():
            raise ConfigurationError("Device must not be empty.")


@dataclass(frozen=True)
class ServiceConfig:
    """Server-owned runtime and resource limits.

    These settings are read once when FastAPI starts. Detection callers cannot
    override them.
    """

    device: str = "cpu"
    max_upload_bytes: int = 20 * 1024 * 1024
    max_image_pixels: int = 25_000_000
    request_timeout_seconds: float = 120.0
    max_concurrent_detections: int = 2

    def __post_init__(self) -> None:
        if not self.device.strip():
            raise ConfigurationError("YOLO_DEVICE must not be empty.")
        if self.max_upload_bytes < 1:
            raise ConfigurationError("YOLO_MAX_UPLOAD_BYTES must be positive.")
        if self.max_image_pixels < 1:
            raise ConfigurationError("YOLO_MAX_IMAGE_PIXELS must be positive.")
        if self.request_timeout_seconds <= 0:
            raise ConfigurationError(
                "YOLO_REQUEST_TIMEOUT_SECONDS must be positive."
            )
        if self.max_concurrent_detections < 1:
            raise ConfigurationError(
                "YOLO_MAX_CONCURRENT_DETECTIONS must be positive."
            )

    @classmethod
    def from_environment(cls) -> "ServiceConfig":
        """Load validated server settings from environment variables."""

        return cls(
            device=os.getenv("YOLO_DEVICE", "cpu"),
            max_upload_bytes=_environment_int(
                "YOLO_MAX_UPLOAD_BYTES",
                cls.max_upload_bytes,
            ),
            max_image_pixels=_environment_int(
                "YOLO_MAX_IMAGE_PIXELS",
                cls.max_image_pixels,
            ),
            request_timeout_seconds=_environment_float(
                "YOLO_REQUEST_TIMEOUT_SECONDS",
                cls.request_timeout_seconds,
            ),
            max_concurrent_detections=_environment_int(
                "YOLO_MAX_CONCURRENT_DETECTIONS",
                cls.max_concurrent_detections,
            ),
        )


def _environment_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer.") from error


def _environment_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a number.") from error
