from __future__ import annotations

import json
from pathlib import Path

import pytest

from bma.experiments.hbp_eurostat_sts_v0_1 import GateFailure
from bma.experiments.hbp_indec_ucii_v0_1 import (
    bayesian_linear_posterior,
    bounded_forecast,
    extract_ucii_records,
    harmonic_features,
    inverse_logit_percent,
    logit_percent,
)


ROOT = Path(__file__).resolve().parents[1]


def test_logit_percent_roundtrip_and_bounds() -> None:
    for value in (1.0, 41.5, 59.1, 99.0):
        assert inverse_logit_percent(logit_percent([value])[0]) == pytest.approx(value)
    with pytest.raises(GateFailure):
        logit_percent([0.0])
    with pytest.raises(GateFailure):
        logit_percent([100.0])


def test_harmonic_posterior_is_finite_and_bounded_after_mapping() -> None:
    response = [0.01, -0.02, 0.03, -0.01, 0.0, 0.02]
    design = [harmonic_features(month) for month in (1, 2, 3, 4, 5, 6)]
    posterior = bayesian_linear_posterior(
        response,
        design,
        prior_mean=[0.0] * 5,
        prior_precision_diagonal=[1.0, 4.0, 4.0, 8.0, 8.0],
        alpha0=2.0,
        beta0_scale=0.0004,
        future_features=harmonic_features(7),
    )
    forecast = bounded_forecast(59.1, posterior["posterior_predictive"])
    assert 0.0 < forecast["lower_90_percent"] < forecast["point_median_percent"]
    assert forecast["point_median_percent"] < forecast["upper_90_percent"] < 100.0


def test_real_ucii_v0_1_gate_fails_before_fit_on_sector_boundary() -> None:
    pytest.importorskip("xlrd")
    source = (
        ROOT
        / "evidence"
        / "runs"
        / "hbp-indec-ucii-v0.1-2026-07-schema-capture"
        / "indec_ucii_series_through_2026_06.xls"
    )
    with pytest.raises(GateFailure, match="strictly between 0 and 100"):
        extract_ucii_records(source)


def test_ucii_v0_1_gate_failure_is_preserved_without_fit() -> None:
    result = json.loads(
        (ROOT / "evidence" / "runs" / "hbp-indec-ucii-logit-v0.1-2026-07-gate-fail" / "GATE_FAILURE.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["status"] == "GATE_FAIL_SECTOR_BOUNDARY_VALUE_BEFORE_FIT"
    assert result["general_support"] == {"strict_0_100": True, "minimum": 42.0, "maximum": 69.6}
    assert len(result["sector_boundary_events"]) == 2
    assert result["fit_performed"] is False
    assert result["forecast_performed"] is False
    assert result["target_outcome_opened"] is False
    assert result["global_winner"] is None
