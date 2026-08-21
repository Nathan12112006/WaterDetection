from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    xyxy: tuple[int, int, int, int]


class DetectionModel(Protocol):
    def predict(self, frame: np.ndarray) -> list[Detection]: ...

    def close(self) -> None: ...
