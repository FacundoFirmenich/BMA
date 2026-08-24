import math

import pytest

from bma.experiments.hbp_eurostat_sts_v0_1 import (
    GateFailure,
    index_forecast,
    log_innovations,
    m0_posterior,
    m1_posterior,
)


def test_log_innovations_and_positive_gate() -> None:
    observed = log_innovations([100.0, 101.0, 99.0])
    assert observed == pytest.approx([math.log(1.01), math.log(99.0 / 101.0)])
    with pytest.raises(GateFailure):
        log_innovations([100.0, 0.0])


def test_m0_exact_inverse_gamma_update() -> None:
    posterior = m0_posterior([0.1, -0.2], alpha0=2.0, beta0=0.0004)
    assert posterior["n"] == 2
    assert posterior["alpha"] == pytest.approx(3.0)
    assert posterior["beta"] == pytest.approx(0.0254)
    assert posterior["predictive"].location == 0.0


def test_m1_exact_normal_inverse_gamma_update() -> None:
    posterior = m1_posterior(
        [0.1, -0.1], mu0=0.0, kappa0=1.0, alpha0=2.0, beta0=0.0004
    )
    assert posterior["n"] == 2
    assert posterior["mu"] == pytest.approx(0.0)
    assert posterior["kappa"] == pytest.approx(3.0)
    assert posterior["alpha"] == pytest.approx(3.0)
    assert posterior["beta"] == pytest.approx(0.0104)


def test_forecast_maps_log_predictive_monotonically() -> None:
    posterior = m1_posterior(
        [0.01, 0.02, -0.01], mu0=0.0, kappa0=1.0, alpha0=2.0, beta0=0.0004
    )
    forecast = index_forecast(100.0, posterior["predictive"])
    assert forecast["lower_90_index"] < forecast["point_median_index"] < forecast["upper_90_index"]
    assert forecast["point_median_index"] > 0.0

