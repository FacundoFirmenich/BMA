from __future__ import annotations

from bma.experiments.mercabarna_flor_v0_5_1 import evidence_status, summarize_participation


def test_support_gate_preserves_not_estimable() -> None:
    assert evidence_status(29, 30, 0.5, [0.6]) == "NOT_ESTIMABLE_INSUFFICIENT_SUPPORT"


def test_participation_summary_is_descriptive_only() -> None:
    rows = [
        {
            "actual": 1,
            "bma_brier": 0.1,
            "origin_frozen_brier": 0.2,
            "bma_log_loss": 0.3,
            "origin_frozen_log_loss": 0.4,
        }
        for _ in range(100)
    ]
    result = summarize_participation(rows)
    assert result["status"] == "FAVOURABLE_DESCRIPTIVE_ONLY"
    assert result["positive"] == 100
