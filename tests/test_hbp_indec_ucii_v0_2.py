from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bma.experiments.hbp_indec_ucii_v0_2 import extract_ucii_records_v0_2


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_v0_2_amendment_changes_only_sector_support_gate() -> None:
    amendment = json.loads(
        (
            ROOT / "preregistrations" / "HBP_INDEC_UCII_LOGIT_2026_07_FREEZE_V0.2.json"
        ).read_text(encoding="utf-8")
    )
    parent = ROOT / amendment["parent_preregistration"]["path"]
    failure = ROOT / amendment["observed_gate_failure"]["path"]
    assert sha256(parent) == amendment["parent_preregistration"]["sha256"]
    assert sha256(failure) == amendment["observed_gate_failure"]["sha256"]
    assert amendment["status"] == "FROZEN_AFTER_V0_1_GATE_FAILURE_BEFORE_ANY_FIT"
    assert amendment["exposure_boundary"]["model_or_prior_changed_after_scan"] is False
    assert (
        amendment["single_repair"]["v0_2_general_gate"]
        == "every general value must satisfy 0 < u < 100"
    )
    assert (
        amendment["hard_invariants"]["sector_blocks_used_in_general_likelihood"]
        is False
    )
    assert amendment["hard_invariants"]["V0_1_gate_failure_preserved"] is True
    assert amendment["hard_invariants"]["global_winner"] is None


def test_real_v0_2_extraction_preserves_two_sector_boundaries() -> None:
    pytest.importorskip("xlrd")
    source = (
        ROOT
        / "evidence"
        / "runs"
        / "hbp-indec-ucii-v0.1-2026-07-schema-capture"
        / "indec_ucii_series_through_2026_06.xls"
    )
    records, headers, version, boundary_events = extract_ucii_records_v0_2(source)
    assert version == "2.0.2"
    assert len(records) == 126
    assert len(headers) == 14
    assert records[0]["time"] == "2016-01"
    assert records[-1]["time"] == "2026-06"
    assert round(records[-1]["general_percent"], 1) == 59.1
    assert min(record["general_percent"] for record in records) == 42.0
    assert max(record["general_percent"] for record in records) == 69.6
    assert [
        (event["time"], event["label"], event["value"]) for event in boundary_events
    ] == [
        ("2020-04", "Productos                del tabaco", 0.0),
        ("2020-04", "Industria automotriz", 0.0),
    ]
    assert not any(record["time"] == "2026-07" for record in records)
