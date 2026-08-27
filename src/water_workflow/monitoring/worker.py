from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from ..config import CameraMonitoringConfig, MonitoringRuntimeConfig
from .buffer import LatestFrameBuffer
from .events import VisionEventStateMachine
from .scheduler import BranchScheduler
from .types import (
    FrameResultSink,
    FrameSource,
    WorkerSnapshot,
    WorkerState,
    VisionEventSink,
)


class CameraWorker:
    """One camera lifecycle composed from a source, processor and result sink."""

    def __init__(
        self,
        config: CameraMonitoringConfig,
        source: FrameSource,
        processor: BranchScheduler,
        sink: FrameResultSink,
        runtime: MonitoringRuntimeConfig,
        event_state_machine: VisionEventStateMachine | None = None,
        event_sink: VisionEventSink | None = None,
    ) -> None:
        self.config = config
        self.source = source
        self.processor = processor
        self.sink = sink
        self.event_state_machine = event_state_machine
        self.event_sink = event_sink
        self.runtime = runtime
        self.buffer = LatestFrameBuffer(runtime.queue_size)
        self.state = WorkerState.CONFIGURED
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at: datetime | None = None
        self._last_frame_at: datetime | None = None
        self._last_inference_at: datetime | None = None
        self._frames_received = 0
        self._frames_processed = 0
        self._last_error: str | None = None
        self._source_thread: threading.Thread | None = None
        self._last_inference_latency_ms: float | None = None
        self._inference_timeout_count = 0

    @property
    def camera_id(self) -> str:
        return self.config.camera_id

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.buffer = LatestFrameBuffer(self.runtime.queue_size)
        self.state = WorkerState.WARMING_UP
        self._started_at = datetime.now(timezone.utc)
        self._last_error = None
        self._source_thread = threading.Thread(target=self._read_loop, name=f"source-{self.camera_id}", daemon=True)
        self._thread = threading.Thread(target=self._process_loop, name=f"worker-{self.camera_id}", daemon=True)
        self._source_thread.start()
        self._thread.start()

    def _read_loop(self) -> None:
        try:
            self.source.open()
            while not self._stop.is_set():
                packet = self.source.read()
                if packet is None:
                    if self.source.is_live:
                        self.state = WorkerState.OFFLINE
                        self._last_error = "video source returned no frame"
                    break
                self._frames_received += 1
                self._last_frame_at = packet.captured_at or datetime.now(timezone.utc)
                self.buffer.put(packet)
        except Exception as exc:
            self.state = WorkerState.OFFLINE
            self._last_error = str(exc)
        finally:
            self.buffer.close()

    def _process_loop(self) -> None:
        processed_once = False
        warmup_deadline = time.monotonic() + self.runtime.warmup_timeout_seconds
        try:
            while not self._stop.is_set():
                packet = self.buffer.get(timeout=0.2)
                if packet is None:
                    if self.buffer.closed:
                        break
                    if not processed_once and time.monotonic() >= warmup_deadline:
                        self.state = WorkerState.DEGRADED
                        self._last_error = "warmup timed out before first processed frame"
                        break
                    continue
                if packet.captured_at is not None:
                    age_ms = (datetime.now(timezone.utc) - packet.captured_at).total_seconds() * 1000
                    if age_ms > self.runtime.max_frame_age_ms:
                        continue
                started = time.monotonic()
                result = self.processor.process(packet)
                self._last_inference_latency_ms = (time.monotonic() - started) * 1000
                if self._last_inference_latency_ms > self.runtime.inference_timeout_ms:
                    self._inference_timeout_count += 1
                    self.state = WorkerState.DEGRADED
                    self._last_error = (
                        f"inference exceeded timeout: {self._last_inference_latency_ms:.1f}ms"
                    )
                self.sink.publish(result)
                if self.event_state_machine is not None and self.event_sink is not None:
                    for event in self.event_state_machine.observe(
                        result.detections,
                        result.segments,
                        packet.captured_at,
                    ):
                        self.event_sink.publish(event)
                self._frames_processed += 1
                self._last_inference_at = datetime.now(timezone.utc)
                if not processed_once and self.state != WorkerState.DEGRADED:
                    self.state = WorkerState.HEALTHY
                    processed_once = True
        except Exception as exc:
            self.state = WorkerState.DEGRADED
            self._last_error = str(exc)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self.buffer.close()
        self.source.close()
        if self.event_sink is not None:
            self.event_sink.close()
        for thread in (self._source_thread, self._thread):
            if thread and thread.is_alive():
                thread.join(timeout=timeout)
        if self.state not in {WorkerState.OFFLINE, WorkerState.DEGRADED}:
            self.state = WorkerState.STOPPED

    def snapshot(self) -> WorkerSnapshot:
        last_age = None
        if self._last_frame_at is not None:
            last_age = (datetime.now(timezone.utc) - self._last_frame_at).total_seconds() * 1000
        if (
            self.source.is_live
            and last_age is not None
            and last_age > self.runtime.health_stale_after_ms
            and self.state == WorkerState.HEALTHY
        ):
            self.state = WorkerState.DEGRADED
            self._last_error = f"latest frame is stale: {last_age:.1f}ms"
        return WorkerSnapshot(
            camera_id=self.camera_id,
            state=self.state,
            started_at=self._started_at,
            last_frame_at=self._last_frame_at,
            last_inference_at=self._last_inference_at,
            frames_received=self._frames_received,
            frames_processed=self._frames_processed,
            frames_dropped=self.buffer.dropped,
            last_frame_age_ms=last_age,
            last_error=self._last_error,
            last_inference_latency_ms=self._last_inference_latency_ms,
            inference_timeout_count=self._inference_timeout_count,
        )
