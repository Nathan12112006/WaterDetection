from .detection_service import (
    DetectionPersistence,
    DetectionRecord,
    ingest_detection_records,
    register_model_version,
)

__all__ = ["DetectionPersistence", "DetectionRecord", "ingest_detection_records", "register_model_version"]
