"""Define JSON schemas exposed by the HTTP API."""

from pydantic import BaseModel, ConfigDict, Field


class DetectionResponse(BaseModel):
    """JSON representation of one detected object.

    Attributes:
        class_name: Human-readable detected class, serialized as ``class``.
        confidence: Detection confidence from 0.0 to 1.0.
        bbox: Bounding box in ``[x1, y1, x2, y2]`` pixel coordinates.
    """

    model_config = ConfigDict(populate_by_name=True)

    class_name: str = Field(alias="class", min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float] = Field(min_length=4, max_length=4)
