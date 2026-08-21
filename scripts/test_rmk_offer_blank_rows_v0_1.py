from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
OFFER = ROOT / "evidence" / "runs" / "bpm-rmk-timber-v0.1-2025-causal" / "events" / "2025-10-21" / "structured" / "offer_structured.json"


class OfferBlankRowRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(OFFER.read_text(encoding="utf-8"))

    def test_offer_volume_is_preserved(self) -> None:
        self.assertEqual(self.payload["advertised_volume_m3"], 33587)

    def test_all_source_totals_reconcile(self) -> None:
        self.assertTrue(self.payload["all_location_totals_match"])
        for obj in self.payload["objects"]:
            self.assertEqual(obj["advertised_volume_m3"], obj["location_sheet_total_m3"])
            self.assertEqual(obj["location_sheet_total_m3"], obj["location_component_sum_m3"])

    def test_blank_cells_are_not_duplicate_rows(self) -> None:
        for obj in self.payload["objects"]:
            self.assertEqual(obj["location_exact_duplicate_rows"], [])


if __name__ == "__main__":
    unittest.main()
