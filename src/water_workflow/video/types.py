from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol

import numpy as np


@dataclass(frozen=True)
class FramePacket:
    frame: np.ndarray
    frame_index: int
    timestamp_seconds: float


class VideoSource(Protocol):
    def __iter__(self) -> Iterator[FramePacket]: ...

    def close(self) -> None: ...
