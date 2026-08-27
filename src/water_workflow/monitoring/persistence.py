from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.models import VisionEventOutbox, VisionEventRecord
from .types import VisionEvent, VisionEventSink


def _naive_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def event_payload(event: VisionEvent) -> dict:
    payload = asdict(event)
    payload["occurred_at"] = event.occurred_at.astimezone(timezone.utc).isoformat()
    payload["source_branches"] = list(event.source_branches)
    payload["model_versions"] = list(event.model_versions)
    payload["bbox"] = list(event.bbox) if event.bbox is not None else None
    return payload


class SqlAlchemyVisionEventSink(VisionEventSink):
    """Persist each event revision and its delivery payload atomically."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory

    def publish(self, event: VisionEvent) -> None:
        payload = event_payload(event)
        with self.session_factory() as session:
            existing = session.scalar(
                select(VisionEventRecord).where(
                    VisionEventRecord.event_id == event.event_id,
                    VisionEventRecord.event_revision == event.event_revision,
                )
            )
            if existing is not None:
                return
            session.add(
                VisionEventRecord(
                    event_id=event.event_id,
                    event_revision=event.event_revision,
                    event_status=event.event_status,
                    event_type=event.event_type,
                    camera_id=event.camera_id,
                    risk_region_id=event.risk_region_id,
                    occurred_at=_naive_utc(event.occurred_at),
                    confidence=event.confidence,
                    source_branches=list(event.source_branches),
                    model_versions=list(event.model_versions),
                    config_revision=event.config_revision,
                    bbox=list(event.bbox) if event.bbox is not None else None,
                    area_ratio_in_risk_region=event.area_ratio_in_risk_region,
                )
            )
            session.add(
                VisionEventOutbox(
                    event_id=event.event_id,
                    event_revision=event.event_revision,
                    payload=payload,
                )
            )
            session.commit()

    def close(self) -> None:
        return None


class VisionEventPublisher(Protocol):
    def publish(self, payload: dict) -> None: ...


class OutboxDispatcher:
    """Retry pending notifications without changing the durable event history."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        publisher: VisionEventPublisher | Callable[[dict], None],
        *,
        max_attempts: int = 0,
        retry_delay_seconds: float = 5.0,
    ) -> None:
        self.session_factory = session_factory
        self.publisher = publisher
        self.max_attempts = max_attempts
        self.retry_delay_seconds = retry_delay_seconds

    def dispatch_once(self) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with self.session_factory() as session:
            row = session.scalar(
                select(VisionEventOutbox)
                .where(
                    VisionEventOutbox.status == "pending",
                    VisionEventOutbox.next_attempt_at <= now,
                )
                .order_by(VisionEventOutbox.id.asc())
                .limit(1)
            )
            if row is None:
                return False
            row.status = "sending"
            row.attempts += 1
            session.commit()
            payload = dict(row.payload)
            row_id = row.id
            attempts = row.attempts
        try:
            if hasattr(self.publisher, "publish"):
                self.publisher.publish(payload)  # type: ignore[union-attr]
            else:
                self.publisher(payload)  # type: ignore[operator]
        except Exception as exc:
            with self.session_factory() as session:
                failed = session.get(VisionEventOutbox, row_id)
                if failed is not None:
                    failed.last_error = str(exc)
                    if self.max_attempts and attempts >= self.max_attempts:
                        failed.status = "failed"
                    else:
                        failed.status = "pending"
                        failed.next_attempt_at = now + timedelta(seconds=self.retry_delay_seconds)
                    session.commit()
            return True
        with self.session_factory() as session:
            sent = session.get(VisionEventOutbox, row_id)
            if sent is not None:
                sent.status = "published"
                sent.published_at = now
                sent.last_error = None
                session.commit()
        return True

    def dispatch_available(self, limit: int = 100) -> int:
        processed = 0
        while processed < limit and self.dispatch_once():
            processed += 1
        return processed
