from __future__ import annotations

import numpy as np


class NoOpModel:
    """Pipeline smoke-test model. It intentionally returns no detections."""

    def predict(self, frame: np.ndarray) -> list:
        return []

    def close(self) -> None:
        return None
