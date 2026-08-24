#!/usr/bin/env python3
"""Causal 2023 continuation: December 2022 predicts January 2023.

M0 carries the sealed 2022 posterior without a year reset.  M1/M2 are
seasonal overlays trained only from sealed 2022 M0 innovations; they are
scored and updated only after their 2023 target is adjudicated.
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
from bma.experiments import aeat_monthly_sequential_v0_6_4 as v064
from bma.experiments.aeat_monthly_sequential_v0_6_4_resume import FeatureContext, model_from_serialized, participation_from_serialized

YEAR = 2023
SCHEMA = "bma.aeat.chapter72.monthly-seasonal.causal-2023.v0.6.5"


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


def logistic(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-35.0, min(35.0, value))))


def logit(probability: float) -> float:
    p = min(1.0 - seasonal.LOG_SCORE_FLOOR, max(seasonal.LOG_SCORE_FLOOR, probability))
    return math.log(p / (1.0 - p))


def cell_from_id(cell_id: str) -> dict[str, str]:
    flow, cn8, partner = cell_id.split("|")
    return {"cell_id": cell_id, "flow": flow, "cn4": cn8[:4], "partner_country": partner}


def seed_from_2022(root: Path) -> tuple[base.MonthlyState, Any, Any, list[str], dict[str, float], dict[str, seasonal.SeasonalState]]:
    prior = read_gzip(root / "priors" / "prior_after_2022-12_YEAR_END_UNCALIBRATED.json.gz")
    z_post = json.loads((root / "z_post" / "z_post_2022-12.json").read_text(encoding="utf-8"))
    if sha256_file(root / "priors" / "prior_after_2022-12_YEAR_END_UNCALIBRATED.json.gz") != z_post["future_prior_sha256"]:
        raise base.GateFailure("2022 December posterior is not sealed by Z_post")
    january = read_gzip(root / "structured_months" / "month_2022-01.json.gz")
    initial, initial_participation, names, scales = base.initialize(january)
    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    known: dict[str, dict[str, Any]] = {}
    for month in range(1, 13):
        document = read_gzip(root / "structured_months" / f"month_2022-{month:02d}.json.gz")
        for row in document["cells"]:
            item = {**row, "period": document["period"]}
            history[str(row["cell_id"])].append(item)
            known[str(row["cell_id"])] = row
    state = base.MonthlyState(model_from_serialized(prior["quantity_model"]), model_from_serialized(prior["unit_value_model"]), history, known)
    participation = participation_from_serialized(prior["participation_model"])
    control = participation_from_serialized(initial_participation.serializable())
    control.admit([known[key] for key in sorted(known)])
    seasons = {"participation": seasonal.SeasonalState(), "quantity": seasonal.SeasonalState(), "unit_value": seasonal.SeasonalState()}
    for month in range(2, 13):
        period = f"2022-{month:02d}"
        adjudication = read_gzip(root / "adjudications" / f"adjudication_{period}.json.gz")
        for row in adjudication["participation"]:
            cell = cell_from_id(str(row["cell_id"]))
            seasons["participation"].update_after_adjudication(cell, period, int(row["actual"]) - float(row["bma_probability"]))
        for variable, key in (("quantity", "quantity_conditional_on_participation"), ("unit_value", "statistical_unit_value_conditional_on_participation")):
            base_variable = "weight_kg" if variable == "quantity" else "statistical_unit_value_eur_per_kg"
            for row in adjudication[key]:
                innovation = base.transformed(float(row["actual"]), base_variable) - base.transformed(float(row["bma_point"]), base_variable)
                seasons[variable].update_after_adjudication(cell_from_id(str(row["cell_id"])), period, innovation)
    return state, participation, control, names, scales, seasons


def adjusted_distribution(distribution: dict[str, float], variable: str, delta: float) -> dict[str, float]:
    shifted = {
        **distribution,
        "location": float(distribution["location"]) + delta,
        "lower_90": float(distribution["lower_90"]) + delta,
        "upper_90": float(distribution["upper_90"]) + delta,
    }
    return base.prediction(shifted, variable)


def run(source_2022: Path, output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        allowed = {"freezes/freeze_2023-01.json.gz"}
        present = {
            path.relative_to(output).as_posix()
            for path in output.rglob("*")
            if path.is_file()
        }
        if present != allowed:
            raise base.GateFailure("2023 recovery permits only the sealed January freeze before first outcome")
    state, participation, control, names, scales, seasons = seed_from_2022(source_2022)
    weights = {key: seasonal.PrequentialWeights() for key in ("participation", "quantity", "unit_value")}
    sequence: list[dict[str, Any]] = []
    for month in range(1, 13):
        target = f"{YEAR}-{month:02d}"
        training = "2022-12" if month == 1 else f"{YEAR}-{month - 1:02d}"
        regime = "YEAR_END_UNCALIBRATED" if month == 12 else "ORDINARY"
        if max(base.period_index(items[-1]["period"]) for items in state.history.values()) != base.period_index(training):
            raise base.GateFailure("posterior did not carry exactly to the preceding month")
        candidates = [state.known[key] for key in sorted(state.known)]
        control.admit(candidates)
        q_context = FeatureContext(state, target, "weight_kg", names, scales["quantity_center"], scales["quantity_scale"], scales["quantity_center"], scales["quantity_scale"])
        v_context = FeatureContext(state, target, "statistical_unit_value_eur_per_kg", names, scales["unit_value_center"], scales["unit_value_scale"], scales["quantity_center"], scales["quantity_scale"])
        q_dists = state.quantity_model.predict(np.vstack([q_context.design(row) for row in candidates]))
        v_dists = state.unit_value_model.predict(np.vstack([v_context.design(row) for row in candidates]))
        frozen: list[dict[str, Any]] = []
        for row, q_dist, v_dist in zip(candidates, q_dists, v_dists):
            cell = cell_from_id(str(row["cell_id"]))
            p0 = participation.predict(cell["cell_id"])
            predictions: dict[str, Any] = {"participation": {}, "quantity": {}, "unit_value": {}}
            for model in seasonal.MODEL_IDS:
                predictions["participation"][model] = logistic(logit(p0) + seasons["participation"].prediction_delta(cell, target, model))
                predictions["quantity"][model] = adjusted_distribution(q_dist, "weight_kg", seasons["quantity"].prediction_delta(cell, target, model))
                predictions["unit_value"][model] = adjusted_distribution(v_dist, "statistical_unit_value_eur_per_kg", seasons["unit_value"].prediction_delta(cell, target, model))
            last = state.history[cell["cell_id"]][-1]
            frozen.append({"cell_id": cell["cell_id"], "models": predictions, "weights": {key: value.probabilities() for key, value in weights.items()}, "persistence": {"weight_kg": base.row_value(last, "weight_kg"), "statistical_unit_value_eur_per_kg": base.row_value(last, "statistical_unit_value_eur_per_kg")}})
        freeze = {"schema_version": SCHEMA, "transition": f"{training}->{target}", "knowledge_cut": training, "target_prediction_unit": target, "block_contract": "EXACTLY_ONE_MONTH_TO_EXACTLY_ONE_MONTH", "regime": regime, "predictions": frozen, "status": "FROZEN_BEFORE_TARGET_ARCHIVE_OPENED_IN_THIS_REPLAY", "seasonal_training": "2022 adjudicated M0 innovations only"}
        freeze_path = output / "freezes" / f"freeze_{target}.json.gz"
        if freeze_path.exists():
            if read_gzip(freeze_path) != freeze:
                raise base.GateFailure("existing freeze differs from reconstructed prior")
            freeze_hash = sha256_file(freeze_path)
        else:
            freeze_hash = gzip_new(freeze_path, freeze)
        sequence.append({"event": "FREEZE_WRITTEN", "target_period": target, "training_period": training, "sha256": freeze_hash})
        outcome = v064.fetch_month(YEAR, month)
        if outcome.get("period") != target:
            raise base.GateFailure("wrong target period returned by AEAT")
        outcome_hash = gzip_new(output / "structured_months" / f"month_{target}.json.gz", outcome)
        sequence.append({"event": "TARGET_MONTH_OPENED_AND_STRUCTURED", "target_period": target, "after_freeze_sha256": freeze_hash, "sha256": outcome_hash})
        observed = {str(row["cell_id"]): row for row in outcome["cells"]}
        p_scores: list[dict[str, Any]] = []
        q_scores: list[dict[str, Any]] = []
        v_scores: list[dict[str, Any]] = []
        log_scores = {key: {model: 0.0 for model in seasonal.MODEL_IDS} for key in weights}
        for item in frozen:
            cell_id = str(item["cell_id"]); actual_presence = int(cell_id in observed)
            p_row = {"cell_id": cell_id, "actual": actual_presence, "models": {}}
            for model, probability in item["models"]["participation"].items():
                score = base.log_loss(actual_presence, float(probability)); log_scores["participation"][model] -= score
                p_row["models"][model] = {"probability": probability, "brier": base.brier(actual_presence, float(probability)), "log_loss": score}
            p_scores.append(p_row)
            cell = cell_from_id(cell_id)
            seasons["participation"].update_after_adjudication(
                cell, target, actual_presence - float(item["models"]["participation"]["M0"])
            )
            if not actual_presence: continue
            for label, variable, rows in (("quantity", "weight_kg", q_scores), ("unit_value", "statistical_unit_value_eur_per_kg", v_scores)):
                actual = base.row_value(observed[cell_id], variable)
                persistence = item["persistence"][variable]
                if actual is None or persistence is None: continue
                scored = {"cell_id": cell_id, "actual": actual, "persistence": persistence, "models": {}}
                for model, prediction in item["models"][label].items():
                    point = float(prediction["point_median"]); error = abs(base.transformed(actual, variable) - base.transformed(point, variable))
                    scored["models"][model] = {"point": point, "male": error}
                    log_scores[label][model] -= error
                rows.append(scored)
            for label, variable in (("quantity", "weight_kg"), ("unit_value", "statistical_unit_value_eur_per_kg")):
                actual = base.row_value(observed[cell_id], variable)
                if actual is not None:
                    point = float(item["models"][label]["M0"]["point_median"])
                    seasons[label].update_after_adjudication(
                        cell, target, base.transformed(actual, variable) - base.transformed(point, variable)
                    )
        for key in weights: weights[key].update_after_adjudication(log_scores[key])
        adjudication = {"schema_version": SCHEMA, "transition": f"{training}->{target}", "freeze_sha256": freeze_hash, "outcome_sha256": outcome_hash, "participation": p_scores, "quantity": q_scores, "unit_value": v_scores, "post_outcome_log_scores": log_scores}
        adjudication_hash = gzip_new(output / "adjudications" / f"adjudication_{target}.json.gz", adjudication)
        qx = np.vstack([q_context.design(row) for row in outcome["cells"]]); state.quantity_model.update(qx, np.asarray([base.transformed(float(row["weight_kg"]), "weight_kg") for row in outcome["cells"]]))
        value_rows = [row for row in outcome["cells"] if base.row_value(row, "statistical_unit_value_eur_per_kg") is not None]
        vx = np.vstack([v_context.design(row) for row in value_rows]); state.unit_value_model.update(vx, np.asarray([base.transformed(float(row["statistical_unit_value_eur_per_kg"]), "statistical_unit_value_eur_per_kg") for row in value_rows]))
        participation.admit(outcome["cells"]); participation.update(set(observed))
        for row in outcome["cells"]:
            cell = cell_from_id(str(row["cell_id"])); state.known[cell["cell_id"]] = row; state.history.setdefault(cell["cell_id"], []).append({**row, "period": target})
        posterior = {"schema_version": SCHEMA, "compiled_from_target": target, "adjudication_sha256": adjudication_hash, "m0_state": {"quantity": state.quantity_model.serializable(), "unit_value": state.unit_value_model.serializable(), "participation": participation.serializable()}, "seasonal_weights": {key: value.log_evidence for key, value in weights.items()}, "regime": regime}
        posterior_hash = gzip_new(output / "priors" / f"prior_after_{target}_{regime}.json.gz", posterior)
        write_json_new(output / "z_post" / f"z_post_{target}.json", {"target_period": target, "adjudication_sha256": adjudication_hash, "future_prior_sha256": posterior_hash, "transition_contract": "OUTCOME_t_UPDATES_ONLY_PRIOR_FOR_t_PLUS_1"})
        sequence.append({"event": "ADJUDICATION_AND_Z_POST_WRITTEN", "target_period": target, "adjudication_sha256": adjudication_hash, "prior_sha256": posterior_hash})
    write_json_new(output / "SEQUENCE.json", sequence)
    write_json_new(output / "RESULT.json", {"schema_version": SCHEMA, "status": "EXECUTED_RETROSPECTIVE_CAUSAL_2023", "sequence": sequence, "claim_boundary": {"global_winner": None, "promotion": "PROHIBITED", "prospective_validation": False}})
    write_manifest(output)


if __name__ == "__main__":
    run(Path("evidence/runs/aeat-ch72-monthly-sequential-v0.6.5-2022-bootstrap-r2"), Path("evidence/runs/aeat-ch72-monthly-seasonal-v0.6.5-2023-causal"))
