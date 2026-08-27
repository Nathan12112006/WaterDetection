from __future__ import annotations

import unittest

import numpy as np
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from water_workflow.config import AppConfig, DatabaseConfig, DisplayConfig, ModelConfig, VideoConfig
from water_workflow.database.base import Base
from water_workflow.database.models import Alarm, Camera, ModelVersion
from water_workflow.models.base import Detection
from water_workflow.pipeline import Workflow
from water_workflow.video.types import FramePacket


class OneFrameSource:
    def __iter__(self):
        yield FramePacket(np.zeros((8, 8, 3), dtype=np.uint8), 7, 1.5)

    def close(self):
        return None


class OneDetectionModel:
    def predict(self, frame):
        return [Detection("water drop", 0.88, (1, 2, 5, 6))]

    def close(self):
        return None


class WorkflowPersistenceTests(unittest.TestCase):
    def test_workflow_writes_detection_and_alarm(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        session_factory = lambda: Session(engine)
        with session_factory() as db:
            camera = Camera(camera_code="WF-TEST", camera_name="Workflow Test", area_name="Test", source_type="file")
            db.add(camera)
            db.commit()
            camera_id = camera.id

        import water_workflow.pipeline as pipeline_module
        original_factory = pipeline_module.get_session_factory
        pipeline_module.get_session_factory = lambda: session_factory
        try:
            config = AppConfig(
                video=VideoConfig(source="file"),
                model=ModelConfig(backend="noop"),
                display=DisplayConfig(enabled=False),
                database=DatabaseConfig(enabled=True, camera_id=camera_id),
            )
            Workflow(config, OneFrameSource(), OneDetectionModel()).run()
        finally:
            pipeline_module.get_session_factory = original_factory

        with session_factory() as db:
            self.assertEqual(len(db.scalars(select(ModelVersion)).all()), 1)
            self.assertEqual(len(db.scalars(select(Alarm)).all()), 1)


if __name__ == "__main__":
    unittest.main()
