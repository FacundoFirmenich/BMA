from __future__ import annotations

from bma.experiments.aeat_monthly_sequential_v0_6_4 import (
    StructurallyExtensibleFrozenParticipation,
)


def test_structural_admission_does_not_add_outcome_evidence() -> None:
    state = StructurallyExtensibleFrozenParticipation()
    state.predict("I|72083900|DE")
    assert state.last == {}
    assert sum(sum(values.values()) for values in state.success.values()) == 0
    assert sum(sum(values.values()) for values in state.trials.values()) == 0
