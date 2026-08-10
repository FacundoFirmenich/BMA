"""Execution-safe v0.6.5 seasonal state.

This amendment is algebraically equivalent to the frozen core's centering
rule: a new innovation changes only its own global/flow/CN4/partner/cell
nodes, therefore only those five nodes need re-centering.  Scanning every
previously seen node after each cell is quadratic and cannot execute AEAT.
"""
from __future__ import annotations

import math

import numpy as np

from bma.experiments import aeat_monthly_seasonal_v0_6_5 as frozen

SCHEMA = "bma.aeat.chapter72.monthly-seasonal.runtime.v0.6.5"
MODEL_IDS = frozen.MODEL_IDS
LOG_SCORE_FLOOR = frozen.LOG_SCORE_FLOOR
PrequentialWeights = frozen.PrequentialWeights
GateFailure = frozen.GateFailure
calendar_phase = frozen.calendar_phase
harmonic_basis = frozen.harmonic_basis


class SeasonalState(frozen.SeasonalState):
    def update_after_adjudication(self, cell: dict[str, str], target_period: str, innovation: float) -> None:
        if not math.isfinite(innovation):
            raise GateFailure("innovation must be finite")
        month = calendar_phase(target_period)
        basis = harmonic_basis(month)
        self.harmonic_xtx += np.outer(basis, basis)
        self.harmonic_xty += basis * innovation
        residual = innovation - self.harmonic(month)
        position = month - 1
        keys = self.hierarchy_keys(cell)
        for key in keys:
            self.residual_sum[key][position] += residual
            self.residual_count[key][position] += 1.0
        for key in keys:
            totals = self.residual_sum[key]
            counts = self.residual_count[key]
            active = counts > 0
            weighted_mean = float(totals[active].sum() / counts[active].sum())
            totals[active] -= weighted_mean * counts[active]
            if abs(float(totals[active].sum())) > 1e-10:
                raise GateFailure("monthly residuals violate their weighted zero-sum invariant")
