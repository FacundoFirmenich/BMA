"""Frozen v0.6.5 seasonal components; intentionally no AEAT transport access.

The runner is assembled only after the software addendum is hashed.  This
module operates on already admissible, one-month-ahead innovations and makes
the chronology and state transitions testable without opening 2022--2023.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from bma.experiments import aeat_monthly_sequential_v0_6_4 as m0

SCHEMA = "bma.aeat.chapter72.monthly-seasonal.v0.6.5"
MODEL_IDS = ("M0", "M1", "M2")
SUPPORT_THRESHOLDS = {"global": 1, "flow": 3, "cn4": 6, "partner": 6, "cell": 12}
LOG_SCORE_FLOOR = 1e-12


class GateFailure(RuntimeError):
    pass


def calendar_phase(period: str) -> int:
    """Return the calendar month and reject malformed/non-monthly periods."""
    try:
        year, month = period.split("-")
        parsed_year, parsed_month = int(year), int(month)
    except ValueError as exc:
        raise GateFailure(f"invalid monthly period {period!r}") from exc
    if not 1 <= parsed_month <= 12 or parsed_year < 1:
        raise GateFailure(f"invalid monthly period {period!r}")
    return parsed_month


def require_next_month(training_period: str, target_period: str) -> None:
    def index(period: str) -> int:
        year, month = period.split("-")
        return int(year) * 12 + int(month)

    if index(target_period) - index(training_period) != 1:
        raise GateFailure("v0.6.5 permits exactly one calendar month ahead")


def m0_features(*args: object, **kwargs: object) -> np.ndarray:
    """Exact M0 delegation: v0.6.5 cannot silently alter the v0.6.4 control."""
    return m0.build_features(*args, **kwargs)  # type: ignore[arg-type]


def harmonic_basis(month: int) -> np.ndarray:
    if not 1 <= month <= 12:
        raise GateFailure("month must be in 1..12")
    phase = 2.0 * math.pi * (month - 1) / 12.0
    return np.asarray([math.sin(phase), math.cos(phase), math.sin(2 * phase), math.cos(2 * phase)])


@dataclass
class PrequentialWeights:
    """Separate, post-outcome-only Bayesian model weights for one target."""
    log_evidence: dict[str, float] = field(default_factory=lambda: {model: 0.0 for model in MODEL_IDS})

    def probabilities(self) -> dict[str, float]:
        values = np.asarray([self.log_evidence[model] for model in MODEL_IDS], dtype=float)
        values -= float(np.max(values))
        normalizer = float(np.exp(values).sum())
        return {model: float(math.exp(self.log_evidence[model] - float(np.max(np.asarray([self.log_evidence[m] for m in MODEL_IDS])))) / normalizer) for model in MODEL_IDS}

    def update_after_adjudication(self, log_scores: dict[str, float]) -> None:
        if set(log_scores) != set(MODEL_IDS):
            raise GateFailure("weights require one post-outcome log score per M0/M1/M2")
        for model, score in log_scores.items():
            if not math.isfinite(score):
                raise GateFailure("non-finite prequential log score")
            self.log_evidence[model] += score


@dataclass
class SeasonalState:
    """Causal harmonic plus hierarchical zero-sum monthly innovation memory."""
    ridge: float = 4.0
    residual_shrinkage: float = 8.0
    harmonic_xtx: np.ndarray = field(default_factory=lambda: np.eye(4) * 4.0)
    harmonic_xty: np.ndarray = field(default_factory=lambda: np.zeros(4))
    residual_sum: dict[str, np.ndarray] = field(default_factory=lambda: defaultdict(lambda: np.zeros(12)))
    residual_count: dict[str, np.ndarray] = field(default_factory=lambda: defaultdict(lambda: np.zeros(12)))

    @staticmethod
    def hierarchy_keys(cell: dict[str, str]) -> tuple[str, ...]:
        required = ("flow", "cn4", "partner_country", "cell_id")
        if any(not cell.get(key) for key in required):
            raise GateFailure("seasonal hierarchy requires flow, CN4, partner and cell")
        return (
            "global:GLOBAL",
            f"flow:{cell['flow']}",
            f"cn4:{cell['flow']}|{cell['cn4']}",
            f"partner:{cell['flow']}|{cell['partner_country']}",
            f"cell:{cell['cell_id']}",
        )

    def harmonic(self, month: int) -> float:
        beta = np.linalg.solve(self.harmonic_xtx + np.eye(4) * self.ridge, self.harmonic_xty)
        return float(harmonic_basis(month) @ beta)

    def residual(self, cell: dict[str, str], month: int) -> float:
        position = month - 1
        inherited = 0.0
        for level, key in zip(("global", "flow", "cn4", "partner", "cell"), self.hierarchy_keys(cell)):
            count = float(self.residual_count[key][position])
            if count < SUPPORT_THRESHOLDS[level]:
                continue
            local = float(self.residual_sum[key][position] / count)
            inherited = (count * local + self.residual_shrinkage * inherited) / (count + self.residual_shrinkage)
        return inherited

    def prediction_delta(self, cell: dict[str, str], target_period: str, model: str) -> float:
        month = calendar_phase(target_period)
        if model == "M0":
            return 0.0
        if model == "M1":
            return self.harmonic(month)
        if model == "M2":
            return self.harmonic(month) + self.residual(cell, month)
        raise GateFailure(f"unknown model {model!r}")

    def update_after_adjudication(self, cell: dict[str, str], target_period: str, innovation: float) -> None:
        if not math.isfinite(innovation):
            raise GateFailure("innovation must be finite")
        month = calendar_phase(target_period)
        basis = harmonic_basis(month)
        self.harmonic_xtx += np.outer(basis, basis)
        self.harmonic_xty += basis * innovation
        residual = innovation - self.harmonic(month)
        position = month - 1
        for key in self.hierarchy_keys(cell):
            self.residual_sum[key][position] += residual
            self.residual_count[key][position] += 1.0
        self._assert_zero_sum()

    def _assert_zero_sum(self) -> None:
        for key, totals in self.residual_sum.items():
            counts = self.residual_count[key]
            active = counts > 0
            if active.any():
                weighted_mean = float(totals[active].sum() / counts[active].sum())
                self.residual_sum[key][active] -= weighted_mean * counts[active]
        for totals, counts in zip(self.residual_sum.values(), self.residual_count.values()):
            active = counts > 0
            if active.any() and abs(float(totals[active].sum())) > 1e-10:
                raise GateFailure("monthly residuals violate their weighted zero-sum invariant")

def mixture_location(m0_location: float, state: SeasonalState, cell: dict[str, str], target_period: str, weights: PrequentialWeights) -> float:
    probabilities = weights.probabilities()
    return sum(probabilities[model] * (m0_location + state.prediction_delta(cell, target_period, model)) for model in MODEL_IDS)


def update_models_after_target(states: Iterable[SeasonalState], cell: dict[str, str], training_period: str, target_period: str, innovation: float) -> None:
    """The only legal update location: after the corresponding target outcome."""
    require_next_month(training_period, target_period)
    for state in states:
        state.update_after_adjudication(cell, target_period, innovation)
