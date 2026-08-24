"""Causal local models for BPM-RMK timber auctions.

This module has no transport or workbook access.  It only consumes observations
that were independently frozen as comparable product-location-phase cells.
Historical 2023-2024 eligibility rows are deliberately not accepted here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable


MODEL_IDS = ("M0", "M1", "M2")
MIN_M1_OBSERVATIONS = 3
MIN_M0_TRANSITIONS = 3
MIN_M2_PHASE_INNOVATIONS = 2
PROBABILITY_FLOOR = 1e-12


class NotEstimable(RuntimeError):
    """A preregistered support or comparability gate is not satisfied."""


@dataclass(frozen=True)
class StudentTPredictive:
    location: float
    scale: float
    degrees_of_freedom: int

    def logpdf(self, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        nu = float(self.degrees_of_freedom)
        z = (value - self.location) / self.scale
        return (
            math.lgamma((nu + 1.0) / 2.0)
            - math.lgamma(nu / 2.0)
            - 0.5 * math.log(nu * math.pi)
            - math.log(self.scale)
            - ((nu + 1.0) / 2.0) * math.log1p((z * z) / nu)
        )

    def pdf(self, value: float) -> float:
        return math.exp(self.logpdf(value))


def _require_positive(values: Iterable[float]) -> list[float]:
    data = [float(value) for value in values]
    if not data or any(not math.isfinite(value) or value <= 0.0 for value in data):
        raise ValueError("price and volume observations must be finite and positive")
    return data


def _sample_predictive(log_values: list[float], minimum: int, label: str) -> StudentTPredictive:
    if len(log_values) < minimum:
        raise NotEstimable(f"{label}_SUPPORT")
    location = sum(log_values) / len(log_values)
    sum_squares = sum((value - location) ** 2 for value in log_values)
    sample_variance = sum_squares / (len(log_values) - 1)
    if not sample_variance > 0.0:
        raise NotEstimable(f"{label}_ZERO_SCALE")
    scale = math.sqrt(sample_variance * (1.0 + 1.0 / len(log_values)))
    return StudentTPredictive(location, scale, len(log_values) - 1)


def m1_predictive(observations: Iterable[float]) -> StudentTPredictive:
    """Jeffreys-reference posterior predictive on log outcome."""
    raw = [float(value) for value in observations]
    if len(raw) < MIN_M1_OBSERVATIONS:
        raise NotEstimable("M1_SUPPORT")
    values = _require_positive(raw)
    return _sample_predictive([math.log(value) for value in values], MIN_M1_OBSERVATIONS, "M1")


def m0_point(observations: Iterable[float]) -> float:
    values = _require_positive(observations)
    return values[-1]


def m0_predictive(observations: Iterable[float]) -> StudentTPredictive:
    """Persistence location plus an objective Student-t transition-error law."""
    values = _require_positive(observations)
    if len(values) - 1 < MIN_M0_TRANSITIONS:
        raise NotEstimable("M0_DENSITY_SUPPORT")
    logs = [math.log(value) for value in values]
    transitions = [current - previous for previous, current in zip(logs, logs[1:])]
    error_law = _sample_predictive(transitions, MIN_M0_TRANSITIONS, "M0_DENSITY")
    return StudentTPredictive(logs[-1] + error_law.location, error_law.scale, error_law.degrees_of_freedom)


def canonical_phase(months: Iterable[int]) -> str:
    unique = sorted(set(int(month) for month in months))
    if not unique or any(month < 1 or month > 12 for month in unique):
        raise ValueError("delivery phase requires calendar months in 1..12")
    return "-".join(f"M{month:02d}" for month in unique)


def _adaptive_simpson(function, left: float, right: float, tolerance: float, depth: int = 20) -> float:
    midpoint = (left + right) / 2.0
    f_left, f_mid, f_right = function(left), function(midpoint), function(right)
    whole = (right - left) * (f_left + 4.0 * f_mid + f_right) / 6.0

    def recurse(a, b, fa, fm, fb, estimate, tol, remaining):
        middle = (a + b) / 2.0
        left_mid, right_mid = (a + middle) / 2.0, (middle + b) / 2.0
        f_left_mid, f_right_mid = function(left_mid), function(right_mid)
        left_estimate = (middle - a) * (fa + 4.0 * f_left_mid + fm) / 6.0
        right_estimate = (b - middle) * (fm + 4.0 * f_right_mid + fb) / 6.0
        combined = left_estimate + right_estimate
        if remaining <= 0 or abs(combined - estimate) <= 15.0 * tol:
            return combined + (combined - estimate) / 15.0
        return recurse(a, middle, fa, f_left_mid, fm, left_estimate, tol / 2.0, remaining - 1) + recurse(
            middle, b, fm, f_right_mid, fb, right_estimate, tol / 2.0, remaining - 1
        )

    return recurse(left, right, f_left, f_mid, f_right, whole, tolerance, depth)


def convolved_logpdf(first: StudentTPredictive, second: StudentTPredictive, total: float) -> float:
    """Numerical density of the sum of two independent Student-t variables."""
    center = first.location
    tangent_scale = max(first.scale, second.scale, 1e-9)
    endpoint = math.pi / 2.0 - 1e-8

    def transformed(theta: float) -> float:
        cosine = math.cos(theta)
        x_value = center + tangent_scale * math.tan(theta)
        jacobian = tangent_scale / (cosine * cosine)
        return first.pdf(x_value) * second.pdf(total - x_value) * jacobian

    density = _adaptive_simpson(transformed, -endpoint, endpoint, 1e-10)
    if not math.isfinite(density) or density <= 0.0:
        raise NotEstimable("M2_CONVOLUTION_NUMERICAL_FAILURE")
    return math.log(density)


@dataclass
class LocalOutcomeState:
    """One outcome in one exact product/standard/location cell."""

    observations: list[float] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    m1_innovations: list[tuple[str, float]] = field(default_factory=list)

    def freeze_predictions(self, phase: str) -> dict[str, dict[str, float | int | str]]:
        predictions: dict[str, dict[str, float | int | str]] = {}
        if self.observations:
            predictions["M0"] = {"point": m0_point(self.observations)}
            try:
                distribution = m0_predictive(self.observations)
                predictions["M0"].update(_distribution_payload(distribution))
            except NotEstimable as exc:
                predictions["M0"]["density_state"] = str(exc)
        else:
            predictions["M0"] = {"state": "NOT_ESTIMABLE_M0_NO_PRIOR_LOCAL_OBSERVATION"}

        try:
            m1 = m1_predictive(self.observations)
            predictions["M1"] = {"point": math.exp(m1.location), **_distribution_payload(m1)}
        except (NotEstimable, ValueError) as exc:
            predictions["M1"] = {"state": f"NOT_ESTIMABLE_{exc}"}
            return predictions | {"M2": {"state": "NOT_ESTIMABLE_M1_REQUIRED"}}

        residuals = [value for residual_phase, value in self.m1_innovations if residual_phase == phase]
        try:
            residual_distribution = _sample_predictive(residuals, MIN_M2_PHASE_INNOVATIONS, "M2_PHASE")
            predictions["M2"] = {
                "point": math.exp(m1.location + residual_distribution.location),
                "m1": _distribution_payload(m1),
                "phase_residual": _distribution_payload(residual_distribution),
                "phase_support": len(residuals),
                "density": "NUMERICAL_STUDENT_T_CONVOLUTION_ON_LOG_SCALE",
            }
        except NotEstimable as exc:
            predictions["M2"] = {"state": f"NOT_ESTIMABLE_{exc}", "phase_support": len(residuals)}
        return predictions

    def update_after_adjudication(self, phase: str, outcome: float) -> None:
        value = _require_positive([outcome])[0]
        try:
            prior_m1 = m1_predictive(self.observations)
        except NotEstimable:
            prior_m1 = None
        if prior_m1 is not None:
            self.m1_innovations.append((phase, math.log(value) - prior_m1.location))
        self.observations.append(value)
        self.phases.append(phase)


def _distribution_payload(distribution: StudentTPredictive) -> dict[str, float | int | str]:
    return {
        "density_state": "ESTIMABLE",
        "log_location": distribution.location,
        "log_scale": distribution.scale,
        "degrees_of_freedom": distribution.degrees_of_freedom,
    }


@dataclass
class CommonSupportWeights:
    """Local/outcome weights that begin only at common M0/M1/M2 density support."""

    activated: bool = False
    common_support_events: int = 0
    log_evidence: dict[str, float] = field(default_factory=lambda: {model: 0.0 for model in MODEL_IDS})

    def probabilities(self) -> dict[str, float] | None:
        if not self.activated:
            return None
        peak = max(self.log_evidence.values())
        raw = {model: math.exp(value - peak) for model, value in self.log_evidence.items()}
        total = sum(raw.values())
        return {model: value / total for model, value in raw.items()}

    def update_after_common_adjudication(self, log_scores: dict[str, float]) -> None:
        if set(log_scores) != set(MODEL_IDS) or any(not math.isfinite(score) for score in log_scores.values()):
            raise ValueError("weights require finite common-support scores for M0/M1/M2")
        if not self.activated:
            self.activated = True
        for model, score in log_scores.items():
            self.log_evidence[model] += score
        self.common_support_events += 1
