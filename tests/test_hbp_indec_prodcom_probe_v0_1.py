from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "evidence" / "runs" / "hbp-indec-prodcom-public-custody-probe-v0.1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_preregistration_is_bounded_and_no_fit() -> None:
    prereg = json.loads(
        (ROOT / "preregistrations" / "HBP_INDEC_PRODCOM_PUBLIC_CUSTODY_PROBE_V0.1.json").read_text(
            encoding="utf-8"
        )
    )
    assert prereg["status"] == "PREREGISTERED_BEFORE_BYTE_ACQUISITION"
    assert prereg["prodcom_probe"]["reporter"] == "ES"
    assert prereg["prodcom_probe"]["product"] == "16101035"
    assert prereg["prodcom_probe"]["reference_year"] == "2024"
    assert prereg["epistemic_boundary"]["global_winner"] == "FORBIDDEN"


def test_capture_manifest_raw_hashes_and_invariants() -> None:
    manifest = json.loads((RUN / "capture_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["records"]) == 6
    for record in manifest["records"]:
        assert record["http_status"] == 200
        assert sha256(RUN / record["name"]) == record["sha256"]
    assert set(manifest["invariants"].values()) == {False}


def test_prodcom_empty_cell_is_preserved_not_estimated() -> None:
    raw = json.loads((RUN / "eurostat_prodcom_es_16101035_2024_primary.json").read_text(encoding="utf-8"))
    adjudication = json.loads((RUN / "probe_adjudication.json").read_text(encoding="utf-8"))
    assert raw["id"] == ["freq", "reporter", "product", "indicators", "time"]
    assert raw["size"] == [1, 1, 1, 3, 1]
    assert raw["value"] == {}
    assert adjudication["eurostat_prodcom"]["status"] == "NOT_ESTIMABLE_NO_CELL"
    assert adjudication["eurostat_prodcom"]["published_value_count"] == 0


def test_indec_current_vintage_values_and_authority() -> None:
    result = json.loads((RUN / "probe_adjudication.json").read_text(encoding="utf-8"))
    assert result["raw_integrity"] == "PASS_ALL_CAPTURE_HASHES_RECOMPUTED"
    assert result["indec_ipi"]["national_general"]["original_index_base_2004_100"] == 119.9
    assert result["indec_ipi"]["wood_evidence"]["wood_year_over_year_percent"] == 17.3
    assert result["indec_ipi"]["forecast_authority"] == "ABSTAIN_UNTIL_STRUCTURED_SERIES_OR_FUTURE_FREEZE"
    assert result["indec_ucii"]["general_capacity_utilization_percent"] == 59.1
    assert result["indec_ucii"]["forecast_authority"] == "OBSERVER_ONLY_UNTIL_SEPARATE_CAUSAL_PREREGISTRATION"
    assert result["coral_adjudication"]["position_change"] == "BETTER_OBSERVATIONAL_CUSTODY_BUT_NO_NEW_CAUSAL_SCORE"

