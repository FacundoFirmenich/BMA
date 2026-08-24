import math

import pytest

from bma.experiments.hbp_eurostat_sts_v0_1 import (
    GateFailure,
    StudentTPredictive,
    score_index_observation,
    student_t_crps,
    update_weights_from_log_scores,
)


def test_student_t_crps_is_symmetric_and_positive() -> None:
    predictive = StudentTPredictive(degrees_of_freedom=10.0, location=0.0, scale=1.0)
    assert student_t_crps(0.0, predictive) > 0.0
    assert student_t_crps(-0.7, predictive) == pytest.approx(student_t_crps(0.7, predictive))


def test_score_index_observation_applies_log_jacobian() -> None:
    forecast = {
        "degrees_of_freedom": 10.0,
        "log_index_location": math.log(100.0),
        "log_index_scale": 0.1,
        "point_median_index": 100.0,
        "lower_90_index": 80.0,
        "upper_90_index": 120.0,
    }
    score = score_index_observation(100.0, forecast)
    assert score["absolute_error_index_points"] == 0.0
    assert score["central_90_covered"] is True
    assert math.isfinite(score["log_score_index_density"])
    assert score["crps_log_index"] > 0.0


def test_log_score_weight_update_is_normalized_and_directional() -> None:
    updated = update_weights_from_log_scores(
        {"M0": 0.5, "M1": 0.5},
        {"M0": -2.0, "M1": -1.0},
    )
    assert sum(updated.values()) == pytest.approx(1.0)
    assert updated["M1"] > updated["M0"]


def test_weight_update_rejects_identity_or_support_failures() -> None:
    with pytest.raises(GateFailure):
        update_weights_from_log_scores({"M0": 1.0}, {"M1": -1.0})
    with pytest.raises(GateFailure):
        update_weights_from_log_scores({"M0": 0.0}, {"M0": -1.0})
