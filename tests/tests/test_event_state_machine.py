from __future__ import annotations

from datetime import datetime, timedelta, timezone

import unittest

from water_workflow.config import EventRuleConfig, EventRulesConfig
from water_workflow.monitoring.events import VisionEventStateMachine
from water_workflow.monitoring.types import DetectionEvidence


class VisionEventStateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        rule = EventRuleConfig(confirm_hits=2, confirm_window_seconds=3, recovery_quiet_seconds=5, update_interval_seconds=1)
        self.machine = VisionEventStateMachine(
            "cam-1",
            EventRulesConfig(water_drop=rule, pipe_burst=rule, water_accumulation=rule, default=rule),
        )
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def evidence(self, at: datetime) -> DetectionEvidence:
        return DetectionEvidence("cam-1", 1, at, "water_drop", 0.9, (1, 2, 8, 9), "full_frame")

    def test_confirm_update_recover_and_revision(self) -> None:
        self.assertEqual(self.machine.observe([self.evidence(self.start)], [], self.start), [])
        confirmed = self.machine.observe([self.evidence(self.start + timedelta(seconds=1))], [], self.start + timedelta(seconds=1))
        self.assertEqual(confirmed[0].event_status, "confirmed")
        self.assertEqual(confirmed[0].event_revision, 1)
        updated = self.machine.observe([self.evidence(self.start + timedelta(seconds=3))], [], self.start + timedelta(seconds=3))
        self.assertEqual(updated[0].event_status, "updated")
        self.assertEqual(updated[0].event_revision, 2)
        recovered = self.machine.observe([], [], self.start + timedelta(seconds=9))
        self.assertEqual(recovered[0].event_status, "recovered")
        self.assertEqual(recovered[0].event_revision, 3)

    def test_short_suspected_sequence_resets(self) -> None:
        self.machine.observe([self.evidence(self.start)], [], self.start)
        self.assertEqual(self.machine.observe([], [], self.start + timedelta(seconds=4)), [])
        self.assertEqual(self.machine.active_states(), {})


if __name__ == "__main__":
    unittest.main()
