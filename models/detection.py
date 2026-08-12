"""Represent one object detected in an image."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Detection:
    """A serializable object-detection result.

    Attributes:
        class_name: Human-readable name of the detected object class.
        confidence: Model confidence for the detection.
        bbox: Bounding box coordinates in ``[x1, y1, x2, y2]`` order.
    """

    class_name: str
    confidence: float
    bbox: list[float]

    def to_dict(self) -> dict[str, Any]:
        """Convert the detection to the public JSON response structure.

        Returns:
            A dictionary with ``class``, ``confidence``, and ``bbox`` fields.
        """
        return {
            "class": self.class_name,
            "confidence": self.confidence,
            "bbox": self.bbox,
        }
