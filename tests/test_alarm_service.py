from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from water_workflow.api.schemas import DetectionEventCreate, DetectionInput
from water_workflow.api.services import ingest_detection_event
from water_workflow.config import AlarmConfig
from water_workflow.database.base import Base
from water_workflow.database.models import Alarm, Camera, DetectionEvent


class AlarmServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        camera = Camera(camera_code="TEST-01", camera_name="Test Camera", area_name="Test Area", source_type="file")
        self.db.add(camera)
        self.db.commit()
        self.camera_id = camera.id

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_event_creates_and_then_updates_one_active_alarm(self) -> None:
        payload = DetectionEventCreate(camera_id=self.camera_id, frame_index=1, detections=[DetectionInput(label="water drop", confidence=0.8, bbox=[1, 2, 30, 40])])
        first_event_ids, first_alarm_ids = ingest_detection_event(self.db, payload)
        second_event_ids, second_alarm_ids = ingest_detection_event(self.db, payload)
        alarms = list(self.db.scalars(select(Alarm)).all())
        events = list(self.db.scalars(select(DetectionEvent)).all())
        self.assertEqual(len(first_event_ids), 1)
        self.assertEqual(len(second_event_ids), 1)
        self.assertEqual(first_alarm_ids, second_alarm_ids)
        self.assertEqual(len(events), 2)
        self.assertEqual(len(alarms), 1)
        self.assertEqual(alarms[0].frame_count, 2)

    def test_pipe_burst_is_critical(self) -> None:
        payload = DetectionEventCreate(camera_id=self.camera_id, detections=[DetectionInput(label="pipe burst", confidence=0.9, bbox=[1, 2, 30, 40])])
        _, alarm_ids = ingest_detection_event(self.db, payload)
        alarm = self.db.get(Alarm, alarm_ids[0])
        self.assertEqual(alarm.severity, "critical")

    def test_accumulation_requires_three_consecutive_frames(self) -> None:
        def submit(frame_index: int):
            return ingest_detection_event(
                self.db,
                DetectionEventCreate(
                    camera_id=self.camera_id,
                    frame_index=frame_index,
                    detections=[DetectionInput(label="accumulate", confidence=0.9, bbox=[1, 2, 30, 40])],
                ),
            )

        _, alarm_ids = submit(10)
        alarm = self.db.get(Alarm, alarm_ids[0])
        self.assertEqual(alarm.status, "candidate")
        self.assertEqual(alarm.consecutive_count, 1)

        submit(11)
        self.assertEqual(self.db.get(Alarm, alarm.id).status, "candidate")

        submit(12)
        alarm = self.db.get(Alarm, alarm.id)
        self.assertEqual(alarm.status, "active")
        self.assertEqual(alarm.consecutive_count, 3)
        self.assertEqual(alarm.required_confirmations, 3)

    def test_non_consecutive_frames_reset_candidate_streak(self) -> None:
        config = AlarmConfig(confirmation_frames=3)
        from water_workflow.services.detection_service import DetectionRecord, ingest_detection_records

        def submit(frame_index: int):
            return ingest_detection_records(
                self.db,
                self.camera_id,
                [DetectionRecord("pipe burst", 0.9, (1, 2, 30, 40))],
                frame_index=frame_index,
                alarm_config=config,
            )

        _, alarm_ids = submit(1)
        submit(3)
        alarm = self.db.get(Alarm, alarm_ids[0])
        self.assertEqual(alarm.status, "candidate")
        self.assertEqual(alarm.consecutive_count, 1)


if __name__ == "__main__":
    unittest.main()
