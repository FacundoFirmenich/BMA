from __future__ import annotations

import json
from pathlib import Path

from bma.evidence import load_and_validate


ROOT = Path(__file__).parents[1]


def test_v051_and_industrial_registry_addendum_is_valid() -> None:
    result = load_and_validate(ROOT / "evidence" / "registry_addendum_v051_industrial_20260809.json")
    assert result == {
        "status": "PASS",
        "entries": 3,
        "ids": [
            "DE-RLP-WERTHOLZ-2026-SOURCE-AUDIT",
            "ES-AEAT-NC72083900-SOURCE-AUDIT",
            "MB-FLOR-V051-SUBFAMILY-AUDIT",
        ],
    }


def test_industrial_audit_separates_open_aeat_from_restricted_timber() -> None:
    document = json.loads((ROOT / "evidence" / "industrial_source_candidates_20260809.json").read_text("utf-8"))
    decision = document["decision"]
    assert decision["best_open_spanish_nonbiological_source"] == "ES-AEAT-FOREIGN-TRADE-GOODS"
    assert decision["best_transaction_level_bind_candidate"] == "ES-SCRAPAD-METALS"
    assert decision["source_connector_authorized"] is True
    assert decision["model_execution_authorized"] is False
    assert decision["raw_publication_authorized_by_source"] == {
        "ES-AEAT-FOREIGN-TRADE-GOODS": True,
        "DE-RLP-WERTHOLZ-PFALZ-2026": False,
    }


def test_aeat_receipt_reconciles_detail_and_summary() -> None:
    receipt = json.loads((ROOT / "evidence" / "receipts" / "aeat-steel-source-audit-20260809.json").read_text("utf-8"))
    assert receipt["status"] == "TECHNICAL_SOURCE_PASS_MODEL_NOT_EXECUTED"
    assert receipt["sample_2025_01"]["cn72083900"]["detail_to_summary_reconciled"] is True
    assert receipt["claim_boundary"]["transaction_or_award_price"] is False
    assert receipt["claim_boundary"]["regulated_price_market"] is False


def test_v051_receipt_preserves_plant_quantity_not_estimable() -> None:
    receipt = json.loads((ROOT / "evidence" / "receipts" / "mercabarna-flor-v0.5.1.json").read_text("utf-8"))
    assert receipt["plant_live_ordinary"]["participation"]["status"] == "FAVOURABLE_DESCRIPTIVE_ONLY"
    assert receipt["plant_live_ordinary"]["quantity"]["status"] == "NOT_ESTIMABLE_INSUFFICIENT_SUPPORT"
