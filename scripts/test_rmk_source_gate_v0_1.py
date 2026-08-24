from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parent))
from freeze_rmk_offer_v0_6 import object_gate  # noqa: E402


class SourceGateTests(unittest.TestCase):
    def test_verified_source_passes(self) -> None:
        self.assertIsNone(object_gate("VALID", "VERIFIED_STATED_TOTAL_AND_COMPONENT_SUM"))

    def test_volume_conflict_blocks_even_with_valid_period(self) -> None:
        self.assertEqual(
            object_gate("VALID", "SOURCE_STATED_TOTAL_DISAGREEMENT"),
            "NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT",
        )

    def test_invalid_period_has_first_precedence(self) -> None:
        self.assertEqual(
            object_gate("NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY", "SOURCE_STATED_TOTAL_DISAGREEMENT"),
            "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY",
        )


if __name__ == "__main__":
    unittest.main()
