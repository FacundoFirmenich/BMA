from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_bpm_luke_roundwood_monthly_v0_1.py"
CAPTURE = ROOT / "scripts" / "capture_bpm_luke_roundwood_history_v0_1.py"
MONTHS = [
    f"{year}M{month:02d}"
    for year in range(2020, 2027)
    for month in range(1, 13)
    if (year, month) <= (2026, 7)
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _prepare_fixture(repo: Path, *, missing: bool = False, flagged: bool = False) -> None:
    prereg = repo / "preregistrations" / "BPM_LUKE_ROUNDWOOD_MONTHLY_2020_2026_V0.1.json"
    addendum = (
        repo
        / "preregistrations"
        / "BPM_LUKE_ROUNDWOOD_MONTHLY_2020_2026_V0.1_SOFTWARE_ADDENDUM.json"
    )
    _write_json(prereg, {"status": "FROZEN_BEFORE_HISTORICAL_VALUE_ACQUISITION"})
    _write_json(addendum, {"status": "FROZEN_BEFORE_HISTORICAL_VALUE_ACQUISITION"})

    volumes: list[float | None] = []
    prices: list[float] = []
    for index, _month in enumerate(MONTHS):
        volumes.append(350.0 + 0.8 * index + 20.0 * ((index % 12) / 11.0))
        prices.append(70.0 + 0.15 * index + 2.0 * ((index % 12) / 11.0))
    if missing:
        volumes[17] = None
    raw = {
        "class": "dataset",
        "id": ["INFO", "M", "MPKH", "KAUP", "PTL"],
        "size": [2, len(MONTHS), 1, 1, 1],
        "dimension": {
            "INFO": {"category": {"index": {"M3T": 0, "E_M3": 1}}},
            "M": {"category": {"index": {month: index for index, month in enumerate(MONTHS)}}},
            "MPKH": {"category": {"index": {"SSS": 0}}},
            "KAUP": {"category": {"index": {"PKAUP": 0}}},
            "PTL": {"category": {"index": {"TUK_KU": 0}}},
        },
        "value": volumes + prices,
    }
    if flagged:
        raw["status"] = {"17": "SOURCE_FLAG_NOT_PREREGISTERED_FOR_INTERPRETATION"}
    capture = repo / "evidence" / "runs" / "bpm-luke-roundwood-monthly-v0.1-history-capture"
    raw_path = capture / "history.json"
    _write_json(raw_path, raw)
    _write_json(
        capture / "capture_manifest.json",
        {
            "response": {"path": raw_path.name, "sha256": _sha256(raw_path)},
            "preregistration": {"sha256": _sha256(prereg)},
            "software_addendum": {"sha256": _sha256(addendum)},
        },
    )


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, str(RUNNER), str(repo)],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_complete_synthetic_fixture_exercises_the_full_causal_artifact_chain(tmp_path: Path) -> None:
    """Synthetic values test software mechanics only; they carry no scientific evidence."""
    _prepare_fixture(tmp_path)
    completed = _run(tmp_path)
    assert completed.returncode == 0, completed.stderr

    run = tmp_path / "evidence" / "runs" / "bpm-luke-roundwood-monthly-v0.1-causal"
    result = json.loads((run / "RESULT.json").read_text(encoding="utf-8"))
    forecast = json.loads((run / "FORECAST_2026-08.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "MANIFEST.json").read_text(encoding="utf-8"))
    january_2021 = json.loads((run / "freezes" / "freeze_2021-01_price.json").read_text(encoding="utf-8"))
    july_2026 = json.loads((run / "z_post" / "z_post_2026-07_price.json").read_text(encoding="utf-8"))

    assert result["status"] == "RETROSPECTIVE_REPLAY_COMPLETE_PROSPECTIVE_2026_08_FROZEN"
    assert result["history"] == {"first_month": "2020-01", "last_month": "2026-07", "month_count": 79}
    assert result["target_count"] == 78
    assert result["scored_target_count"] == 77
    assert result["preopened_targets_excluded_from_weights_and_aggregates"] == ["2026-07"]
    assert january_2021["bootstrap_seasonality"] is False
    assert july_2026["weight_evidence_updated"] is False
    assert july_2026["posterior_updates"] == 78
    assert forecast["target_period"] == "2026-08"
    assert forecast["target_opened"] is False
    assert forecast["target_available_in_raw_capture"] is False
    assert result["global_winner"] is None
    assert manifest["artifact_count_excluding_manifest"] == len(manifest["artifacts"])
    assert manifest["artifact_count_excluding_manifest"] == 713


def test_missing_cell_abstains_before_any_fit_forecast_or_z_post(tmp_path: Path) -> None:
    _prepare_fixture(tmp_path, missing=True)
    completed = _run(tmp_path)
    assert completed.returncode == 0, completed.stderr

    run = tmp_path / "evidence" / "runs" / "bpm-luke-roundwood-monthly-v0.1-causal"
    result = json.loads((run / "RESULT.json").read_text(encoding="utf-8"))
    assert result["status"] == "NOT_ESTIMABLE_INCOMPLETE_PANEL"
    assert result["fit_performed"] is False
    assert result["forecast_performed"] is False
    assert result["posterior_updated"] is False
    assert result["Z_post_updated"] is False
    assert not (run / "freezes").exists()
    assert not (run / "priors").exists()


def test_uninterpreted_source_status_abstains_before_any_fit(tmp_path: Path) -> None:
    _prepare_fixture(tmp_path, flagged=True)
    completed = _run(tmp_path)
    assert completed.returncode == 0, completed.stderr

    run = tmp_path / "evidence" / "runs" / "bpm-luke-roundwood-monthly-v0.1-causal"
    result = json.loads((run / "RESULT.json").read_text(encoding="utf-8"))
    assert result["status"] == "NOT_ESTIMABLE_UNINTERPRETED_SOURCE_STATUS"
    assert result["flagged"] == [
        {
            "period": "2021-06",
            "status": "SOURCE_FLAG_NOT_PREREGISTERED_FOR_INTERPRETATION",
            "target": "volume",
        }
    ]
    assert result["fit_performed"] is False
    assert not (run / "freezes").exists()


def test_capture_contract_is_one_bounded_post_with_no_metadata_get() -> None:
    source = CAPTURE.read_text(encoding="utf-8")
    compile(source, str(CAPTURE), "exec")
    assert 'method="POST"' in source
    assert '"remote_metadata_gets": 0' in source
    assert '"remote_data_posts": 1' in source
    assert '["M3T", "E_M3"]' in source
    assert '["SSS"]' in source
    assert '["PKAUP"]' in source
    assert '["TUK_KU"]' in source
    assert '"bulk_download": False' in source
    assert len(MONTHS) == 79
    assert MONTHS[0] == "2020M01"
    assert MONTHS[-1] == "2026M07"
