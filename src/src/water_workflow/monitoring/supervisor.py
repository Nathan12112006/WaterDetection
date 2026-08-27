from __future__ import annotations

from dataclasses import dataclass

from ..config import AppConfig, effective_monitoring_cameras
from ..models.factory import create_model, create_segmentation_model
from .scheduler import BranchScheduler, SharedDetectionRunner, SharedSegmentationRunner
from .sources import create_frame_source
from .events import VisionEventStateMachine
from .types import FrameProcessingResult, ServiceState, VisionEvent, WorkerState
from .worker import CameraWorker


class MemoryResultSink:
    def __init__(self, max_items: int = 20) -> None:
        self.max_items = max_items
        self.items: list[FrameProcessingResult] = []

    def publish(self, result: FrameProcessingResult) -> None:
        self.items.append(result)
        if len(self.items) > self.max_items:
            del self.items[:-self.max_items]

    def close(self) -> None:
        return None

    def latest(self) -> FrameProcessingResult | None:
        return self.items[-1] if self.items else None


class MemoryEventSink:
    def __init__(self) -> None:
        self.items: list[VisionEvent] = []

    def publish(self, event: VisionEvent) -> None:
        self.items.append(event)

    def close(self) -> None:
        return None


@dataclass
class ManagedWorker:
    worker: CameraWorker
    sink: MemoryResultSink
    event_sink: MemoryEventSink


class MonitoringSupervisor:
    def __init__(self, config: AppConfig, sink_factory=None) -> None:
        self.config = config
        self._workers: dict[str, ManagedWorker] = {}
        self._detector = SharedDetectionRunner(create_model(config.models.detector), config.models.detector.backend)
        self._segmenter = None
        if config.monitoring.branches.water_surface_segmentation.enabled:
            self._segmenter = SharedSegmentationRunner(
                create_segmentation_model(config.models.water_surface_seg),
                config.models.water_surface_seg.backend,
            )
        sink_factory = sink_factory or (lambda camera_id: MemoryResultSink())
        for camera in effective_monitoring_cameras(config):
            sink = sink_factory(camera.camera_id)
            event_sink = MemoryEventSink()
            source = create_frame_source(camera.camera_id, camera.source)
            processor = BranchScheduler(
                camera.camera_id,
                config.monitoring.branches,
                self._detector,
                segmenter=self._segmenter,
                risk_regions=camera.risk_regions,
                draw_annotations=config.display.draw_boxes,
            )
            self._workers[camera.camera_id] = ManagedWorker(
                CameraWorker(
                    config=camera,
                    source=source,
                    processor=processor,
                    sink=sink,
                    runtime=config.monitoring.runtime,
                    event_state_machine=VisionEventStateMachine(
                        camera.camera_id,
                        config.monitoring.events,
                    ),
                    event_sink=event_sink,
                ),
                sink,
                event_sink,
            )

    def start(self, camera_id: str | None = None) -> None:
        for key, managed in self._workers.items():
            if camera_id is None or key == camera_id:
                managed.worker.start()

    def stop(self, camera_id: str | None = None) -> None:
        for key, managed in self._workers.items():
            if camera_id is None or key == camera_id:
                managed.worker.stop()

    def restart(self, camera_id: str) -> None:
        self.stop(camera_id)
        self.start(camera_id)

    def status(self, camera_id: str | None = None):
        if camera_id is not None:
            managed = self._workers.get(camera_id)
            if managed is None:
                raise KeyError(camera_id)
            return managed.worker.snapshot()
        return {key: managed.worker.snapshot() for key, managed in self._workers.items()}

    def service_state(self) -> ServiceState:
        snapshots = list(self.status().values())
        if not snapshots or all(item.state in {WorkerState.CONFIGURED, WorkerState.STOPPED} for item in snapshots):
            return ServiceState.NOT_READY
        if all(item.state == WorkerState.HEALTHY for item in snapshots):
            return ServiceState.READY
        return ServiceState.DEGRADED

    def latest_result(self, camera_id: str) -> FrameProcessingResult | None:
        managed = self._workers.get(camera_id)
        if managed is None:
            raise KeyError(camera_id)
        return managed.sink.latest()

    def events(self, camera_id: str | None = None):
        if camera_id is not None:
            managed = self._workers.get(camera_id)
            if managed is None:
                raise KeyError(camera_id)
            return list(managed.event_sink.items)
        return {key: list(managed.event_sink.items) for key, managed in self._workers.items()}

    def close(self) -> None:
        self.stop()
        for managed in self._workers.values():
            managed.sink.close()
        self._detector.close()
        if self._segmenter is not None:
            self._segmenter.close()
