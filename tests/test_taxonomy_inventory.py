from __future__ import annotations

from bma.taxonomy import AMBIGUOUS, ARBOLES_Y_VERDES, COMPLEMENTOS, FLOR_CORTADA, PLANTA_VIVA


def test_frozen_training_inventory_is_complete_and_disjoint() -> None:
    groups = [FLOR_CORTADA, PLANTA_VIVA, ARBOLES_Y_VERDES, COMPLEMENTOS, AMBIGUOUS]
    assert [len(group) for group in groups] == [36, 22, 23, 13, 4]
    assert len(set().union(*groups)) == 98
    for index, left in enumerate(groups):
        for right in groups[index + 1 :]:
            assert left.isdisjoint(right)
