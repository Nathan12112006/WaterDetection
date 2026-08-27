from __future__ import annotations

from ..config import AppConfig, load_config
from .supervisor import MonitoringSupervisor


class MonitoringEngine:
    """Small external interface over multi-camera monitoring."""

    def __init__(self, config: AppConfig | str = "configs/default.yaml") -> None:
        self.config = load_config(config) if isinstance(config, (str, bytes)) else config
        self.supervisor = MonitoringSupervisor(self.config)

    def start(self, camera_id: str | None = None) -> None:
        self.supervisor.start(camera_id)

    def stop(self, camera_id: str | None = None) -> None:
        self.supervisor.stop(camera_id)

    def restart(self, camera_id: str) -> None:
        self.supervisor.restart(camera_id)

    def status(self, camera_id: str | None = None):
        return self.supervisor.status(camera_id)

    def service_state(self):
        return self.supervisor.service_state()

    def latest_result(self, camera_id: str):
        return self.supervisor.latest_result(camera_id)

    def events(self, camera_id: str | None = None):
        return self.supervisor.events(camera_id)

    def close(self) -> None:
        self.supervisor.close()
