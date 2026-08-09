#!/usr/bin/env python3
"""Pre-execution gate correction for AEAT monthly sequential replay v0.6.3.

v0.6.3 was never run on real data: its tests found that the January-frozen
participation control could not structurally represent later first-appearance
cells and that source-period identity was not asserted at the fetch boundary.
This revision fixes both conditions while preserving the 1 month -> 1 month
engine unchanged.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from bma.experiments import aeat_monthly_sequential_v0_6_3 as base

SCHEMA = "bma.aeat.chapter72.monthly-sequential.v0.6.4"
GateFailure = base.GateFailure
one_to_one_transitions = base.one_to_one_transitions
build_features = base.build_features
initialize = base.initialize
ParticipationState = base.ParticipationState

# Exposed as a module attribute so tests can replace transport without network.
fetch_month = base.fetch_month


class StructurallyExtensibleFrozenParticipation(base.ParticipationState):
    """A frozen control may learn identity/support, never later outcomes."""

    def predict(self, cell_id: str) -> float:
        if cell_id not in self.metadata:
            pieces = cell_id.split("|")
            if len(pieces) != 3 or len(pieces[1]) < 4:
                raise GateFailure(f"invalid AEAT cell identity {cell_id!r}")
            flow, cn8, partner = pieces
            self.metadata[cell_id] = {
                "flow": flow,
                "cn8": cn8,
                "cn4": cn8[:4],
                "partner_country": partner,
            }
        return super().predict(cell_id)


def run(output: Path) -> dict[str, Any]:
    transport = fetch_month

    def guarded_fetch(year: int, month: int) -> dict[str, Any]:
        document = transport(year, month)
        expected = f"{year:04d}-{month:02d}"
        if document.get("period") != expected:
            raise GateFailure(
                f"target period mismatch {document.get('period')!r} != {expected!r}"
            )
        return document

    old_schema = base.SCHEMA
    old_fetch = base.fetch_month
    old_participation = base.ParticipationState
    base.SCHEMA = SCHEMA
    base.fetch_month = guarded_fetch
    base.ParticipationState = StructurallyExtensibleFrozenParticipation
    try:
        result = base.run(output)
    finally:
        base.SCHEMA = old_schema
        base.fetch_month = old_fetch
        base.ParticipationState = old_participation
    if result.get("schema_version") != SCHEMA:
        raise GateFailure("v0.6.4 schema identity was not propagated")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(f"status={result['status']} transitions={result['transition_count']}")


if __name__ == "__main__":
    main()
