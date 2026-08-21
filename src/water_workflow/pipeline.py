from __future__ import annotations

import cv2

from .config import AppConfig
from .models import DetectionModel
from .video import FramePacket, VideoSource


class Workflow:
    def __init__(self, config: AppConfig, source: VideoSource, model: DetectionModel) -> None:
        self.config = config
        self.source = source
        self.model = model

    def run(self) -> None:
        try:
            for packet in self.source:
                detections = self.model.predict(packet.frame)
                annotated = self._annotate(packet, detections)
                if self.config.display.enabled:
                    cv2.imshow(self.config.display.window_name, annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        finally:
            self.source.close()
            self.model.close()
            cv2.destroyAllWindows()

    def _annotate(self, packet: FramePacket, detections: list) -> object:
        frame = packet.frame.copy()
        if not self.config.display.draw_boxes:
            return frame
        for detection in detections:
            x1, y1, x2, y2 = detection.xyxy
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{detection.label} {detection.confidence:.2f}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return frame
