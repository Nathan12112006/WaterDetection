from __future__ import annotations

import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

from ..config import SourceConfig
from ..video.types import FramePacket


class FileFrameSource:
    is_live = False

    def __init__(self, camera_id: str, config: SourceConfig) -> None:
        self.camera_id = camera_id
        self.config = config
        self.capture: cv2.VideoCapture | None = None
        self.frame_index = 0
        self._next_frame_at = 0.0

    def open(self) -> None:
        path = Path(self.config.path)
        if not path.is_file():
            raise FileNotFoundError(f"Video file does not exist: {path}")
        self.capture = cv2.VideoCapture(str(path))
        if not self.capture.isOpened():
            raise RuntimeError(f"Unable to open video file: {path}")
        self.frame_index = 0
        self._next_frame_at = time.monotonic()

    def read(self) -> FramePacket | None:
        if self.capture is None:
            raise RuntimeError("FileFrameSource is not open")
        ok, frame = self.capture.read()
        if not ok and self.config.loop:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_index = 0
            ok, frame = self.capture.read()
        if not ok:
            return None
        if self.config.fps_limit:
            delay = self._next_frame_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self._next_frame_at = max(
                self._next_frame_at + 1.0 / self.config.fps_limit,
                time.monotonic(),
            )
        timestamp_ms = self.capture.get(cv2.CAP_PROP_POS_MSEC)
        timestamp = timestamp_ms / 1000.0 if timestamp_ms > 0 else float(self.frame_index)
        now = datetime.now(timezone.utc)
        packet = FramePacket(
            frame=frame,
            frame_index=self.frame_index,
            timestamp_seconds=timestamp,
            camera_id=self.camera_id,
            captured_at=now,
        )
        self.frame_index += 1
        return packet

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None


class CameraFrameSource:
    is_live = True

    def __init__(self, camera_id: str, config: SourceConfig) -> None:
        self.camera_id = camera_id
        self.config = config
        self.capture: cv2.VideoCapture | None = None
        self.frame_index = 0
        self._closed = False
        self._last_emit_at = 0.0
        self._reconnect_attempts = 0

    def _target(self) -> int | str:
        if self.config.type == "rtsp" or self.config.uri:
            return self.config.uri
        return self.config.camera_index

    def _open_capture(self) -> cv2.VideoCapture:
        target = self._target()
        if isinstance(target, int) and platform.system() == "Windows":
            capture = cv2.VideoCapture(target, cv2.CAP_DSHOW)
        else:
            capture = cv2.VideoCapture(target)
        if self.config.width:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        if self.config.height:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        return capture

    def open(self) -> None:
        self._closed = False
        self.capture = self._open_capture()
        if not self.capture.isOpened():
            self.capture.release()
            self.capture = None
            raise RuntimeError(f"Unable to open camera source: {self._target()}")
        self.frame_index = 0
        self._reconnect_attempts = 0

    def _reconnect(self) -> bool:
        if self._closed or not self.config.reconnect:
            return False
        if self.config.max_reconnect_attempts and self._reconnect_attempts >= self.config.max_reconnect_attempts:
            return False
        self._reconnect_attempts += 1
        if self.capture is not None:
            self.capture.release()
        if self.config.reconnect_delay_seconds:
            time.sleep(self.config.reconnect_delay_seconds)
        if self._closed:
            return False
        self.capture = self._open_capture()
        return self.capture.isOpened()

    def read(self) -> FramePacket | None:
        while not self._closed:
            if self.capture is None:
                return None
            ok, frame = self.capture.read()
            if not ok:
                if self._reconnect():
                    continue
                return None
            self._reconnect_attempts = 0
            if self.config.fps_limit:
                interval = 1.0 / self.config.fps_limit
                now_mono = time.monotonic()
                if now_mono - self._last_emit_at < interval:
                    continue
                self._last_emit_at = now_mono
            now = datetime.now(timezone.utc)
            packet = FramePacket(
                frame=frame,
                frame_index=self.frame_index,
                timestamp_seconds=now.timestamp(),
                camera_id=self.camera_id,
                captured_at=now,
            )
            self.frame_index += 1
            return packet
        return None

    def close(self) -> None:
        self._closed = True
        if self.capture is not None:
            self.capture.release()
            self.capture = None


def create_frame_source(camera_id: str, config: SourceConfig):
    if config.type == "file":
        return FileFrameSource(camera_id, config)
    if config.type in {"camera", "rtsp"}:
        return CameraFrameSource(camera_id, config)
    raise ValueError(f"Unsupported source type: {config.type}")
