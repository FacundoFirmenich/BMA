import math

import pytest

from bma.experiments import aeat_monthly_seasonal_v0_6_5 as seasonal
from bma.experiments import aeat_monthly_sequential_v0_6_4 as m0


CELL = {"flow": "I", "cn4": "7207", "partner_country": "DE", "cell_id": "I|72070000|DE"}


def test_calendar_contract_rejects_pooled_or_skipped_targets():
    seasonal.require_next_month("2022-01", "2022-02")
    with pytest.raises(seasonal.GateFailure):
        seasonal.require_next_month("2022-01", "2022-03")


def test_m0_feature_delegation_is_exact():
    row = {**CELL, "cn8": "72070000"}
    state, _, names, scales = m0.initialize({"period": "2024-01", "cells": [{**row, "weight_kg": 5.0, "statistical_unit_value_eur_per_kg": 2.0}]})
    expected = m0.build_features(row, "2024-02", "weight_kg", state, names, scales["quantity_center"], scales["quantity_scale"], scales["quantity_center"], scales["quantity_scale"])
    assert (seasonal.m0_features(row, "2024-02", "weight_kg", state, names, scales["quantity_center"], scales["quantity_scale"], scales["quantity_center"], scales["quantity_scale"]) == expected).all()


def test_weights_are_separate_and_post_outcome():
    quantity = seasonal.PrequentialWeights()
    value = seasonal.PrequentialWeights()
    quantity.update_after_adjudication({"M0": -2.0, "M1": -1.0, "M2": -3.0})
    assert quantity.probabilities()["M1"] > quantity.probabilities()["M0"]
    assert value.probabilities() == {"M0": pytest.approx(1 / 3), "M1": pytest.approx(1 / 3), "M2": pytest.approx(1 / 3)}


def test_m2_residual_is_centered_and_future_free():
    state = seasonal.SeasonalState()
    assert state.prediction_delta(CELL, "2023-02", "M2") == 0.0
    state.update_after_adjudication(CELL, "2022-02", 2.0)
    state.update_after_adjudication(CELL, "2023-02", -1.0)
    assert math.isfinite(state.prediction_delta(CELL, "2024-02", "M2"))
    for totals, counts in zip(state.residual_sum.values(), state.residual_count.values()):
        active = counts > 0
        assert abs(float(totals[active].sum())) < 1e-10
