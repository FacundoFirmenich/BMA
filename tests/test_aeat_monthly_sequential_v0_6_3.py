from __future__ import annotations

import json
from pathlib import Path

import pytest

from bma.experiments import aeat_monthly_sequential_v0_6_3 as experiment


def cell(period_month: int, suffix: str = "FR") -> dict[str, object]:
    weight = 100.0 + period_month
    return {
        "cell_id": f"I|72083900|{suffix}",
        "flow": "I",
        "cn8": "72083900",
        "cn4": "7208",
        "partner_country": suffix,
        "weight_kg": weight,
        "supplementary_units": 0.0,
        "statistical_value_eur": weight * (0.5 + period_month / 100.0),
        "invoice_value_eur": weight * 0.6,
        "statistical_unit_value_eur_per_kg": 0.5 + period_month / 100.0,
        "invoice_unit_value_eur_per_kg": 0.6,
        "line_count": 1,
        "dimension_cardinality": {},
    }


def document(month: int) -> dict[str, object]:
    cells = [cell(month)]
    if month >= 3:
        cells.append(cell(month, "DE"))
    return {
        "schema_version": "test",
        "period": f"2024-{month:02d}",
        "scope": "chapter_72_iron_and_steel",
        "aggregation_key": ["flow", "cn8", "partner_country"],
        "source": {
            "archive_sha256": f"{month:064x}",
            "raw_archive_persisted": False,
        },
        "cells": cells,
    }


def test_contract_contains_only_adjacent_one_to_one_transitions() -> None:
    transitions = experiment.one_to_one_transitions()
    assert transitions == [(month, month + 1) for month in range(1, 12)]
    assert all(target - training == 1 for training, target in transitions)


def test_future_month_in_feature_history_is_rejected() -> None:
    initial = document(1)
    state, _, names, scales = experiment.initialize(initial)
    state.history["I|72083900|FR"].append({**cell(3), "period": "2024-03"})
    with pytest.raises(experiment.GateFailure, match="future month"):
        experiment.build_features(
            cell(1),
            "2024-02",
            "weight_kg",
            state,
            names,
            scales["quantity_center"],
            scales["quantity_scale"],
            scales["quantity_center"],
            scales["quantity_scale"],
        )


def test_run_freezes_each_target_before_open_and_carries_same_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[int] = []

    def fake_fetch(year: int, month: int) -> dict[str, object]:
        assert year == 2024
        opened.append(month)
        return document(month)

    monkeypatch.setattr(experiment, "fetch_month", fake_fetch)
    output = tmp_path / "run"
    result = experiment.run(output)
    assert result["transition_count"] == 11
    assert result["temporal_contract"]["raw_months_per_transition"] == 1
    assert result["temporal_contract"]["same_model_posterior_carried_forward"] is True
    assert opened == list(range(1, 13))

    sequence = json.loads((output / "SEQUENCE.json").read_text(encoding="utf-8"))
    for month in range(2, 13):
        period = f"2024-{month:02d}"
        freeze_index = next(
            index
            for index, item in enumerate(sequence)
            if item["event"] == "FREEZE_WRITTEN" and item["target_period"] == period
        )
        open_index = next(
            index
            for index, item in enumerate(sequence)
            if item["event"] == "TARGET_MONTH_OPENED_AND_STRUCTURED"
            and item["target_period"] == period
        )
        assert freeze_index < open_index
        transition = result["transitions"][month - 2]
        assert transition["training_period"] == f"2024-{month - 1:02d}"
        assert transition["target_period"] == period


def test_non_adjacent_state_cut_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(year: int, month: int) -> dict[str, object]:
        payload = document(month)
        if month == 2:
            payload["period"] = "2024-01"
        return payload

    monkeypatch.setattr(experiment, "fetch_month", fake_fetch)
    with pytest.raises(experiment.GateFailure):
        experiment.run(tmp_path / "invalid")
