#!/usr/bin/env python3
"""Causal January--September 2024 replay from the sealed December 2023 posterior.

This run preserves the existing independently initialized 2024 baseline.  It
reconstructs seasonal memory only from sealed 2022--2023 M0 innovations,
freezes each next-month prediction, and only then opens the corresponding
already sealed 2024 structured target.  It is retrospective and not blind.
"""
from __future__ import annotations

import gzip
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from bma.custody import canonical_bytes, sha256_bytes, sha256_file, write_json_new, write_manifest
from bma.experiments import aeat_monthly_seasonal_v0_6_5_runtime as seasonal
from bma.experiments import aeat_monthly_sequential_v0_6_3 as base
from bma.experiments.aeat_monthly_sequential_v0_6_4_resume import (
    FeatureContext,
    model_from_serialized,
    participation_from_serialized,
)

YEAR = 2024
FIRST_MONTH = 1
LAST_MONTH = 9
SCHEMA = "bma.aeat.chapter72.monthly-seasonal.causal-mini-2024.v0.6.5"
PREREGISTRATION = Path("preregistrations/AEAT_CH72_SEASONAL_2024_CAUSAL_MINI_REPLAY_V0_6_5.json")


def read_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def gzip_new(path: Path, value: Any) -> str:
    if path.exists():
        raise base.GateFailure(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = gzip.compress(canonical_bytes(value), compresslevel=9, mtime=0)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def copy_gzip_new_after_freeze(source: Path, target: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    if target.exists():
        raise base.GateFailure(f"refusing to overwrite {target}")
    payload = source.read_bytes()
    observed_sha256 = sha256_bytes(payload)
    if observed_sha256 != expected_sha256:
        raise base.GateFailure(f"sealed target hash mismatch for {source}")
    document = json.loads(gzip.decompress(payload).decode("utf-8"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return document, observed_sha256


def logistic(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-35.0, min(35.0, value))))


def logit(probability: float) -> float:
    p = min(1.0 - seasonal.LOG_SCORE_FLOOR, max(seasonal.LOG_SCORE_FLOOR, probability))
    return math.log(p / (1.0 - p))


def cell_from_id(cell_id: str) -> dict[str, str]:
    flow, cn8, partner = cell_id.split("|")
    return {"cell_id": cell_id, "flow": flow, "cn4": cn8[:4], "partner_country": partner}


def adjusted_distribution(distribution: dict[str, float], variable: str, delta: float) -> dict[str, float]:
    shifted = {
        **distribution,
        "location": float(distribution["location"]) + delta,
        "lower_90": float(distribution["lower_90"]) + delta,
        "upper_90": float(distribution["upper_90"]) + delta,
    }
    return base.prediction(shifted, variable)


def parse_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for physical_line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = physical_line.split("  ", 1)
        entries[relative.replace("\\", "/")] = digest
    return entries


def update_seasonal_from_2022(
    states: dict[str, seasonal.SeasonalState], source_2022: Path
) -> None:
    for month in range(2, 13):
        period = f"2022-{month:02d}"
        adjudication = read_gzip(source_2022 / "adjudications" / f"adjudication_{period}.json.gz")
        for row in adjudication["participation"]:
            cell = cell_from_id(str(row["cell_id"]))
            innovation = int(row["actual"]) - float(row["bma_probability"])
            states["participation"].update_after_adjudication(cell, period, innovation)
        for label, key, variable in (
            ("quantity", "quantity_conditional_on_participation", "weight_kg"),
            ("unit_value", "statistical_unit_value_conditional_on_participation", "statistical_unit_value_eur_per_kg"),
        ):
            for row in adjudication[key]:
                innovation = base.transformed(float(row["actual"]), variable) - base.transformed(
                    float(row["bma_point"]), variable
                )
                states[label].update_after_adjudication(cell_from_id(str(row["cell_id"])), period, innovation)


def update_seasonal_and_weights_from_2023(
    states: dict[str, seasonal.SeasonalState],
    reconstructed_weights: dict[str, seasonal.PrequentialWeights],
    source_2023: Path,
) -> None:
    for month in range(1, 13):
        period = f"2023-{month:02d}"
        adjudication = read_gzip(source_2023 / "adjudications" / f"adjudication_{period}.json.gz")
        for row in adjudication["participation"]:
            cell = cell_from_id(str(row["cell_id"]))
            innovation = int(row["actual"]) - float(row["models"]["M0"]["probability"])
            states["participation"].update_after_adjudication(cell, period, innovation)
        for label, variable in (
            ("quantity", "weight_kg"),
            ("unit_value", "statistical_unit_value_eur_per_kg"),
        ):
            for row in adjudication[label]:
                innovation = base.transformed(float(row["actual"]), variable) - base.transformed(
                    float(row["models"]["M0"]["point"]), variable
                )
                states[label].update_after_adjudication(cell_from_id(str(row["cell_id"])), period, innovation)
        for label in reconstructed_weights:
            reconstructed_weights[label].update_after_adjudication(adjudication["post_outcome_log_scores"][label])


def seed_from_2023(
    source_2022: Path, source_2023: Path
) -> tuple[
    base.MonthlyState,
    Any,
    list[str],
    dict[str, float],
    dict[str, seasonal.SeasonalState],
    dict[str, seasonal.PrequentialWeights],
    dict[str, Any],
]:
    prior_path = source_2023 / "priors" / "prior_after_2023-12_YEAR_END_UNCALIBRATED.json.gz"
    z_post = json.loads((source_2023 / "z_post" / "z_post_2023-12.json").read_text(encoding="utf-8"))
    if sha256_file(prior_path) != z_post["future_prior_sha256"]:
        raise base.GateFailure("December 2023 posterior is not sealed by Z_post")
    prior = read_gzip(prior_path)
    if prior["compiled_from_target"] != "2023-12":
        raise base.GateFailure("wrong terminal posterior for 2024 continuation")

    january_2022 = read_gzip(source_2022 / "structured_months" / "month_2022-01.json.gz")
    _, _, names, scales = base.initialize(january_2022)
    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    known: dict[str, dict[str, Any]] = {}
    for year, source, first_month in ((2022, source_2022, 1), (2023, source_2023, 1)):
        for month in range(first_month, 13):
            document = read_gzip(source / "structured_months" / f"month_{year}-{month:02d}.json.gz")
            for row in document["cells"]:
                item = {**row, "period": document["period"]}
                history[str(row["cell_id"])].append(item)
                known[str(row["cell_id"])] = row

    state = base.MonthlyState(
        model_from_serialized(prior["m0_state"]["quantity"]),
        model_from_serialized(prior["m0_state"]["unit_value"]),
        history,
        known,
    )
    participation = participation_from_serialized(prior["m0_state"]["participation"])
    states = {
        "participation": seasonal.SeasonalState(),
        "quantity": seasonal.SeasonalState(),
        "unit_value": seasonal.SeasonalState(),
    }
    update_seasonal_from_2022(states, source_2022)
    reconstructed_weights = {
        key: seasonal.PrequentialWeights() for key in ("participation", "quantity", "unit_value")
    }
    update_seasonal_and_weights_from_2023(states, reconstructed_weights, source_2023)

    weights: dict[str, seasonal.PrequentialWeights] = {}
    for label, stored in prior["seasonal_weights"].items():
        stored_float = {model: float(value) for model, value in stored.items()}
        reconstructed = reconstructed_weights[label].log_evidence
        if any(not math.isclose(stored_float[m], reconstructed[m], rel_tol=0.0, abs_tol=1e-8) for m in seasonal.MODEL_IDS):
            raise base.GateFailure(f"stored and reconstructed 2023 weights differ for {label}")
        weights[label] = seasonal.PrequentialWeights(log_evidence=stored_float)

    recovery = {
        "terminal_prior_sha256": sha256_file(prior_path),
        "terminal_z_post_sha256": sha256_file(source_2023 / "z_post" / "z_post_2023-12.json"),
        "weights_reconciled": True,
        "seasonal_innovation_order": "2022-02..2022-12 then 2023-01..2023-12",
    }
    return state, participation, names, scales, states, weights, recovery


def average(values: list[float]) -> float | None:
    return float(np.mean(np.asarray(values, dtype=float))) if values else None


def run(source_2022: Path, source_2023: Path, sealed_2024: Path, output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise base.GateFailure(f"refusing to mix with non-empty output {output}")
    if not PREREGISTRATION.is_file():
        raise base.GateFailure("missing frozen mini-replay preregistration")
    state, participation, names, scales, seasons, weights, recovery = seed_from_2023(source_2022, source_2023)
    target_manifest_path = sealed_2024 / "MANIFEST_SHA256.txt"
    target_manifest = parse_manifest(target_manifest_path)
    sequence: list[dict[str, Any]] = []
    monthly: list[dict[str, Any]] = []

    for month in range(FIRST_MONTH, LAST_MONTH + 1):
        target = f"{YEAR}-{month:02d}"
        training = "2023-12" if month == 1 else f"{YEAR}-{month - 1:02d}"
        seasonal.require_next_month(training, target)
        if max(base.period_index(items[-1]["period"]) for items in state.history.values()) != base.period_index(training):
            raise base.GateFailure("posterior did not carry exactly to the preceding month")

        candidates = [state.known[key] for key in sorted(state.known)]
        q_context = FeatureContext(
            state,
            target,
            "weight_kg",
            names,
            scales["quantity_center"],
            scales["quantity_scale"],
            scales["quantity_center"],
            scales["quantity_scale"],
        )
        v_context = FeatureContext(
            state,
            target,
            "statistical_unit_value_eur_per_kg",
            names,
            scales["unit_value_center"],
            scales["unit_value_scale"],
            scales["quantity_center"],
            scales["quantity_scale"],
        )
        q_dists = state.quantity_model.predict(np.vstack([q_context.design(row) for row in candidates]))
        v_dists = state.unit_value_model.predict(np.vstack([v_context.design(row) for row in candidates]))
        frozen: list[dict[str, Any]] = []
        for row, q_dist, v_dist in zip(candidates, q_dists, v_dists):
            cell = cell_from_id(str(row["cell_id"]))
            p0 = participation.predict(cell["cell_id"])
            predictions: dict[str, Any] = {"participation": {}, "quantity": {}, "unit_value": {}}
            for model in seasonal.MODEL_IDS:
                predictions["participation"][model] = logistic(
                    logit(p0) + seasons["participation"].prediction_delta(cell, target, model)
                )
                predictions["quantity"][model] = adjusted_distribution(
                    q_dist, "weight_kg", seasons["quantity"].prediction_delta(cell, target, model)
                )
                predictions["unit_value"][model] = adjusted_distribution(
                    v_dist,
                    "statistical_unit_value_eur_per_kg",
                    seasons["unit_value"].prediction_delta(cell, target, model),
                )
            last = state.history[cell["cell_id"]][-1]
            frozen.append(
                {
                    "cell_id": cell["cell_id"],
                    "models": predictions,
                    "weights": {key: value.probabilities() for key, value in weights.items()},
                    "persistence": {
                        "weight_kg": base.row_value(last, "weight_kg"),
                        "statistical_unit_value_eur_per_kg": base.row_value(
                            last, "statistical_unit_value_eur_per_kg"
                        ),
                    },
                }
            )

        freeze = {
            "schema_version": SCHEMA,
            "transition": f"{training}->{target}",
            "knowledge_cut": training,
            "target_prediction_unit": target,
            "block_contract": "EXACTLY_ONE_MONTH_TO_EXACTLY_ONE_MONTH",
            "regime": "ORDINARY",
            "predictions": frozen,
            "status": "FROZEN_BEFORE_TARGET_PAYLOAD_OPENED_BY_THIS_RUNNER",
            "seasonal_training": f"sealed M0 innovations through {training}",
            "epistemic_class": "RETROSPECTIVE_CAUSAL_REPLAY_NOT_BLIND",
        }
        freeze_path = output / "freezes" / f"freeze_{target}.json.gz"
        freeze_hash = gzip_new(freeze_path, freeze)
        sequence.append(
            {"event": "FREEZE_WRITTEN", "target_period": target, "training_period": training, "sha256": freeze_hash}
        )

        relative_target = f"structured_months/month_{target}.json.gz"
        if relative_target not in target_manifest:
            raise base.GateFailure(f"target missing from sealed 2024 manifest: {relative_target}")
        outcome, outcome_hash = copy_gzip_new_after_freeze(
            sealed_2024 / relative_target,
            output / relative_target,
            target_manifest[relative_target],
        )
        if outcome.get("period") != target:
            raise base.GateFailure("wrong target period in sealed 2024 payload")
        sequence.append(
            {
                "event": "SEALED_TARGET_OPENED_AFTER_FREEZE",
                "target_period": target,
                "after_freeze_sha256": freeze_hash,
                "sha256": outcome_hash,
            }
        )

        observed = {str(row["cell_id"]): row for row in outcome["cells"]}
        p_scores: list[dict[str, Any]] = []
        q_scores: list[dict[str, Any]] = []
        v_scores: list[dict[str, Any]] = []
        log_scores = {key: {model: 0.0 for model in seasonal.MODEL_IDS} for key in weights}
        for item in frozen:
            cell_id = str(item["cell_id"])
            actual_presence = int(cell_id in observed)
            p_row = {"cell_id": cell_id, "actual": actual_presence, "models": {}}
            for model, probability in item["models"]["participation"].items():
                score = base.log_loss(actual_presence, float(probability))
                log_scores["participation"][model] -= score
                p_row["models"][model] = {
                    "probability": probability,
                    "brier": base.brier(actual_presence, float(probability)),
                    "log_loss": score,
                }
            p_scores.append(p_row)
            cell = cell_from_id(cell_id)
            seasons["participation"].update_after_adjudication(
                cell, target, actual_presence - float(item["models"]["participation"]["M0"])
            )
            if not actual_presence:
                continue
            for label, variable, rows in (
                ("quantity", "weight_kg", q_scores),
                ("unit_value", "statistical_unit_value_eur_per_kg", v_scores),
            ):
                actual = base.row_value(observed[cell_id], variable)
                persistence = item["persistence"][variable]
                if actual is None or persistence is None:
                    continue
                scored = {"cell_id": cell_id, "actual": actual, "persistence": persistence, "models": {}}
                for model, prediction in item["models"][label].items():
                    point = float(prediction["point_median"])
                    error = abs(base.transformed(actual, variable) - base.transformed(point, variable))
                    scored["models"][model] = {"point": point, "male": error}
                    log_scores[label][model] -= error
                rows.append(scored)
            for label, variable in (
                ("quantity", "weight_kg"),
                ("unit_value", "statistical_unit_value_eur_per_kg"),
            ):
                actual = base.row_value(observed[cell_id], variable)
                if actual is not None:
                    point = float(item["models"][label]["M0"]["point_median"])
                    seasons[label].update_after_adjudication(
                        cell,
                        target,
                        base.transformed(actual, variable) - base.transformed(point, variable),
                    )

        for key in weights:
            weights[key].update_after_adjudication(log_scores[key])
        adjudication = {
            "schema_version": SCHEMA,
            "transition": f"{training}->{target}",
            "freeze_sha256": freeze_hash,
            "outcome_sha256": outcome_hash,
            "participation": p_scores,
            "quantity": q_scores,
            "unit_value": v_scores,
            "post_outcome_log_scores": log_scores,
        }
        adjudication_hash = gzip_new(
            output / "adjudications" / f"adjudication_{target}.json.gz", adjudication
        )

        qx = np.vstack([q_context.design(row) for row in outcome["cells"]])
        state.quantity_model.update(
            qx,
            np.asarray([base.transformed(float(row["weight_kg"]), "weight_kg") for row in outcome["cells"]]),
        )
        value_rows = [
            row
            for row in outcome["cells"]
            if base.row_value(row, "statistical_unit_value_eur_per_kg") is not None
        ]
        vx = np.vstack([v_context.design(row) for row in value_rows])
        state.unit_value_model.update(
            vx,
            np.asarray(
                [
                    base.transformed(
                        float(row["statistical_unit_value_eur_per_kg"]),
                        "statistical_unit_value_eur_per_kg",
                    )
                    for row in value_rows
                ]
            ),
        )
        participation.admit(outcome["cells"])
        participation.update(set(observed))
        for row in outcome["cells"]:
            cell = cell_from_id(str(row["cell_id"]))
            state.known[cell["cell_id"]] = row
            state.history.setdefault(cell["cell_id"], []).append({**row, "period": target})

        posterior = {
            "schema_version": SCHEMA,
            "compiled_from_target": target,
            "adjudication_sha256": adjudication_hash,
            "m0_state": {
                "quantity": state.quantity_model.serializable(),
                "unit_value": state.unit_value_model.serializable(),
                "participation": participation.serializable(),
            },
            "seasonal_weights": {key: value.log_evidence for key, value in weights.items()},
            "regime": "ORDINARY",
        }
        posterior_hash = gzip_new(output / "priors" / f"prior_after_{target}_ORDINARY.json.gz", posterior)
        write_json_new(
            output / "z_post" / f"z_post_{target}.json",
            {
                "target_period": target,
                "adjudication_sha256": adjudication_hash,
                "future_prior_sha256": posterior_hash,
                "transition_contract": "OUTCOME_t_UPDATES_ONLY_PRIOR_FOR_t_PLUS_1",
            },
        )
        sequence.append(
            {
                "event": "ADJUDICATION_AND_Z_POST_WRITTEN",
                "target_period": target,
                "adjudication_sha256": adjudication_hash,
                "prior_sha256": posterior_hash,
            }
        )

        p_month = {
            model: average([float(row["models"][model]["brier"]) for row in p_scores])
            for model in seasonal.MODEL_IDS
        }
        q_month = {
            model: average([float(row["models"][model]["male"]) for row in q_scores])
            for model in seasonal.MODEL_IDS
        }
        v_month = {
            model: average([float(row["models"][model]["male"]) for row in v_scores])
            for model in seasonal.MODEL_IDS
        }
        monthly.append(
            {
                "target_period": target,
                "n_participation": len(p_scores),
                "n_quantity": len(q_scores),
                "n_unit_value": len(v_scores),
                "participation_brier": p_month,
                "quantity_male": q_month,
                "quantity_persistence_male": average(
                    [
                        abs(
                            base.transformed(float(row["actual"]), "weight_kg")
                            - base.transformed(float(row["persistence"]), "weight_kg")
                        )
                        for row in q_scores
                    ]
                ),
                "unit_value_male": v_month,
                "unit_value_persistence_male": average(
                    [
                        abs(
                            base.transformed(float(row["actual"]), "statistical_unit_value_eur_per_kg")
                            - base.transformed(
                                float(row["persistence"]), "statistical_unit_value_eur_per_kg"
                            )
                        )
                        for row in v_scores
                    ]
                ),
            }
        )

    write_json_new(output / "SEQUENCE.json", sequence)
    write_json_new(
        output / "RESULT.json",
        {
            "schema_version": SCHEMA,
            "status": "EXECUTED_RETROSPECTIVE_CAUSAL_MINI_2024_JAN_SEP",
            "preregistration_sha256": sha256_file(PREREGISTRATION),
            "runner_sha256": sha256_file(Path(__file__)),
            "source_2024_manifest_sha256": sha256_file(target_manifest_path),
            "recovery": recovery,
            "monthly": monthly,
            "final_weights": {key: value.probabilities() for key, value in weights.items()},
            "sequence": sequence,
            "claim_boundary": {
                "global_winner": None,
                "promotion": "PROHIBITED",
                "prospective_validation": False,
                "blindness": False,
            },
        },
    )
    write_manifest(output)


if __name__ == "__main__":
    run(
        Path("evidence/runs/aeat-ch72-monthly-sequential-v0.6.5-2022-bootstrap-r2"),
        Path("evidence/runs/aeat-ch72-monthly-seasonal-v0.6.5-2023-causal"),
        Path("evidence/runs/aeat-ch72-monthly-sequential-v0.6.4"),
        Path("evidence/runs/aeat-ch72-monthly-seasonal-v0.6.5-2024-causal-mini-jan-sep"),
    )
