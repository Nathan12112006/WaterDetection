from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from ..config import EventRuleConfig, EventRulesConfig
from .types import (
    DetectionEvidence,
    EventLifecycleState,
    SegmentationEvidence,
    VisionEvent,
)


def _event_type(label: str, *, segmented: bool = False) -> str | None:
    normalized = " ".join(label.lower().replace("_", " ").replace("-", " ").split())
    if segmented or normalized in {"water accumulation", "water surface"}:
        return "water_accumulation"
    if normalized in {"water drop", "drop", "滴水", "水滴"}:
        return "water_drop"
    if normalized in {"pipe burst", "burst", "爆管", "爆管漏水"}:
        return "pipe_burst"
    return None


def _rule_for(event_type: str, rules: EventRulesConfig) -> EventRuleConfig:
    return getattr(rules, event_type, rules.default)


@dataclass
class _ActiveEvent:
    event_id: str
    event_type: str
    camera_id: str
    risk_region_id: str | None
    state: EventLifecycleState = EventLifecycleState.NORMAL
    hits: list[datetime] = field(default_factory=list)
    last_seen_at: datetime | None = None
    last_emitted_at: datetime | None = None
    revision: int = 0
    evidence: list[DetectionEvidence | SegmentationEvidence] = field(default_factory=list)


class VisionEventStateMachine:
    """Convert per-frame evidence into confirmed, updated and recovered events."""

    def __init__(self, camera_id: str, rules: EventRulesConfig, config_revision: str = "unversioned") -> None:
        self.camera_id = camera_id
        self.rules = rules
        self.config_revision = config_revision
        self._active: dict[tuple[str, str | None], _ActiveEvent] = {}

    def _now(self, value: datetime | None) -> datetime:
        return value or datetime.now(timezone.utc)

    def _evidence(self, detections, segments):
        items: list[DetectionEvidence | SegmentationEvidence] = []
        for item in detections:
            event_type = _event_type(item.label)
            if event_type:
                items.append(item)
        for item in segments:
            event_type = _event_type(item.class_name, segmented=True)
            if event_type:
                items.append(item)
        return items

    @staticmethod
    def _summary(event: _ActiveEvent) -> tuple[float, tuple[str, ...], tuple[str, ...], tuple[int, int, int, int] | None, float | None]:
        evidence = event.evidence
        confidence = max((item.confidence for item in evidence), default=0.0)
        sources = tuple(sorted({item.source_branch for item in evidence}))
        models = tuple(sorted({item.model_version for item in evidence}))
        boxes = [item.bbox for item in evidence]
        bbox = None
        if boxes:
            bbox = (
                min(item[0] for item in boxes),
                min(item[1] for item in boxes),
                max(item[2] for item in boxes),
                max(item[3] for item in boxes),
            )
        ratios = [item.area_ratio_in_risk_region for item in evidence if isinstance(item, SegmentationEvidence) and item.area_ratio_in_risk_region is not None]
        return confidence, sources, models, bbox, (max(ratios) if ratios else None)

    def _emit(self, event: _ActiveEvent, status: str, at: datetime) -> VisionEvent:
        confidence, sources, models, bbox, area_ratio = self._summary(event)
        event.revision += 1
        event.last_emitted_at = at
        return VisionEvent(
            event_id=event.event_id,
            event_revision=event.revision,
            event_status=status,
            event_type=event.event_type,
            camera_id=event.camera_id,
            risk_region_id=event.risk_region_id,
            occurred_at=at,
            confidence=confidence,
            source_branches=sources,
            model_versions=models,
            config_revision=self.config_revision,
            bbox=bbox,
            area_ratio_in_risk_region=area_ratio,
        )

    def observe(self, detections, segments, at: datetime | None = None) -> list[VisionEvent]:
        observed_at = self._now(at)
        grouped: dict[tuple[str, str | None], list[DetectionEvidence | SegmentationEvidence]] = {}
        for item in self._evidence(detections, segments):
            event_type = _event_type(item.label if isinstance(item, DetectionEvidence) else item.class_name, segmented=isinstance(item, SegmentationEvidence))
            if event_type is not None:
                grouped.setdefault((event_type, item.risk_region_id), []).append(item)
        emitted: list[VisionEvent] = []
        keys = set(self._active) | set(grouped)
        for key in keys:
            event_type, region_id = key
            rule = _rule_for(event_type, self.rules)
            active = self._active.get(key)
            evidence = [item for item in grouped.get(key, []) if item.confidence >= rule.min_confidence]
            if active is None:
                active = _ActiveEvent(str(uuid4()), event_type, self.camera_id, region_id)
                self._active[key] = active
            if evidence:
                active.evidence = list(evidence)
                active.last_seen_at = observed_at
                active.hits = [item for item in active.hits if (observed_at - item).total_seconds() <= rule.confirm_window_seconds]
                active.hits.append(observed_at)
                if active.state == EventLifecycleState.RECOVERY:
                    active.state = EventLifecycleState.CONFIRMED
                elif active.state == EventLifecycleState.NORMAL:
                    active.state = EventLifecycleState.SUSPECTED
                if active.state == EventLifecycleState.SUSPECTED and len(active.hits) >= rule.confirm_hits:
                    active.state = EventLifecycleState.CONFIRMED
                    emitted.append(self._emit(active, "confirmed", observed_at))
                elif active.state == EventLifecycleState.CONFIRMED and (
                    active.last_emitted_at is None or (observed_at - active.last_emitted_at).total_seconds() >= rule.update_interval_seconds
                ):
                    emitted.append(self._emit(active, "updated", observed_at))
            elif active.state == EventLifecycleState.CONFIRMED and active.last_seen_at is not None:
                if (observed_at - active.last_seen_at).total_seconds() >= rule.recovery_quiet_seconds:
                    active.state = EventLifecycleState.RECOVERY
                    emitted.append(self._emit(active, "recovered", observed_at))
                    del self._active[key]
            elif active.state == EventLifecycleState.SUSPECTED and active.hits:
                if (observed_at - active.hits[-1]).total_seconds() > rule.confirm_window_seconds:
                    del self._active[key]
        return emitted

    def active_states(self) -> dict[tuple[str, str | None], EventLifecycleState]:
        return {key: event.state for key, event in self._active.items()}
