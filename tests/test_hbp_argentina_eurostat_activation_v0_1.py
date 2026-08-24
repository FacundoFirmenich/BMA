from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bma.experiments.hbp_indec_ipi_v0_1 import extract_ipi_records


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_indec_ipi_preregistration_fixes_source_target_and_separation() -> None:
    prereg = json.loads(
        (ROOT / "preregistrations" / "HBP_INDEC_IPI_SA_2026_07_FREEZE_V0.1.json").read_text(
            encoding="utf-8"
        )
    )
    source = ROOT / prereg["jurisdiction"]["source_workbook"]
    assert sha256(source) == prereg["jurisdiction"]["source_workbook_sha256"]
    assert prereg["target"] == {"month": "2026-07", "must_be_absent_from_workbook": True, "one_step_only": True}
    assert prereg["hard_invariants"]["IPI_and_UCII_not_merged"] is True
    assert prereg["hard_invariants"]["global_winner"] is None


def test_indec_ipi_biff8_extracts_exact_contiguous_training_series() -> None:
    pytest.importorskip("xlrd")
    source = (
        ROOT
        / "evidence"
        / "runs"
        / "hbp-indec-prodcom-public-custody-probe-v0.1"
        / "indec_ipi_series_2026.xls"
    )
    records, version = extract_ipi_records(source)
    assert version == "2.0.2"
    assert len(records) == 126
    assert records[0]["time"] == "2016-01"
    assert records[-1]["time"] == "2026-06"
    assert round(records[-1]["original_index"], 1) == 119.9
    assert round(records[-1]["seasonally_adjusted_index"], 1) == 119.1
    assert not any(record["time"] == "2026-07" for record in records)


def test_eurostat_adjudication_is_bound_to_verified_parent_and_one_target() -> None:
    prereg = json.loads(
        (
            ROOT
            / "preregistrations"
            / "HBP_EUROSTAT_STS_ES_C_2026_07_ADJUDICATION_V0.1.json"
        ).read_text(encoding="utf-8")
    )
    parent = (
        ROOT
        / "evidence"
        / "runs"
        / "hbp-eurostat-sts-es-c-v0.1-2026-07-freeze"
        / "forecast_freeze.json"
    )
    assert sha256(parent) == prereg["parent_freeze_sha256"]
    assert prereg["target_month"] == "2026-07"
    assert "sinceTimePeriod=2026-07" in prereg["target_query"]
    assert "untilTimePeriod=2026-07" in prereg["target_query"]
    assert prereg["hard_invariants"]["global_winner"] is None


def test_ucii_capture_is_schema_only_and_requires_second_freeze() -> None:
    prereg = json.loads(
        (ROOT / "preregistrations" / "HBP_INDEC_UCII_2026_07_CAPTURE_V0.1.json").read_text(
            encoding="utf-8"
        )
    )
    assert prereg["status"] == "FROZEN_BEFORE_WORKBOOK_ACQUISITION_SCHEMA_CAPTURE_ONLY"
    assert "FIT" in prereg["forbidden_operations"]
    assert "FORECAST" in prereg["forbidden_operations"]
    assert "separate exact freeze preregistration" in prereg["next_gate"]
