from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

import cv2
import numpy as np

from water_workflow.config import CameraMonitoringConfig, MonitoringRuntimeConfig, SourceConfig, load_config
from water_workflow.monitoring.buffer import LatestFrameBuffer
from water_workflow.monitoring.engine import MonitoringEngine
from water_workflow.monitoring.scheduler import BranchScheduler, SharedDetectionRunner
from water_workflow.monitoring.types import WorkerState
from water_workflow.monitoring.worker import CameraWorker
from water_workflow.models.base import Detection
from water_workflow.video.types import FramePacket


class CountingModel:
    def __init__(self) -> None:
        self.calls = 0

    def predict(self, frame):
        self.calls += 1
        return [Detection("water_drop", 0.9, (1, 1, 4, 4))]

    def close(self):
        return None


class OneFrameSource:
    is_live = False

    def open(self):
        return None

    def read(self):
        if getattr(self, "done", False):
            return None
        self.done = True
        return FramePacket(np.zeros((8, 8, 3), dtype=np.uint8), 1, 1.0, camera_id="slow")

    def close(self):
        return None


class SlowProcessor:
    def process(self, packet):
        time.sleep(0.02)
        from water_workflow.monitoring.types import FrameProcessingResult

        return FrameProcessingResult(packet)


class MonitoringRuntimeTests(unittest.TestCase):
    def test_latest_frame_buffer_drops_oldest(self) -> None:
        buffer = LatestFrameBuffer(1)
        frame = np.zeros((2, 2, 3), dtype=np.uint8)
        buffer.put(FramePacket(frame, 1, 1.0))
        buffer.put(FramePacket(frame, 2, 2.0))
        self.assertEqual(buffer.dropped, 1)
        self.assertEqual(buffer.get().frame_index, 2)

    def test_legacy_config_derives_one_monitoring_camera(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text("video:\n  source: camera\n  camera_index: 3\n", encoding="utf-8")
            config = load_config(path)
        from water_workflow.config import effective_monitoring_cameras

        cameras = effective_monitoring_cameras(config)
        self.assertEqual(len(cameras), 1)
        self.assertEqual(cameras[0].camera_id, "camera-3")

    def test_scheduler_processes_full_frame(self) -> None:
        model = CountingModel()
        from water_workflow.config import BranchesConfig, MotionCropBranchConfig, ScheduledBranchConfig

        branches = BranchesConfig(
            full_frame_detection=ScheduledBranchConfig(enabled=True, interval_ms=1),
            motion_crop_detection=MotionCropBranchConfig(enabled=False),
        )
        scheduler = BranchScheduler("cam-1", branches, SharedDetectionRunner(model))
        result = scheduler.process(FramePacket(np.zeros((8, 8, 3), dtype=np.uint8), 1, 1.0, camera_id="cam-1"))
        self.assertEqual(model.calls, 1)
        self.assertEqual(result.detections[0].camera_id, "cam-1")

    def test_multi_camera_file_workers_process_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video_path = Path(directory) / "demo.avi"
            writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (16, 16))
            for _ in range(5):
                writer.write(np.zeros((16, 16, 3), dtype=np.uint8))
            writer.release()
            config_path = Path(directory) / "monitoring.yaml"
            config_path.write_text(
                f"monitoring:\n  enabled: true\n  cameras:\n    - camera_id: file-1\n      source: {{type: file, path: {video_path.as_posix()}}}\n    - camera_id: file-2\n      source: {{type: file, path: {video_path.as_posix()}}}\ndisplay: {{enabled: false}}\n",
                encoding="utf-8",
            )
            engine = MonitoringEngine(str(config_path))
            try:
                engine.start()
                deadline = time.time() + 3
                while time.time() < deadline and not all(item.frames_processed > 0 for item in engine.status().values()):
                    time.sleep(0.05)
                self.assertTrue(all(item.frames_processed > 0 for item in engine.status().values()))
            finally:
                engine.close()

    def test_inference_timeout_is_visible_in_worker_status(self) -> None:
        worker = CameraWorker(
            CameraMonitoringConfig(camera_id="slow", source=SourceConfig(type="file", path="unused")),
            OneFrameSource(),
            SlowProcessor(),
            sink=type("Sink", (), {"publish": lambda self, result: None, "close": lambda self: None})(),
            runtime=MonitoringRuntimeConfig(inference_timeout_ms=1),
        )
        worker.start()
        deadline = time.time() + 1
        while time.time() < deadline and worker.snapshot().frames_processed == 0:
            time.sleep(0.01)
        snapshot = worker.snapshot()
        worker.stop()
        self.assertEqual(snapshot.state, WorkerState.DEGRADED)
        self.assertEqual(snapshot.inference_timeout_count, 1)


if __name__ == "__main__":
    unittest.main()
