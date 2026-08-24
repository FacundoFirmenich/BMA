from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parent))
from close_rmk_scored_event_v0_2 import phase_state, predictive_log_score  # noqa: E402
from freeze_rmk_offer_v0_5 import delivery_phase, frozen_outcome  # noqa: E402


class BatchM1Tests(unittest.TestCase):
    def test_delivery_period_whitespace(self) -> None:
        self.assertEqual(delivery_phase("13.10.2025 - 31.12.2025", "2025-10-07"), ("VALID", "M10-M11-M12"))

    def test_invalid_delivery_chronology(self) -> None:
        state, phase = delivery_phase("26.08.2025-31.10.2024", "2025-08-22")
        self.assertEqual(state, "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY")
        self.assertIsNone(phase)

    def test_m1_numeric_freeze_at_three_observations(self) -> None:
        cell = {
            "price": {"observations": [55.0, 40.0, 47.0], "phases": ["M05-M06-M07", "M10-M11-M12", "M10-M11-M12"], "m1_innovations": []},
            "volume": {"observations": [2761.0, 2300.0, 40000.0], "phases": ["M05-M06-M07", "M10-M11-M12", "M10-M11-M12"], "m1_innovations": []},
        }
        payload = frozen_outcome(cell, "price", "M10-M11-M12")
        self.assertIn("point", payload["M1"])
        self.assertEqual(payload["M1"]["density_state"], "ESTIMABLE")
        self.assertEqual(payload["M2"]["state"], "NOT_ESTIMABLE_M2_PHASE_SUPPORT")

    def test_original_scale_log_score_has_jacobian(self) -> None:
        payload = {"log_location": math.log(50.0), "log_scale": 0.2, "degrees_of_freedom": 2}
        score = predictive_log_score(payload, 50.0)
        self.assertTrue(math.isfinite(score))
        self.assertLess(score, 0.0)

    def test_same_event_innovations_do_not_activate_m2(self) -> None:
        payload = {
            "observations": [10.0, 11.0, 12.0, 13.0, 14.0],
            "phases": ["M01", "M02", "M03", "M04", "M04"],
            "m1_innovations": [["M04", 0.1], ["M04", -0.1]],
            "m1_innovation_events": ["2025-04-01", "2025-04-01"],
        }
        state = phase_state(payload)
        self.assertEqual(state["M2"]["state"], "NOT_ESTIMABLE_SEASONAL_SUPPORT")
        self.assertEqual(state["M2"]["same_phase_distinct_innovation_events"]["M04"], 1)

    def test_distinct_events_can_satisfy_m2_event_gate(self) -> None:
        payload = {
            "observations": [10.0, 11.0, 12.0, 13.0, 14.0],
            "phases": ["M01", "M02", "M03", "M04", "M04"],
            "m1_innovations": [["M04", 0.1], ["M04", -0.1]],
            "m1_innovation_events": ["2025-04-01", "2026-04-01"],
        }
        state = phase_state(payload)
        self.assertEqual(state["M2"]["state"], "ESTIMABLE_FOR_LISTED_PHASES")
        self.assertEqual(state["M2"]["estimable_phases"], ["M04"])


if __name__ == "__main__":
    unittest.main()
