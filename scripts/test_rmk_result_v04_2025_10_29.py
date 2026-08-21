from __future__ import annotations

import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-10-29"


class ResultV04Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.offer = json.loads((EVENT / "structured/offer_structured.json").read_text(encoding="utf-8"))
        cls.result = json.loads((EVENT / "structured/result_v0_4_candidate.json").read_text(encoding="utf-8"))
        cls.offer_by_id = {item["object_id"]: item for item in cls.offer["objects"]}

    def test_census_and_quarantine(self) -> None:
        self.assertEqual(self.result["award_row_count"], 72)
        self.assertEqual(self.result["local_outcome_count"], 62)
        self.assertEqual(self.result["quarantined_outcome_count"], 10)
        self.assertEqual(self.result["extraction_failures"], [])
        self.assertEqual({item["object_id"] for item in self.result["quarantined_outcomes"]}, {6})
        self.assertNotIn(6, {item["object_id"] for item in self.result["local_outcomes"]})

    def test_offer_product_is_canonical_and_raw_label_is_preserved(self) -> None:
        for row in self.result["rows"]:
            self.assertEqual(row["product"], self.offer_by_id[row["object_id"]]["product"])
            self.assertTrue(row["raw_result_product"])

    def test_weighted_price_examples(self) -> None:
        first_by_object = {}
        for row in self.result["rows"]:
            first_by_object.setdefault(row["object_id"], row)
        expected = {
            1: 72 * 0.24 + 115 * 0.76,
            2: 72 * 0.70 + 97 * 0.30,
            3: 155 * 0.16 + 175 * 0.50 + 190 * 0.34,
            5: 96 * 0.07 + 98 * 0.40 + 100 * 0.53,
        }
        for object_id, value in expected.items():
            self.assertTrue(math.isclose(first_by_object[object_id]["effective_weighted_price_eur_m3"], value, rel_tol=0, abs_tol=1e-12))
            self.assertEqual(first_by_object[object_id]["price_state"], "ESTIMABLE_OFFER_WEIGHTED_CLASS_PRICE")

    def test_weighted_row_count(self) -> None:
        self.assertEqual(sum(row["price_state"] == "ESTIMABLE_OFFER_WEIGHTED_CLASS_PRICE" for row in self.result["rows"]), 13)

    def test_source_conflict_has_no_denominator(self) -> None:
        total = next(item for item in self.result["object_totals"] if item["object_id"] == 6)
        self.assertEqual(total["state"], "NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT")
        self.assertIsNone(total["coverage_offer_denominator"])
        self.assertIsNone(total["coverage_location_sheet_denominator"])

    def test_raw_and_freeze_links(self) -> None:
        self.assertEqual(self.result["source_sha256"], "1620F40B4BD2ACDCE86765D02EFDD57F8A20485BE7F064006EDF7C6589B47A67")
        self.assertEqual(self.result["freeze_used_sha256"], "5407C7504D3D7C2F44BC9572A215CCE6247681E1F651884D28622C51D496B635")


if __name__ == "__main__":
    unittest.main()
