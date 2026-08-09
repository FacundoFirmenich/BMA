from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from bma.custody import verify_manifest
from bma.experiments import mercabarna_flor_v0_4_1 as experiment


def _write_fixture_day(root: Path, day: date, units: int | None, price: float = 1.0) -> None:
    directory = root / "observations" / day.isoformat()
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    if units is not None:
        rows.append(
            {
                "cell_id": "48|ROSA",
                "product": "ROSA FLORES I PLANTAS",
                "origin_label": "Barcelona",
                "unit_count": units,
                "price_eur_per_unit": price,
            }
        )
    document = {
        "date": day.isoformat(),
        "origin_code": "48",
        "rows": rows,
        "metadata": {"forbidden_accumulated_columns_discarded": ["quantity_accumulated", "value_accumulated"]},
    }
    (directory / "origin_48.json").write_text(json.dumps(document), encoding="utf-8")


def _fixture_sources(tmp_path: Path) -> tuple[Path, Path]:
    source_v01 = tmp_path / "source-v01"
    source_v02 = tmp_path / "source-v02"
    for day_number in range(20, 27):
        target = date(2026, 7, day_number)
        _write_fixture_day(source_v01, target, None if day_number == 26 else 10 + day_number, 1.0 + (day_number % 3) / 10)
    for day_number in range(27, 32):
        target = date(2026, 7, day_number)
        _write_fixture_day(source_v02, target, 10 + day_number, 1.0 + (day_number % 3) / 10)
    return source_v01, source_v02


def test_regimes_are_explicit() -> None:
    assert experiment.regime_for(date(2026, 7, 25)) == "SATURDAY_ACTIVE_UNCALIBRATED"
    assert experiment.regime_for(date(2026, 7, 31)) == "MONTH_END_PRE_AUGUST_UNCALIBRATED"
    assert experiment.regime_for(date(2026, 7, 30)) == "ORDINARY"


def test_future_history_is_rejected() -> None:
    names = experiment.feature_names(["48"], ["ROSA FLORES I PLANTAS"])
    row = {
        "cell_id": "48|ROSA",
        "product": "ROSA FLORES I PLANTAS",
        "origin_code": "48",
        "family": "FLORES_I_PLANTAS",
    }
    history = {"48|ROSA": [{**row, "date": "2026-07-22", "unit_count": 1, "price_eur_per_unit": 1.0}]}
    with pytest.raises(experiment.GateFailure):
        experiment.build_features(row, date(2026, 7, 21), history, "quantity", names, 1.0, 1.0, 1.0, 1.0)


def test_conjugate_model_updates() -> None:
    model = experiment.BayesianLinearState.prior(["intercept", "num:x"], 0.0, 1.0)
    design = np.asarray([[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]])
    model.update(design, np.asarray([0.0, 1.0, 2.0]))
    prediction = model.predict(np.asarray([[1.0, 1.5]]))[0]
    assert prediction["lower_90"] < prediction["location"] < prediction["upper_90"]


def test_complete_replay_has_origin_control_and_causal_order(tmp_path: Path) -> None:
    source_v01, source_v02 = _fixture_sources(tmp_path)
    output = tmp_path / "run"
    result = experiment.run([source_v01, source_v02], output)
    assert result["status"] == "EXECUTED_RETROSPECTIVE_DEVELOPMENT_REPLAY"
    assert result["quantity_vs_origin_frozen"]["n"] > 0
    events = result["causal_ordering"]["events"]
    by_target: dict[str, list[str]] = {}
    for event in events:
        by_target.setdefault(event["target_date"], []).append(event["event"])
    assert all(value == ["FREEZE_WRITTEN", "TARGET_STRUCTURED_SOURCE_OPENED_AND_COMPILED"] for value in by_target.values())
    assert result["regime_state_observations"]["ORDINARY"]["quantity"] == 9
    assert result["regime_state_observations"]["SATURDAY_ACTIVE_UNCALIBRATED"]["quantity"] == 6
    assert result["participation_layer"] == "BLOCKED_NO_COMPLETENESS_WITNESS"
    assert verify_manifest(output)["status"] == "PASS"


def test_rerun_is_byte_deterministic(tmp_path: Path) -> None:
    source_v01, source_v02 = _fixture_sources(tmp_path)
    first = experiment.run([source_v01, source_v02], tmp_path / "first")
    second = experiment.run([source_v01, source_v02], tmp_path / "second")
    assert first["manifest_sha256"] == second["manifest_sha256"]
