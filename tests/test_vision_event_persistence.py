from __future__ import annotations

import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from water_workflow.database.base import Base
from water_workflow.database.models import VisionEventOutbox, VisionEventRecord
from water_workflow.monitoring.persistence import SqlAlchemyVisionEventSink
from water_workflow.monitoring.types import VisionEvent


class VisionEventPersistenceTests(unittest.TestCase):
    def test_event_and_outbox_are_written_atomically_and_idempotently(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        sink = SqlAlchemyVisionEventSink(lambda: Session(engine))
        event = VisionEvent(
            event_id="evt-1",
            event_revision=1,
            event_status="confirmed",
            event_type="water_drop",
            camera_id="cam-1",
            risk_region_id=None,
            occurred_at=datetime.now(timezone.utc),
            confidence=0.91,
            source_branches=("full_frame_detection",),
            model_versions=("detector-v1",),
            config_revision="cfg-1",
            bbox=(1, 2, 3, 4),
        )
        sink.publish(event)
        sink.publish(event)
        with Session(engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(VisionEventRecord)), 1)
            self.assertEqual(session.scalar(select(func.count()).select_from(VisionEventOutbox)), 1)


if __name__ == "__main__":
    unittest.main()
