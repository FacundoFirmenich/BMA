from __future__ import annotations

import json
from pathlib import Path

import pytest

from bma.experiments import aeat_monthly_sequential_v0_6_4 as experiment


def cell(month: int, partner: str = "FR") -> dict[str, object]:
    weight = 100.0 + month
    return {
        "cell_id": f"I|72083900|{partner}",
        "flow": "I",
        "cn8": "72083900",
        "cn4": "7208",
        "partner_country": partner,
        "weight_kg": weight,
        "supplementary_units": 0.0,
        "statistical_value_eur": weight * (0.5 + month / 100.0),
        "invoice_value_eur": weight * 0.6,
        "statistical_unit_value_eur_per_kg": 0.5 + month / 100.0,
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
        "source": {"archive_sha256": f"{month:064x}", "raw_archive_persisted": False},
        "cells": cells,
    }


def test_only_adjacent_one_month_transitions_exist() -> None:
    assert experiment.one_to_one_transitions() == [
        (month, month + 1) for month in range(1, 12)
    ]


def test_frozen_control_extends_identity_without_outcome_counts() -> None:
    state = experiment.StructurallyExtensibleFrozenParticipation()
    probability = state.predict("I|72083900|DE")
    assert 0.0 < probability < 1.0
    assert state.metadata["I|72083900|DE"]["cn4"] == "7208"
    assert not state.last
    assert sum(sum(values.values()) for values in state.trials.values()) == 0


def test_full_replay_is_one_to_one_and_causally_ordered(
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
    assert result["schema_version"] == experiment.SCHEMA
    assert result["transition_count"] == 11
    assert opened == list(range(1, 13))
    assert result["temporal_contract"] == {
        "training_unit": "one calendar month",
        "prediction_unit": "one immediately following calendar month",
        "adjudication_unit": "that same target calendar month",
        "Z_post_unit": "that same target calendar month",
        "raw_months_per_transition": 1,
        "same_model_posterior_carried_forward": True,
    }
    sequence = json.loads((output / "SEQUENCE.json").read_text(encoding="utf-8"))
    for target in range(2, 13):
        period = f"2024-{target:02d}"
        freeze = next(
            index
            for index, item in enumerate(sequence)
            if item["event"] == "FREEZE_WRITTEN" and item["target_period"] == period
        )
        opened_target = next(
            index
            for index, item in enumerate(sequence)
            if item["event"] == "TARGET_MONTH_OPENED_AND_STRUCTURED"
            and item["target_period"] == period
        )
        assert freeze < opened_target
        transition = result["transitions"][target - 2]
        assert transition["training_period"] == f"2024-{target - 1:02d}"
        assert transition["target_period"] == period


def test_source_period_mismatch_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_fetch(year: int, month: int) -> dict[str, object]:
        payload = document(month)
        if month == 2:
            payload["period"] = "2024-01"
        return payload

    monkeypatch.setattr(experiment, "fetch_month", fake_fetch)
    with pytest.raises(experiment.GateFailure, match="target period mismatch"):
        experiment.run(tmp_path / "invalid")
