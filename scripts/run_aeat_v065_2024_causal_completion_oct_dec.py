#!/usr/bin/env python3
"""Continue the sealed September 2024 posterior through December 2024."""
from __future__ import annotations

import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from bma.experiments import aeat_monthly_seasonal_v0_6_5_runtime as seasonal


REPOSITORY = Path(r"C:\Users\User\Documents\Codex\2026-08-09\analiza-y-estudia-por-completo-este\BMA")
CORE_RUNNER = REPOSITORY / "scripts" / "run_aeat_v065_2024_causal_mini.py"
MINI_2024 = REPOSITORY / "evidence/runs/aeat-ch72-monthly-seasonal-v0.6.5-2024-causal-mini-jan-sep"
PREREGISTRATION = REPOSITORY / "preregistrations/AEAT_CH72_SEASONAL_2024_CAUSAL_COMPLETION_OCT_DEC_V0_6_5.json"
OUTPUT = REPOSITORY / "evidence/runs/aeat-ch72-monthly-seasonal-v0.6.5-2024-causal-completion-oct-dec"


def load_core():
    spec = importlib.util.spec_from_file_location("bma_aeat_v065_2024_completion_core", CORE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CORE_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure(core):
    def update_from_2024(
        states: dict[str, seasonal.SeasonalState],
        reconstructed_weights: dict[str, seasonal.PrequentialWeights],
    ) -> None:
        for month in range(1, 10):
            period = f"2024-{month:02d}"
            adjudication = core.read_gzip(MINI_2024 / "adjudications" / f"adjudication_{period}.json.gz")
            for row in adjudication["participation"]:
                cell = core.cell_from_id(str(row["cell_id"]))
                innovation = int(row["actual"]) - float(row["models"]["M0"]["probability"])
                states["participation"].update_after_adjudication(cell, period, innovation)
            for label, variable in (
                ("quantity", "weight_kg"),
                ("unit_value", "statistical_unit_value_eur_per_kg"),
            ):
                for row in adjudication[label]:
                    innovation = core.base.transformed(float(row["actual"]), variable) - core.base.transformed(
                        float(row["models"]["M0"]["point"]), variable
                    )
                    states[label].update_after_adjudication(
                        core.cell_from_id(str(row["cell_id"])), period, innovation
                    )
            for label in reconstructed_weights:
                reconstructed_weights[label].update_after_adjudication(
                    adjudication["post_outcome_log_scores"][label]
                )

    def seed_from_september(source_2022: Path, source_2023: Path):
        prior_path = MINI_2024 / "priors/prior_after_2024-09_ORDINARY.json.gz"
        z_post_path = MINI_2024 / "z_post/z_post_2024-09.json"
        z_post = json.loads(z_post_path.read_text(encoding="utf-8"))
        if core.sha256_file(prior_path) != z_post["future_prior_sha256"]:
            raise core.base.GateFailure("September 2024 posterior is not sealed by Z_post")
        prior = core.read_gzip(prior_path)
        if prior["compiled_from_target"] != "2024-09":
            raise core.base.GateFailure("wrong terminal posterior for October continuation")

        january_2022 = core.read_gzip(source_2022 / "structured_months/month_2022-01.json.gz")
        _, _, names, scales = core.base.initialize(january_2022)
        history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        known: dict[str, dict[str, Any]] = {}
        sources = (
            (2022, range(1, 13), source_2022),
            (2023, range(1, 13), source_2023),
            (2024, range(1, 10), MINI_2024),
        )
        for year, months, source in sources:
            for month in months:
                document = core.read_gzip(source / "structured_months" / f"month_{year}-{month:02d}.json.gz")
                for row in document["cells"]:
                    history[str(row["cell_id"])].append({**row, "period": document["period"]})
                    known[str(row["cell_id"])] = row

        state = core.base.MonthlyState(
            core.model_from_serialized(prior["m0_state"]["quantity"]),
            core.model_from_serialized(prior["m0_state"]["unit_value"]),
            history,
            known,
        )
        participation = core.participation_from_serialized(prior["m0_state"]["participation"])
        states = {
            "participation": seasonal.SeasonalState(),
            "quantity": seasonal.SeasonalState(),
            "unit_value": seasonal.SeasonalState(),
        }
        core.update_seasonal_from_2022(states, source_2022)
        reconstructed_weights = {
            key: seasonal.PrequentialWeights() for key in ("participation", "quantity", "unit_value")
        }
        core.update_seasonal_and_weights_from_2023(states, reconstructed_weights, source_2023)
        update_from_2024(states, reconstructed_weights)

        weights: dict[str, seasonal.PrequentialWeights] = {}
        for label, stored in prior["seasonal_weights"].items():
            stored_float = {model: float(value) for model, value in stored.items()}
            reconstructed = reconstructed_weights[label].log_evidence
            if any(
                not math.isclose(stored_float[model], reconstructed[model], rel_tol=0.0, abs_tol=1e-8)
                for model in seasonal.MODEL_IDS
            ):
                raise core.base.GateFailure(f"stored and reconstructed September weights differ for {label}")
            weights[label] = seasonal.PrequentialWeights(log_evidence=stored_float)

        recovery = {
            "terminal_prior_sha256": core.sha256_file(prior_path),
            "terminal_z_post_sha256": core.sha256_file(z_post_path),
            "mini_2024_manifest_sha256": core.sha256_file(MINI_2024 / "MANIFEST_SHA256.txt"),
            "weights_reconciled": True,
            "seasonal_innovation_order": "2022-02..2022-12 then 2023-01..2023-12 then 2024-01..2024-09",
        }
        return state, participation, names, scales, states, weights, recovery

    original_gzip_new = core.gzip_new

    def gzip_new_with_year_end(path: Path, value: Any) -> str:
        if path.name == "freeze_2024-12.json.gz":
            value = {**value, "regime": "YEAR_END_UNCALIBRATED"}
        if path.name == "prior_after_2024-12_ORDINARY.json.gz":
            path = path.with_name("prior_after_2024-12_YEAR_END_UNCALIBRATED.json.gz")
            value = {**value, "regime": "YEAR_END_UNCALIBRATED"}
        return original_gzip_new(path, value)

    original_write_json_new = core.write_json_new

    def write_json_new_with_completion_receipt(path: Path, value: Any) -> None:
        if path.name == "RESULT.json":
            value = {
                **value,
                "status": "EXECUTED_RETROSPECTIVE_CAUSAL_COMPLETION_2024_OCT_DEC",
                "month_regimes": {
                    "2024-10": "ORDINARY",
                    "2024-11": "ORDINARY",
                    "2024-12": "YEAR_END_UNCALIBRATED",
                },
                "continuation_source_manifest_sha256": core.sha256_file(MINI_2024 / "MANIFEST_SHA256.txt"),
                "claim_boundary": {
                    "aggregate_winner": None,
                    "promotion": "PROHIBITED",
                    "prospective_validation": False,
                    "blindness": False,
                    "december_primary_adjudication": "ABSTAIN",
                },
            }
        original_write_json_new(path, value)

    core.FIRST_MONTH = 10
    core.LAST_MONTH = 12
    core.SCHEMA = "bma.aeat.chapter72.monthly-seasonal.causal-completion-2024.v0.6.5"
    core.PREREGISTRATION = PREREGISTRATION
    core.seed_from_2023 = seed_from_september
    core.gzip_new = gzip_new_with_year_end
    core.write_json_new = write_json_new_with_completion_receipt
    core.__file__ = __file__
    return core


if __name__ == "__main__":
    runner = configure(load_core())
    runner.run(
        REPOSITORY / "evidence/runs/aeat-ch72-monthly-sequential-v0.6.5-2022-bootstrap-r2",
        REPOSITORY / "evidence/runs/aeat-ch72-monthly-seasonal-v0.6.5-2023-causal",
        REPOSITORY / "evidence/runs/aeat-ch72-monthly-sequential-v0.6.4",
        OUTPUT,
    )
