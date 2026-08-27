from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Protocol

import numpy as np


@dataclass(frozen=True)
class FramePacket:
    frame: np.ndarray
    frame_index: int
    timestamp_seconds: float
    camera_id: str = ""
    captured_at: datetime | None = None


class VideoSource(Protocol):
    def __iter__(self) -> Iterator[FramePacket]: ...

    def close(self) -> None: ...
