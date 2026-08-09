from __future__ import annotations

from collections import defaultdict

import numpy as np

from bma.experiments import aeat_monthly_sequential_v0_6_3 as base
from bma.experiments.aeat_monthly_sequential_v0_6_4_resume import (
    FeatureContext,
    model_from_serialized,
    participation_from_serialized,
)
from bma.experiments.mercabarna_flor_v0_4_1 import BayesianLinearState


NAMES = [
    "intercept",
    "flow:I",
    "flow:E",
    "cn4:7201",
    "partner:FR",
    "partner:PT",
    "num:lag",
    "num:cross_product_flow",
    "num:cross_partner_flow",
    "num:gap_months",
    "num:lag_available",
    "num:month_sin",
    "num:month_cos",
    "num:year_end",
    "num:lag_weight",
]


def row(cell: str, flow: str, partner: str, weight: float, value: float) -> dict[str, object]:
    return {
        "cell_id": cell,
        "flow": flow,
        "cn8": "72011000",
        "cn4": "7201",
        "partner_country": partner,
        "weight_kg": weight,
        "statistical_unit_value_eur_per_kg": value,
    }


def test_serialized_model_roundtrip_is_exact() -> None:
    model = BayesianLinearState.prior(NAMES, 2.5, 1.75)
    design = np.vstack([np.ones(len(NAMES)), np.arange(len(NAMES), dtype=float)])
    model.update(design, np.asarray([1.0, 2.0]))
    restored = model_from_serialized(model.serializable())
    assert restored.serializable() == model.serializable()


def test_serialized_participation_roundtrip_is_exact() -> None:
    rows = [row("I|72011000|FR", "I", "FR", 10.0, 2.0), row("E|72011000|PT", "E", "PT", 20.0, 3.0)]
    state = base.ParticipationState()
    state.admit(rows)
    state.update({"I|72011000|FR"})
    restored = participation_from_serialized(state.serializable())
    assert restored.serializable() == state.serializable()


def test_precomputed_features_equal_original_repeated_scan() -> None:
    first = row("I|72011000|FR", "I", "FR", 10.0, 2.0)
    second = row("E|72011000|PT", "E", "PT", 20.0, 4.0)
    history = defaultdict(list)
    history[str(first["cell_id"])].append({**first, "period": "2024-01"})
    history[str(second["cell_id"])].append({**second, "period": "2024-01"})
    state = base.MonthlyState(
        BayesianLinearState.prior(NAMES, 1.0, 1.0),
        BayesianLinearState.prior(NAMES, 1.0, 1.0),
        history,
        {str(first["cell_id"]): first, str(second["cell_id"]): second},
    )
    for variable, center, scale in (("weight_kg", 2.0, 1.5), ("statistical_unit_value_eur_per_kg", 1.0, 0.75)):
        context = FeatureContext(state, "2024-02", variable, NAMES, center, scale, 2.0, 1.5)
        for candidate in (first, second):
            expected = base.build_features(candidate, "2024-02", variable, state, NAMES, center, scale, 2.0, 1.5)
            assert np.array_equal(context.design(candidate), expected)
