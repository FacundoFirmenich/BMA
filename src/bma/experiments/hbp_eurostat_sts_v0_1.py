"""Frozen conjugate models for the first HBP Eurostat STS chain.

Scientific values must come from the separately frozen official response.  This
module contains only deterministic transformations and conjugate updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, log, sqrt
from typing import Iterable

from scipy.stats import t as student_t


class GateFailure(RuntimeError):
    """Raised when a frozen scientific or temporal invariant is violated."""


@dataclass(frozen=True)
class StudentTPredictive:
    degrees_of_freedom: float
    location: float
    scale: float

    def interval(self, mass: float = 0.90) -> tuple[float, float]:
        if not 0.0 < mass < 1.0:
            raise GateFailure("predictive interval mass must be strictly between zero and one")
        tail = (1.0 - mass) / 2.0
        return (
            float(student_t.ppf(tail, self.degrees_of_freedom, loc=self.location, scale=self.scale)),
            float(student_t.ppf(1.0 - tail, self.degrees_of_freedom, loc=self.location, scale=self.scale)),
        )


def require_positive_finite(values: Iterable[float]) -> list[float]:
    checked = [float(value) for value in values]
    if not checked:
        raise GateFailure("empty index series")
    if any(not isfinite(value) or value <= 0.0 for value in checked):
        raise GateFailure("all index observations must be positive and finite")
    return checked


def log_innovations(index_values: Iterable[float]) -> list[float]:
    checked = require_positive_finite(index_values)
    return [log(current) - log(previous) for previous, current in zip(checked, checked[1:])]


def m0_posterior(
    innovations: Iterable[float], *, alpha0: float, beta0: float
) -> dict[str, float | int | StudentTPredictive]:
    observed = [float(value) for value in innovations]
    if alpha0 <= 0.0 or beta0 <= 0.0:
        raise GateFailure("inverse-gamma hyperparameters must be positive")
    alpha_n = alpha0 + len(observed) / 2.0
    beta_n = beta0 + 0.5 * sum(value * value for value in observed)
    predictive = StudentTPredictive(
        degrees_of_freedom=2.0 * alpha_n,
        location=0.0,
        scale=sqrt(beta_n / alpha_n),
    )
    return {
        "n": len(observed),
        "sum_squared_innovations": sum(value * value for value in observed),
        "alpha": alpha_n,
        "beta": beta_n,
        "predictive": predictive,
    }


def m1_posterior(
    innovations: Iterable[float], *, mu0: float, kappa0: float, alpha0: float, beta0: float
) -> dict[str, float | int | StudentTPredictive]:
    observed = [float(value) for value in innovations]
    if kappa0 <= 0.0 or alpha0 <= 0.0 or beta0 <= 0.0:
        raise GateFailure("Normal-Inverse-Gamma scale hyperparameters must be positive")
    n = len(observed)
    sample_mean = sum(observed) / n if n else 0.0
    centered_sum_squares = sum((value - sample_mean) ** 2 for value in observed)
    kappa_n = kappa0 + n
    mu_n = (kappa0 * mu0 + n * sample_mean) / kappa_n
    alpha_n = alpha0 + n / 2.0
    beta_n = (
        beta0
        + 0.5 * centered_sum_squares
        + (kappa0 * n * (sample_mean - mu0) ** 2) / (2.0 * kappa_n)
    )
    predictive = StudentTPredictive(
        degrees_of_freedom=2.0 * alpha_n,
        location=mu_n,
        scale=sqrt(beta_n * (kappa_n + 1.0) / (alpha_n * kappa_n)),
    )
    return {
        "n": n,
        "sum_innovations": sum(observed),
        "sum_squared_innovations": sum(value * value for value in observed),
        "sample_mean": sample_mean,
        "centered_sum_squares": centered_sum_squares,
        "mu": mu_n,
        "kappa": kappa_n,
        "alpha": alpha_n,
        "beta": beta_n,
        "predictive": predictive,
    }


def index_forecast(last_index: float, innovation: StudentTPredictive) -> dict[str, float]:
    require_positive_finite([last_index])
    lower_log, upper_log = innovation.interval(0.90)
    last_log = log(last_index)
    return {
        "point_median_index": exp(last_log + innovation.location),
        "lower_90_index": exp(last_log + lower_log),
        "upper_90_index": exp(last_log + upper_log),
        "log_index_location": last_log + innovation.location,
        "log_index_scale": innovation.scale,
        "degrees_of_freedom": innovation.degrees_of_freedom,
    }

