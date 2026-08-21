from __future__ import annotations

import time
from pathlib import Path
from typing import Iterator

import cv2

from ..config import VideoConfig
from .types import FramePacket


class OpenCVVideoSource:
    """Read frames from a camera index or a local video file."""

    def __init__(self, config: VideoConfig) -> None:
        self.config = config
        self.capture: cv2.VideoCapture | None = None

    def _open(self) -> cv2.VideoCapture:
        if self.config.source == "camera":
            capture = cv2.VideoCapture(self.config.camera_index, cv2.CAP_DSHOW)
        elif self.config.source == "file":
            path = Path(self.config.file_path)
            if not path.is_file():
                raise FileNotFoundError(f"Video file does not exist: {path}")
            capture = cv2.VideoCapture(str(path))
        else:
            raise ValueError("video.source must be 'camera' or 'file'")

        if not capture.isOpened():
            raise RuntimeError(f"Unable to open video source: {self.config.source}")
        if self.config.width:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        if self.config.height:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        return capture

    def __iter__(self) -> Iterator[FramePacket]:
        self.capture = self._open()
        capture_frame_index = 0
        emitted_frame_index = 0
        source_fps = self.capture.get(cv2.CAP_PROP_FPS) or 0.0
        output_fps = self.config.fps_limit or source_fps
        if source_fps > 0 and output_fps > 0:
            output_fps = min(source_fps, output_fps)
        file_frame_step = max(1, round(source_fps / output_fps)) if output_fps > 0 else 1
        file_interval = file_frame_step / source_fps if source_fps > 0 else 0.0
        next_file_frame_at = time.monotonic()
        last_camera_emit = 0.0
        while True:
            ok, frame = self.capture.read()
            if not ok:
                if self.config.source == "file" and self.config.loop_file:
                    self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    capture_frame_index = 0
                    emitted_frame_index = 0
                    next_file_frame_at = time.monotonic()
                    continue
                break

            if self.config.source == "file" and capture_frame_index % file_frame_step != 0:
                capture_frame_index += 1
                continue

            if self.config.source == "camera" and self.config.fps_limit and self.config.fps_limit > 0:
                interval = 1.0 / self.config.fps_limit
                now = time.monotonic()
                if now - last_camera_emit < interval:
                    continue
                last_camera_emit = now

            if self.config.source == "file" and file_interval > 0:
                delay = next_file_frame_at - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                next_file_frame_at = max(next_file_frame_at + file_interval, time.monotonic())

            timestamp_ms = self.capture.get(cv2.CAP_PROP_POS_MSEC)
            timestamp = timestamp_ms / 1000.0 if timestamp_ms > 0 else time.monotonic()
            yield FramePacket(frame=frame, frame_index=emitted_frame_index, timestamp_seconds=timestamp)
            emitted_frame_index += 1
            capture_frame_index += 1

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
