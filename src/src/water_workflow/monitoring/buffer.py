from __future__ import annotations

from collections import deque
from threading import Condition

from ..video.types import FramePacket


class LatestFrameBuffer:
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._frames: deque[FramePacket] = deque()
        self._condition = Condition()
        self._closed = False
        self.dropped = 0

    def put(self, packet: FramePacket) -> None:
        with self._condition:
            if self._closed:
                return
            if len(self._frames) == self.capacity:
                self._frames.popleft()
                self.dropped += 1
            self._frames.append(packet)
            self._condition.notify()

    def get(self, timeout: float | None = None) -> FramePacket | None:
        with self._condition:
            if not self._frames and not self._closed:
                self._condition.wait(timeout)
            if self._frames:
                return self._frames.popleft()
            return None

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    @property
    def closed(self) -> bool:
        with self._condition:
            return self._closed

    def __len__(self) -> int:
        with self._condition:
            return len(self._frames)
