from __future__ import annotations

import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from water_workflow.database.base import Base
from water_workflow.database.models import VisionEventOutbox
from water_workflow.monitoring.persistence import OutboxDispatcher, SqlAlchemyVisionEventSink
from water_workflow.monitoring.types import VisionEvent


class OutboxDispatcherTests(unittest.TestCase):
    def test_success_marks_outbox_published(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        sink = SqlAlchemyVisionEventSink(lambda: Session(engine))
        sink.publish(VisionEvent("evt-2", 1, "confirmed", "pipe_burst", "cam-1", None, datetime.now(timezone.utc), 0.9, ("full_frame_detection",), ("v1",), "cfg"))
        sent: list[dict] = []
        dispatcher = OutboxDispatcher(lambda: Session(engine), sent.append)
        self.assertEqual(dispatcher.dispatch_available(), 1)
        self.assertEqual(len(sent), 1)
        with Session(engine) as session:
            row = session.scalar(select(VisionEventOutbox))
            self.assertEqual(row.status, "published")

    def test_failure_is_returned_to_pending(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        sink = SqlAlchemyVisionEventSink(lambda: Session(engine))
        sink.publish(VisionEvent("evt-3", 1, "confirmed", "water_drop", "cam-1", None, datetime.now(timezone.utc), 0.9, (), (), "cfg"))
        dispatcher = OutboxDispatcher(lambda: Session(engine), lambda payload: (_ for _ in ()).throw(RuntimeError("backend down")), retry_delay_seconds=5)
        self.assertTrue(dispatcher.dispatch_once())
        with Session(engine) as session:
            row = session.scalar(select(VisionEventOutbox))
            self.assertEqual(row.status, "pending")
            self.assertEqual(row.attempts, 1)
            self.assertEqual(row.last_error, "backend down")


if __name__ == "__main__":
    unittest.main()
