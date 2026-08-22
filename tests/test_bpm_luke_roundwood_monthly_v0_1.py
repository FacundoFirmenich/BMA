import math

import numpy as np
import pytest

from bma.experiments import bpm_luke_roundwood_monthly_v0_1 as luke


def test_calendar_contract_is_strictly_one_month_ahead() -> None:
    luke.require_next_month("2020-12", "2021-01")
    with pytest.raises(luke.GateFailure):
        luke.require_next_month("2020-12", "2021-02")
    with pytest.raises(luke.GateFailure):
        luke.require_next_month("2020-2", "2020-03")


def test_zero_sum_month_contrasts_are_exact() -> None:
    coefficients = np.linspace(-0.5, 0.5, 11)
    effects = [float(luke.zero_sum_month_basis(month) @ coefficients) for month in range(1, 13)]
    assert sum(effects) == pytest.approx(0.0, abs=1e-12)


def test_model_dimensions_and_frozen_priors_are_target_specific() -> None:
    volume = luke.TargetState.frozen_prior("volume")
    price = luke.TargetState.frozen_prior("price")
    assert volume.models["M0"].precision.shape == (2, 2)
    assert volume.models["M1"].precision.shape == (6, 6)
    assert volume.models["M2"].precision.shape == (17, 17)
    assert volume.models["M0"].b == 0.5
    assert price.models["M0"].b == 0.02
    assert volume.weights.probabilities() == price.weights.probabilities()


def test_bootstrap_predictions_alias_m0_but_all_posteriors_learn_in_shadow() -> None:
    state = luke.TargetState.frozen_prior("volume")
    previous = luke.transform_observation("volume", 400_000.0)
    freeze = state.freeze_prediction(
        "2020-01",
        "2020-02",
        previous,
        0.0,
        bootstrap_seasonality=True,
    )
    assert freeze.components["M0"] == freeze.components["M1"] == freeze.components["M2"]
    state.update_after_adjudication(freeze, luke.transform_observation("volume", 450_000.0))
    assert state.weights.probabilities() == {
        "M0": pytest.approx(1 / 3),
        "M1": pytest.approx(1 / 3),
        "M2": pytest.approx(1 / 3),
    }
    assert {model.updates for model in state.models.values()} == {1}


def test_seasonal_models_activate_after_a_complete_bootstrap_year_without_reset() -> None:
    state = luke.TargetState.frozen_prior("price")
    previous_level = math.log(80.0)
    previous_delta = 0.0
    training = "2020-01"
    for month in range(2, 13):
        target = f"2020-{month:02d}"
        freeze = state.freeze_prediction(
            training,
            target,
            previous_level,
            previous_delta,
            bootstrap_seasonality=True,
        )
        realized_delta = 0.04 * math.sin(2.0 * math.pi * (month - 1) / 12.0)
        realized_level = previous_level + realized_delta
        state.update_after_adjudication(freeze, realized_level)
        training, previous_level, previous_delta = target, realized_level, realized_delta
    assert state.updates == 11
    assert all(model.updates == 11 for model in state.models.values())
    activated = state.freeze_prediction(
        "2020-12",
        "2021-01",
        previous_level,
        previous_delta,
        bootstrap_seasonality=False,
    )
    locations = {round(component.location, 12) for component in activated.components.values()}
    assert len(locations) > 1
    assert sum(activated.weights.values()) == pytest.approx(1.0)


def test_weights_and_updates_cannot_cross_targets_or_reuse_a_stale_freeze() -> None:
    volume = luke.TargetState.frozen_prior("volume")
    price = luke.TargetState.frozen_prior("price")
    previous = luke.transform_observation("volume", 429_000.0)
    freeze = volume.freeze_prediction("2026-07", "2026-08", previous, 0.0, bootstrap_seasonality=False)
    with pytest.raises(luke.GateFailure):
        price.update_after_adjudication(freeze, math.log(84.0))
    volume.update_after_adjudication(freeze, luke.transform_observation("volume", 430_000.0))
    with pytest.raises(luke.GateFailure):
        volume.update_after_adjudication(freeze, luke.transform_observation("volume", 431_000.0))


def test_preopened_target_can_update_state_without_rewriting_weight_evidence() -> None:
    state = luke.TargetState.frozen_prior("price")
    previous = math.log(80.0)
    freeze = state.freeze_prediction("2026-06", "2026-07", previous, 0.0, bootstrap_seasonality=False)
    before = dict(state.weights.log_evidence)
    state.update_after_adjudication(freeze, math.log(83.14), update_weight_evidence=False)
    assert state.weights.log_evidence == before
    assert state.last_period == "2026-07"
    assert all(model.updates == 1 for model in state.models.values())


def test_transform_contract_rejects_invalid_physical_values() -> None:
    assert luke.inverse_transform("volume", luke.transform_observation("volume", 429_000.0)) == pytest.approx(429_000.0)
    assert luke.inverse_transform("price", luke.transform_observation("price", 83.14)) == pytest.approx(83.14)
    with pytest.raises(luke.GateFailure):
        luke.transform_observation("volume", -1.0)
    with pytest.raises(luke.GateFailure):
        luke.transform_observation("price", 0.0)
