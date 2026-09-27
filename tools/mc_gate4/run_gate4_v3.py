#!/usr/bin/env python3
"""Gate 4 v3 contract overlay.

Pins the exact official series selected after inspecting the official search
responses. The quarterly employment series is acquired but is not silently
upsampled; the monthly Gamma employment cells therefore remain eligible to
abstain.
"""
from __future__ import annotations

import acquire_compact as core

# Exact official series contracts selected after source-level audit.
core.SERIES["wage_index"] = ("149.1_SOR_PRIADO_OCTU_0_25", "native")
core.SERIES["registered_employment_quarterly"] = ("155.2_TLTAL_S_0_0_5", "native")

# Employment is observed at quarterly frequency. Reusing it in a monthly
# response matrix is allowed only through the existing support gate, which is
# expected to abstain rather than interpolate.
core.DIMS["E"] = (
    "registered_employment_quarterly",
    "registered_private_employment_quarterly_no_upsampling",
)

# The exact IDs above supersede heuristic discovery for this frozen round.
core.SEARCH.clear()

if __name__ == "__main__":
    core.main()
