#!/usr/bin/env python3
"""Attempt 2 for the October--December causal completion."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from bma.experiments import aeat_monthly_seasonal_v0_6_5 as seasonal_frozen
from bma.experiments import aeat_monthly_seasonal_v0_6_5_runtime as seasonal_runtime


REPOSITORY = Path(r"C:\Users\User\Documents\Codex\2026-08-09\analiza-y-estudia-por-completo-este\BMA")
COMPLETION = REPOSITORY / "scripts/run_aeat_v065_2024_causal_completion_oct_dec.py"


def load_completion():
    spec = importlib.util.spec_from_file_location("bma_aeat_v065_2024_completion_attempt2_core", COMPLETION)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {COMPLETION}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    seasonal_runtime.require_next_month = seasonal_frozen.require_next_month
    completion = load_completion()
    runner = completion.configure(completion.load_core())
    runner.__file__ = __file__
    runner.run(
        REPOSITORY / "evidence/runs/aeat-ch72-monthly-sequential-v0.6.5-2022-bootstrap-r2",
        REPOSITORY / "evidence/runs/aeat-ch72-monthly-seasonal-v0.6.5-2023-causal",
        REPOSITORY / "evidence/runs/aeat-ch72-monthly-sequential-v0.6.4",
        REPOSITORY / "evidence/runs/aeat-ch72-monthly-seasonal-v0.6.5-2024-causal-completion-oct-dec",
    )
