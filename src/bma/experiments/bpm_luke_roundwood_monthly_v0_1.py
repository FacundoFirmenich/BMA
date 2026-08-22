"""Frozen, source-agnostic core for the Luke roundwood monthly campaign.

The module does not perform transport access.  It models one exact Finland x
sale-type x assortment jurisdiction and exposes only post-freeze, one-month-
ahead state transitions.  Quantity and price must use distinct TargetState
instances; no evidence is pooled across targets or jurisdictions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

import numpy as np
from scipy.special import logsumexp
from scipy.stats import t as student_t


SCHEMA = "bpm.luke.roundwood.monthly.v0.1"
MODEL_IDS = ("M0", "M1", "M2")
TARGET_IDS = ("volume", "price")
PROBABILITY_FLOOR = 1e-12
HARMONIC_PRECISION = (16.0, 16.0, 24.0, 24.0)
MONTH_RESIDUAL_PRECISION = 48.0
BASE_PRECISION = (16.0, 8.0)
TARGET_PRIORS = {
    "volume": {"a0": 3.0, "b0": 0.5},
    "price": {"a0": 3.0, "b0": 0.02},
}


class GateFailure(RuntimeError):
    """Raised when chronology, support or mutation authority is violated."""


def month_index(period: str) -> int:
    try:
        year_text, month_text = period.split("-")
        year, month = int(year_text), int(month_text)
    except (ValueError, AttributeError) as exc:
        raise GateFailure(f"invalid monthly period {period!r}") from exc
    if year < 1 or not 1 <= month <= 12 or period != f"{year:04d}-{month:02d}":
        raise GateFailure(f"invalid monthly period {period!r}")
    return year * 12 + month


def require_next_month(training_period: str, target_period: str) -> None:
    if month_index(target_period) - month_index(training_period) != 1:
        raise GateFailure("Luke campaign permits exactly one calendar month ahead")


def calendar_month(period: str) -> int:
    month_index(period)
    return int(period[-2:])


def harmonic_basis(month: int) -> np.ndarray:
    if not 1 <= month <= 12:
        raise GateFailure("month must be in 1..12")
    phase = 2.0 * math.pi * (month - 1) / 12.0
    return np.asarray(
        [math.sin(phase), math.cos(phase), math.sin(2.0 * phase), math.cos(2.0 * phase)],
        dtype=float,
    )


def zero_sum_month_basis(month: int) -> np.ndarray:
    """Eleven contrasts whose implied twelve calendar effects sum to zero."""
    if not 1 <= month <= 12:
        raise GateFailure("month must be in 1..12")
    if month == 12:
        return np.full(11, -1.0, dtype=float)
    result = np.zeros(11, dtype=float)
    result[month - 1] = 1.0
    return result


def design_vector(model_id: str, previous_delta: float, target_period: str) -> np.ndarray:
    if not math.isfinite(previous_delta):
        raise GateFailure("previous innovation must be finite")
    base = np.asarray([1.0, previous_delta], dtype=float)
    if model_id == "M0":
        return base
    harmonic = harmonic_basis(calendar_month(target_period))
    if model_id == "M1":
        return np.concatenate((base, harmonic))
    if model_id == "M2":
        return np.concatenate((base, harmonic, zero_sum_month_basis(calendar_month(target_period))))
    raise GateFailure(f"unknown model {model_id!r}")


def prior_precision(model_id: str) -> np.ndarray:
    diagonal = list(BASE_PRECISION)
    if model_id in {"M1", "M2"}:
        diagonal.extend(HARMONIC_PRECISION)
    if model_id == "M2":
        diagonal.extend([MONTH_RESIDUAL_PRECISION] * 11)
    if model_id not in MODEL_IDS:
        raise GateFailure(f"unknown model {model_id!r}")
    return np.diag(np.asarray(diagonal, dtype=float))


@dataclass(frozen=True)
class StudentTPredictive:
    location: float
    scale: float
    degrees_of_freedom: float

    def logpdf(self, value: float) -> float:
        if not math.isfinite(value):
            raise GateFailure("outcome must be finite")
        return float(student_t.logpdf(value, self.degrees_of_freedom, loc=self.location, scale=self.scale))

    def interval(self, mass: float = 0.90) -> tuple[float, float]:
        if not 0.0 < mass < 1.0:
            raise GateFailure("interval mass must lie in (0,1)")
        tail = (1.0 - mass) / 2.0
        return (
            float(student_t.ppf(tail, self.degrees_of_freedom, loc=self.location, scale=self.scale)),
            float(student_t.ppf(1.0 - tail, self.degrees_of_freedom, loc=self.location, scale=self.scale)),
        )


@dataclass
class BayesianLinearState:
    precision: np.ndarray
    information: np.ndarray
    a: float
    b: float
    updates: int = 0

    @classmethod
    def frozen_prior(cls, target_id: str, model_id: str) -> "BayesianLinearState":
        if target_id not in TARGET_PRIORS:
            raise GateFailure(f"unknown target {target_id!r}")
        precision = prior_precision(model_id)
        return cls(
            precision=precision,
            information=np.zeros(precision.shape[0], dtype=float),
            a=float(TARGET_PRIORS[target_id]["a0"]),
            b=float(TARGET_PRIORS[target_id]["b0"]),
        )

    def mean(self) -> np.ndarray:
        return np.linalg.solve(self.precision, self.information)

    def predict_delta(self, design: np.ndarray) -> StudentTPredictive:
        if design.shape != self.information.shape:
            raise GateFailure("design dimension does not match posterior")
        mean = self.mean()
        location = float(design @ mean)
        leverage = float(design @ np.linalg.solve(self.precision, design))
        scale_squared = (self.b / self.a) * (1.0 + leverage)
        if not math.isfinite(scale_squared) or scale_squared <= 0.0:
            raise GateFailure("invalid predictive variance")
        return StudentTPredictive(location, math.sqrt(scale_squared), 2.0 * self.a)

    def update_after_adjudication(self, design: np.ndarray, delta: float) -> None:
        if design.shape != self.information.shape or not math.isfinite(delta):
            raise GateFailure("invalid post-outcome Bayesian update")
        old_mean = self.mean()
        old_quadratic = float(old_mean @ self.precision @ old_mean)
        new_precision = self.precision + np.outer(design, design)
        new_information = self.information + design * delta
        new_mean = np.linalg.solve(new_precision, new_information)
        new_quadratic = float(new_mean @ new_precision @ new_mean)
        new_b = self.b + 0.5 * (delta * delta + old_quadratic - new_quadratic)
        if not math.isfinite(new_b) or new_b <= 0.0:
            raise GateFailure("invalid inverse-gamma scale after update")
        self.precision = new_precision
        self.information = new_information
        self.a += 0.5
        self.b = new_b
        self.updates += 1


@dataclass
class PrequentialWeights:
    log_evidence: dict[str, float] = field(default_factory=lambda: {model_id: 0.0 for model_id in MODEL_IDS})

    def probabilities(self) -> dict[str, float]:
        values = np.asarray([self.log_evidence[model_id] for model_id in MODEL_IDS], dtype=float)
        probabilities = np.exp(values - logsumexp(values))
        return {model_id: float(probabilities[index]) for index, model_id in enumerate(MODEL_IDS)}

    def update_after_adjudication(self, log_scores: Mapping[str, float]) -> None:
        if set(log_scores) != set(MODEL_IDS):
            raise GateFailure("weights require one post-outcome score for M0/M1/M2")
        for model_id, score in log_scores.items():
            if not math.isfinite(score):
                raise GateFailure("non-finite prequential log score")
            self.log_evidence[model_id] += float(score)


@dataclass(frozen=True)
class FrozenPrediction:
    training_period: str
    target_period: str
    target_id: str
    previous_level: float
    previous_delta: float
    bootstrap_seasonality: bool
    weights: dict[str, float]
    components: dict[str, StudentTPredictive]
    mixture_location: float

    def component_log_scores(self, realized_level: float) -> dict[str, float]:
        return {model_id: predictive.logpdf(realized_level) for model_id, predictive in self.components.items()}

    def mixture_log_score(self, realized_level: float) -> float:
        terms = [
            math.log(max(self.weights[model_id], PROBABILITY_FLOOR)) + predictive.logpdf(realized_level)
            for model_id, predictive in self.components.items()
        ]
        return float(logsumexp(np.asarray(terms, dtype=float)))


@dataclass
class TargetState:
    target_id: str
    models: dict[str, BayesianLinearState]
    weights: PrequentialWeights = field(default_factory=PrequentialWeights)
    last_period: str | None = None
    updates: int = 0

    @classmethod
    def frozen_prior(cls, target_id: str) -> "TargetState":
        if target_id not in TARGET_IDS:
            raise GateFailure(f"unknown target {target_id!r}")
        return cls(
            target_id=target_id,
            models={model_id: BayesianLinearState.frozen_prior(target_id, model_id) for model_id in MODEL_IDS},
        )

    def freeze_prediction(
        self,
        training_period: str,
        target_period: str,
        previous_level: float,
        previous_delta: float,
        *,
        bootstrap_seasonality: bool,
    ) -> FrozenPrediction:
        require_next_month(training_period, target_period)
        if self.last_period is not None and self.last_period != training_period:
            raise GateFailure("posterior period does not match requested training period")
        if not math.isfinite(previous_level):
            raise GateFailure("previous transformed level must be finite")
        actual_components: dict[str, StudentTPredictive] = {}
        for model_id in MODEL_IDS:
            design = design_vector(model_id, previous_delta, target_period)
            delta_prediction = self.models[model_id].predict_delta(design)
            actual_components[model_id] = StudentTPredictive(
                previous_level + delta_prediction.location,
                delta_prediction.scale,
                delta_prediction.degrees_of_freedom,
            )
        if bootstrap_seasonality:
            components = {model_id: actual_components["M0"] for model_id in MODEL_IDS}
        else:
            components = actual_components
        probabilities = self.weights.probabilities()
        mixture_location = sum(probabilities[model_id] * components[model_id].location for model_id in MODEL_IDS)
        return FrozenPrediction(
            training_period=training_period,
            target_period=target_period,
            target_id=self.target_id,
            previous_level=previous_level,
            previous_delta=previous_delta,
            bootstrap_seasonality=bootstrap_seasonality,
            weights=probabilities,
            components=components,
            mixture_location=float(mixture_location),
        )

    def update_after_adjudication(
        self,
        freeze: FrozenPrediction,
        realized_level: float,
        *,
        update_weight_evidence: bool = True,
    ) -> dict[str, float]:
        if freeze.target_id != self.target_id:
            raise GateFailure("freeze target does not match posterior target")
        if self.last_period is not None and self.last_period != freeze.training_period:
            raise GateFailure("freeze is not based on the current posterior")
        log_scores = freeze.component_log_scores(realized_level)
        if update_weight_evidence:
            self.weights.update_after_adjudication(log_scores)
        realized_delta = realized_level - freeze.previous_level
        for model_id in MODEL_IDS:
            design = design_vector(model_id, freeze.previous_delta, freeze.target_period)
            self.models[model_id].update_after_adjudication(design, realized_delta)
        self.last_period = freeze.target_period
        self.updates += 1
        return log_scores


def transform_observation(target_id: str, raw_value: float) -> float:
    if not math.isfinite(raw_value):
        raise GateFailure("raw observation must be finite")
    if target_id == "volume":
        if raw_value < 0.0:
            raise GateFailure("volume cannot be negative")
        return math.log1p(raw_value)
    if target_id == "price":
        if raw_value <= 0.0:
            raise GateFailure("price must be strictly positive")
        return math.log(raw_value)
    raise GateFailure(f"unknown target {target_id!r}")


def inverse_transform(target_id: str, transformed_value: float) -> float:
    if target_id == "volume":
        return max(0.0, math.expm1(transformed_value))
    if target_id == "price":
        return math.exp(transformed_value)
    raise GateFailure(f"unknown target {target_id!r}")
