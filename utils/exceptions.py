"""Define exceptions expected and handled by the application."""


class YoloServiceError(Exception):
    """Base exception for expected application failures."""


class ConfigurationError(YoloServiceError):
    """Raised when application configuration is invalid."""


class DetectionError(YoloServiceError):
    """Raised when object detection fails."""


class ModelManifestError(YoloServiceError):
    """Raised when runtime model identity or integrity verification fails."""
