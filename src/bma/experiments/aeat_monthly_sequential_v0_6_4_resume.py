#!/usr/bin/env python3
"""Resume an interrupted immutable AEAT v0.6.4 monthly replay.

Existing artifacts are never rewritten.  The sealed posterior referenced by
the latest Z_post is loaded, history is reconstructed only from already
structured months, and the next missing month is frozen before its source is
opened.  Feature cross-sections are precomputed once per target; this is
algebraically identical to v0.6.4's repeated scans.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from bma.custody import canonical_bytes, sha256_bytes, sha256_file, write_json_new, write_manifest
from bma.experiments import aeat_monthly_sequential_v0_6_3 as base
from bma.experiments import aeat_monthly_sequential_v0_6_4 as v064
from bma.experiments.mercabarna_flor_v0_4_1 import BayesianLinearState

SCHEMA = v064.SCHEMA
GateFailure = base.GateFailure


def read_gzip_json(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def model_from_serialized(value: dict[str, Any]) -> BayesianLinearState:
    return BayesianLinearState(
        names=[str(item) for item in value["feature_names"]],
        precision=np.asarray(value["precision"], dtype=float),
        eta=np.asarray(value["eta"], dtype=float),
        a=float(value["a"]),
        b=float(value["b"]),
        observations=int(value["observations_ingested"]),
    )


def participation_from_serialized(
    value: dict[str, Any],
) -> v064.StructurallyExtensibleFrozenParticipation:
    state = v064.StructurallyExtensibleFrozenParticipation()
    state.metadata = {str(key): dict(item) for key, item in value["metadata"].items()}
    state.success = defaultdict(lambda: defaultdict(int))
    state.trials = defaultdict(lambda: defaultdict(int))
    for layer, values in value["success"].items():
        state.success[str(layer)].update({str(key): int(count) for key, count in values.items()})
    for layer, values in value["trials"].items():
        state.trials[str(layer)].update({str(key): int(count) for key, count in values.items()})
    state.last = {str(key): int(outcome) for key, outcome in value["last"].items()}
    return state


def gzip_json_new(path: Path, value: Any) -> str:
    if path.exists():
        raise GateFailure(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = gzip.compress(canonical_bytes(value), compresslevel=9, mtime=0)
    path.write_bytes(payload)
    return sha256_bytes(payload)


class FeatureContext:
    """Exact v0.6.4 cross-sectional features, computed once per target."""

    def __init__(
        self,
        state: base.MonthlyState,
        target_period: str,
        variable: str,
        names: list[str],
        center: float,
        scale: float,
        weight_center: float,
        weight_scale: float,
    ) -> None:
        self.state = state
        self.target_period = target_period
        self.target_index = base.period_index(target_period)
        self.variable = variable
        self.names = names
        self.center = center
        self.scale = scale
        self.weight_center = weight_center
        self.weight_scale = weight_scale
        product: dict[tuple[str, str], list[float]] = defaultdict(list)
        partner: dict[tuple[str, str], list[float]] = defaultdict(list)
        for records in state.history.values():
            prior = [
                item
                for item in records
                if base.period_index(str(item["period"])) < self.target_index
            ]
            if not prior:
                continue
            candidate = prior[-1]
            value = base.row_value(candidate, variable)
            if value is None:
                continue
            encoded = base.transformed(value, variable)
            flow = str(candidate["flow"])
            product[(flow, str(candidate["cn8"]))].append(encoded)
            partner[(flow, str(candidate["partner_country"]))].append(encoded)
        self.product = {key: float(np.median(values)) for key, values in product.items()}
        self.partner = {key: float(np.median(values)) for key, values in partner.items()}

    def design(self, row: dict[str, Any]) -> np.ndarray:
        full_history = self.state.history.get(str(row["cell_id"]), [])
        prior = [
            item
            for item in full_history
            if base.period_index(str(item["period"])) < self.target_index
        ]
        if len(prior) != len(full_history):
            raise GateFailure("future month entered feature history")
        last = prior[-1] if prior else None
        last_value = base.row_value(last, self.variable) if last else None
        lag = base.transformed(last_value, self.variable) if last_value is not None else self.center
        gap = self.target_index - base.period_index(str(last["period"])) if last else 12
        flow = str(row["flow"])
        product_value = self.product.get((flow, str(row["cn8"])), self.center)
        partner_value = self.partner.get((flow, str(row["partner_country"])), self.center)
        last_weight = base.row_value(last, "weight_kg") if last else None
        lag_weight = math.log1p(last_weight) if last_weight is not None else self.weight_center
        month = int(self.target_period[-2:])
        mapping = {name: 0.0 for name in self.names}
        mapping["intercept"] = 1.0
        for categorical in (
            f"flow:{row['flow']}",
            f"cn4:{row['cn4']}",
            f"partner:{row['partner_country']}",
        ):
            if categorical in mapping:
                mapping[categorical] = 1.0
        mapping["num:lag"] = (lag - self.center) / self.scale
        mapping["num:cross_product_flow"] = (product_value - self.center) / self.scale
        mapping["num:cross_partner_flow"] = (partner_value - self.center) / self.scale
        mapping["num:gap_months"] = min(max(gap, 1), 12) / 12.0
        mapping["num:lag_available"] = float(last_value is not None)
        mapping["num:month_sin"] = math.sin(2.0 * math.pi * (month - 1) / 12.0)
        mapping["num:month_cos"] = math.cos(2.0 * math.pi * (month - 1) / 12.0)
        mapping["num:year_end"] = float(month == 12)
        mapping["num:lag_weight"] = (lag_weight - self.weight_center) / self.weight_scale
        return np.asarray([mapping[name] for name in self.names], dtype=float)


def monthly_result(adjudication: dict[str, Any], regime: str) -> dict[str, Any]:
    participation = adjudication["participation"]
    quantity = adjudication["quantity_conditional_on_participation"]
    value = adjudication["statistical_unit_value_conditional_on_participation"]
    def mean(rows: list[dict[str, Any]], key: str) -> float | None:
        return float(np.mean([item[key] for item in rows])) if rows else None
    return {
        "training_period": adjudication["training_observation_unit"],
        "target_period": adjudication["target_prediction_unit"],
        "regime": regime,
        "participation_n": len(participation),
        "participation_bma_brier": mean(participation, "bma_brier"),
        "participation_origin_frozen_brier": mean(participation, "origin_frozen_brier"),
        "quantity_n": len(quantity),
        "quantity_bma_male": mean(quantity, "bma_error"),
        "quantity_persistence_male": mean(quantity, "persistence_error"),
        "quantity_wins": sum(item["bma_vs_persistence"] == "LOCAL_WIN" for item in quantity),
        "quantity_losses": sum(item["bma_vs_persistence"] == "LOCAL_LOSS" for item in quantity),
        "unit_value_n": len(value),
        "unit_value_bma_male": mean(value, "bma_error"),
        "unit_value_persistence_male": mean(value, "persistence_error"),
        "unit_value_wins": sum(item["bma_vs_persistence"] == "LOCAL_WIN" for item in value),
        "unit_value_losses": sum(item["bma_vs_persistence"] == "LOCAL_LOSS" for item in value),
        "first_appearance_cells": len(adjudication["unscored_first_appearance_cells"]),
    }


def reconstruct(output: Path, year: int = 2024) -> tuple[
    base.MonthlyState,
    v064.StructurallyExtensibleFrozenParticipation,
    dict[str, Any],
    list[str],
    dict[str, float],
    str,
    str,
]:
    if (output / "RESULT.json").exists() or (output / "MANIFEST_SHA256.txt").exists():
        raise GateFailure("run is already finalized")
    z_paths = sorted((output / "z_post").glob(f"z_post_{year:04d}-*.json"))
    if not z_paths:
        raise GateFailure("no sealed Z_post available for recovery")
    latest_z = json.loads(z_paths[-1].read_text(encoding="utf-8"))
    last_period = str(latest_z["target_period"])
    prior_path = output / "priors" / f"prior_after_{last_period}_ORDINARY.json.gz"
    if not prior_path.exists() or sha256_file(prior_path) != latest_z["future_prior_sha256"]:
        raise GateFailure("latest posterior does not match its sealed Z_post")
    posterior = read_gzip_json(prior_path)
    if posterior["compiled_from_target"] != last_period or posterior["regime"] != "ORDINARY":
        raise GateFailure("latest posterior identity is not resumable ordinary state")

    january = read_gzip_json(output / "structured_months" / f"month_{year:04d}-01.json.gz")
    initial_state, initial_participation, names, scales = base.initialize(january)
    frozen_participation = participation_from_serialized(initial_participation.serializable())
    controls = {
        "quantity": initial_state.quantity_model.clone(),
        "unit_value": initial_state.unit_value_model.clone(),
        "participation": frozen_participation,
    }
    control_hash = sha256_bytes(
        canonical_bytes(
            {
                "quantity": controls["quantity"].serializable(),
                "unit_value": controls["unit_value"].serializable(),
                "participation": controls["participation"].serializable(),
            }
        )
    )
    for freeze_path in sorted((output / "freezes").glob(f"freeze_{year:04d}-*.json.gz")):
        freeze = read_gzip_json(freeze_path)
        if freeze["origin_frozen_state_sha256"] != control_hash:
            raise GateFailure("frozen January control hash changed before recovery")

    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    known: dict[str, dict[str, Any]] = {}
    month_paths = sorted((output / "structured_months").glob(f"month_{year:04d}-*.json.gz"))
    expected_periods = [f"{year:04d}-{month:02d}" for month in range(1, int(last_period[-2:]) + 1)]
    observed_periods: list[str] = []
    for month_path in month_paths:
        document = read_gzip_json(month_path)
        period = str(document["period"])
        if base.period_index(period) > base.period_index(last_period):
            continue
        observed_periods.append(period)
        for row in document["cells"]:
            cell_id = str(row["cell_id"])
            known[cell_id] = row
            history[cell_id].append({**row, "period": period})
    if observed_periods != expected_periods:
        raise GateFailure(f"structured chronology is incomplete: {observed_periods!r}")

    state = base.MonthlyState(
        model_from_serialized(posterior["quantity_model"]),
        model_from_serialized(posterior["unit_value_model"]),
        history,
        known,
    )
    participation = participation_from_serialized(posterior["participation_model"])
    controls["participation"].admit([known[key] for key in sorted(known)])
    if state.quantity_model.names != names or state.unit_value_model.names != names:
        raise GateFailure("posterior feature identity differs from January freeze")
    return state, participation, controls, names, scales, last_period, control_hash


def rebuild_sequence(output: Path, year: int = 2024) -> list[dict[str, Any]]:
    initial_path = output / "structured_months" / f"month_{year:04d}-01.json.gz"
    sequence: list[dict[str, Any]] = [{
        "sequence": 1,
        "event": "INITIAL_MONTH_OPENED_AND_STRUCTURED",
        "period": f"{year:04d}-01",
        "sha256": sha256_file(initial_path),
        "raw_archive_persisted": False,
    }]
    for target_month in range(2, 13):
        target = f"{year:04d}-{target_month:02d}"
        training = f"{year:04d}-{target_month - 1:02d}"
        freeze_path = output / "freezes" / f"freeze_{target}.json.gz"
        outcome_path = output / "structured_months" / f"month_{target}.json.gz"
        adjudication_path = output / "adjudications" / f"adjudication_{target}.json.gz"
        prior_regime = "YEAR_END_UNCALIBRATED" if target_month == 12 else "ORDINARY"
        prior_path = output / "priors" / f"prior_after_{target}_{prior_regime}.json.gz"
        z_path = output / "z_post" / f"z_post_{target}.json"
        required = [freeze_path, outcome_path, adjudication_path, prior_path, z_path]
        if not all(path.exists() for path in required):
            raise GateFailure(f"incomplete finalized transition {target}")
        adjudication = read_gzip_json(adjudication_path)
        sequence.extend([
            {
                "sequence": len(sequence) + 1,
                "event": "FREEZE_WRITTEN",
                "training_period": training,
                "target_period": target,
                "sha256": sha256_file(freeze_path),
            },
            {
                "sequence": len(sequence) + 2,
                "event": "TARGET_MONTH_OPENED_AND_STRUCTURED",
                "target_period": target,
                "sha256": sha256_file(outcome_path),
                "after_freeze_sha256": sha256_file(freeze_path),
                "raw_archive_persisted": False,
            },
            {
                "sequence": len(sequence) + 3,
                "event": "ADJUDICATION_AND_Z_POST_WRITTEN",
                "target_period": target,
                "adjudication_sha256": sha256_file(adjudication_path),
                "prior_sha256": sha256_file(prior_path),
                "z_post_sha256": sha256_file(z_path),
            },
        ])
        if adjudication["freeze_sha256"] != sha256_file(freeze_path):
            raise GateFailure(f"adjudication freeze hash mismatch for {target}")
    return sequence


def resume(output: Path, year: int = 2024) -> dict[str, Any]:
    state, participation, controls, names, scales, last_period, control_hash = reconstruct(output, year)
    start_month = int(last_period[-2:]) + 1
    if start_month > 12:
        raise GateFailure("all target months are already sealed; only finalization is missing")
    states: dict[str, base.MonthlyState] = {"ORDINARY": state}
    participation_states = {"ORDINARY": participation}
    for target_month in range(start_month, 13):
        training_month = target_month - 1
        training_period = f"{year:04d}-{training_month:02d}"
        target_period = f"{year:04d}-{target_month:02d}"
        regime = "YEAR_END_UNCALIBRATED" if target_month == 12 else "ORDINARY"
        if regime not in states:
            states[regime] = states["ORDINARY"].fork()
            participation_states[regime] = participation_states["ORDINARY"].fork()
        current = states[regime]
        current_participation = participation_states[regime]
        latest = max(base.period_index(items[-1]["period"]) for items in current.history.values() if items)
        if latest != base.period_index(training_period):
            raise GateFailure("posterior knowledge cut is not the immediately preceding month")
        candidates = [current.known[key] for key in sorted(current.known)]
        controls["participation"].admit(candidates)
        q_context = FeatureContext(
            current, target_period, "weight_kg", names,
            scales["quantity_center"], scales["quantity_scale"],
            scales["quantity_center"], scales["quantity_scale"],
        )
        v_context = FeatureContext(
            current, target_period, "statistical_unit_value_eur_per_kg", names,
            scales["unit_value_center"], scales["unit_value_scale"],
            scales["quantity_center"], scales["quantity_scale"],
        )
        quantity_x = np.vstack([q_context.design(row) for row in candidates])
        value_x = np.vstack([v_context.design(row) for row in candidates])
        quantity_predictions = current.quantity_model.predict(quantity_x)
        value_predictions = current.unit_value_model.predict(value_x)
        frozen_rows: list[dict[str, Any]] = []
        for row, qdist, vdist in zip(candidates, quantity_predictions, value_predictions):
            cell_id = str(row["cell_id"])
            last = current.history[cell_id][-1]
            frozen_rows.append({
                "cell_id": cell_id,
                "participation_probability": current_participation.predict(cell_id),
                "quantity": base.prediction(qdist, "weight_kg"),
                "statistical_unit_value": base.prediction(vdist, "statistical_unit_value_eur_per_kg"),
                "persistence": {
                    "weight_kg": base.row_value(last, "weight_kg"),
                    "statistical_unit_value_eur_per_kg": base.row_value(last, "statistical_unit_value_eur_per_kg"),
                },
                "last_observation_period": last["period"],
            })
        prior_state = {
            "quantity": current.quantity_model.serializable(),
            "unit_value": current.unit_value_model.serializable(),
            "participation": current_participation.serializable(),
            "regime": regime,
        }
        freeze = {
            "schema_version": SCHEMA,
            "transition": f"{training_period}->{target_period}",
            "training_observation_unit": training_period,
            "target_prediction_unit": target_period,
            "block_contract": "EXACTLY_ONE_MONTH_TO_EXACTLY_ONE_MONTH",
            "knowledge_cut": training_period,
            "prior_state_sha256": sha256_bytes(canonical_bytes(prior_state)),
            "origin_frozen_state_sha256": control_hash,
            "regime": regime,
            "predictions": frozen_rows,
            "status": "FROZEN_BEFORE_TARGET_ARCHIVE_OPENED_IN_THIS_REPLAY",
            "claim_boundary": "retrospective replay; historical releases were public before execution",
        }
        freeze_path = output / "freezes" / f"freeze_{target_period}.json.gz"
        if freeze_path.exists():
            sealed_freeze = read_gzip_json(freeze_path)
            if sealed_freeze["prior_state_sha256"] != freeze["prior_state_sha256"] or sealed_freeze["transition"] != freeze["transition"]:
                raise GateFailure("existing freeze does not match the sealed posterior")
            freeze_hash = sha256_file(freeze_path)
        else:
            freeze_hash = gzip_json_new(freeze_path, freeze)

        outcome = v064.fetch_month(year, target_month)
        if outcome.get("period") != target_period:
            raise GateFailure(f"target period mismatch {outcome.get('period')!r} != {target_period!r}")
        outcome_hash = gzip_json_new(
            output / "structured_months" / f"month_{target_period}.json.gz", outcome
        )
        frozen_by = {row["cell_id"]: row for row in frozen_rows}
        observed_by = {str(row["cell_id"]): row for row in outcome["cells"]}
        participation_scores: list[dict[str, Any]] = []
        quantity_scores: list[dict[str, Any]] = []
        value_scores: list[dict[str, Any]] = []
        for cell_id, frozen in sorted(frozen_by.items()):
            actual_presence = int(cell_id in observed_by)
            probability = float(frozen["participation_probability"])
            control_probability = controls["participation"].predict(cell_id)
            participation_scores.append({
                "cell_id": cell_id,
                "actual": actual_presence,
                "bma_probability": probability,
                "origin_frozen_probability": control_probability,
                "bma_brier": base.brier(actual_presence, probability),
                "origin_frozen_brier": base.brier(actual_presence, control_probability),
                "bma_log_loss": base.log_loss(actual_presence, probability),
                "origin_frozen_log_loss": base.log_loss(actual_presence, control_probability),
            })
            if not actual_presence:
                continue
            actual = observed_by[cell_id]
            for variable, frozen_key, target in (
                ("weight_kg", "quantity", quantity_scores),
                ("statistical_unit_value_eur_per_kg", "statistical_unit_value", value_scores),
            ):
                actual_value = base.row_value(actual, variable)
                persistence_value = frozen["persistence"][variable]
                if actual_value is None or persistence_value is None:
                    continue
                point = float(frozen[frozen_key]["point_median"])
                model_error = abs(base.transformed(actual_value, variable) - base.transformed(point, variable))
                baseline_error = abs(base.transformed(actual_value, variable) - base.transformed(float(persistence_value), variable))
                target.append({
                    "cell_id": cell_id,
                    "actual": actual_value,
                    "bma_point": point,
                    "persistence": persistence_value,
                    "bma_error": model_error,
                    "persistence_error": baseline_error,
                    "bma_vs_persistence": base.local_verdict(model_error, baseline_error),
                    "covered_90": frozen[frozen_key]["lower_90_natural"] <= actual_value <= frozen[frozen_key]["upper_90_natural"],
                })
        adjudication = {
            "schema_version": SCHEMA,
            "transition": f"{training_period}->{target_period}",
            "training_observation_unit": training_period,
            "target_prediction_unit": target_period,
            "freeze_sha256": freeze_hash,
            "outcome_sha256": outcome_hash,
            "status": "ADJUDICATED_ONE_MONTH_TARGET",
            "participation": participation_scores,
            "quantity_conditional_on_participation": quantity_scores,
            "statistical_unit_value_conditional_on_participation": value_scores,
            "unscored_first_appearance_cells": sorted(observed_by.keys() - frozen_by.keys()),
            "completeness_semantics": "definitive monthly archive: known-cell absence is a genuine non-participation outcome",
        }
        adjudication_hash = gzip_json_new(
            output / "adjudications" / f"adjudication_{target_period}.json.gz", adjudication
        )

        update_rows = outcome["cells"]
        q_update_x = np.vstack([q_context.design(row) for row in update_rows])
        q_update_y = np.asarray([base.transformed(float(row["weight_kg"]), "weight_kg") for row in update_rows])
        current.quantity_model.update(q_update_x, q_update_y)
        value_rows = [row for row in update_rows if base.row_value(row, "statistical_unit_value_eur_per_kg") is not None]
        v_update_x = np.vstack([v_context.design(row) for row in value_rows])
        v_update_y = np.asarray([
            base.transformed(float(row["statistical_unit_value_eur_per_kg"]), "statistical_unit_value_eur_per_kg")
            for row in value_rows
        ])
        current.unit_value_model.update(v_update_x, v_update_y)
        current_participation.admit(update_rows)
        current_participation.update(set(observed_by))
        for row in update_rows:
            cell_id = str(row["cell_id"])
            current.known[cell_id] = row
            current.history.setdefault(cell_id, []).append({**row, "period": target_period})
        posterior = {
            "schema_version": SCHEMA,
            "compiled_from_target": target_period,
            "adjudication_sha256": adjudication_hash,
            "knowledge_effect": "FUTURE_ONLY_ONE_MONTH_STEP",
            "next_training_observation_unit": target_period,
            "quantity_model": current.quantity_model.serializable(),
            "unit_value_model": current.unit_value_model.serializable(),
            "participation_model": current_participation.serializable(),
            "regime": regime,
        }
        posterior_hash = gzip_json_new(
            output / "priors" / f"prior_after_{target_period}_{regime}.json.gz", posterior
        )
        z_post = {
            "schema_version": SCHEMA,
            "target_period": target_period,
            "adjudication_sha256": adjudication_hash,
            "future_prior_sha256": posterior_hash,
            "transition_contract": "OUTCOME_t_UPDATES_ONLY_PRIOR_FOR_t_PLUS_1",
            "global_winner": None,
        }
        write_json_new(output / "z_post" / f"z_post_{target_period}.json", z_post)

    transitions: list[dict[str, Any]] = []
    for target_month in range(2, 13):
        period = f"{year:04d}-{target_month:02d}"
        adjudication = read_gzip_json(output / "adjudications" / f"adjudication_{period}.json.gz")
        regime = "YEAR_END_UNCALIBRATED" if target_month == 12 else "ORDINARY"
        transitions.append(monthly_result(adjudication, regime))
    sequence = rebuild_sequence(output, year)
    result = {
        "schema_version": SCHEMA,
        "status": "EXECUTED_RETROSPECTIVE_ONE_MONTH_TO_ONE_MONTH_REPLAY",
        "transition_count": len(transitions),
        "transitions": transitions,
        "temporal_contract": {
            "training_unit": "one calendar month",
            "prediction_unit": "one immediately following calendar month",
            "adjudication_unit": "that same target calendar month",
            "Z_post_unit": "that same target calendar month",
            "raw_months_per_transition": 1,
            "same_model_posterior_carried_forward": True,
        },
        "causal_boundary": {
            "freeze_precedes_target_fetch_in_every_transition": True,
            "historically_unseen_outcomes": False,
            "classification": "RETROSPECTIVE_DEVELOPMENT_REPLAY",
        },
        "source_boundary": {
            "raw_zip_persisted": False,
            "one_archive_in_memory_at_a_time": True,
            "statistical_unit_value_is_transaction_price": False,
        },
        "claim_boundary": {
            "daily_model_evidence": False,
            "prospective_validation": False,
            "seasonality_generalization": False,
            "global_winner": None,
            "promotion": "PROHIBITED",
        },
        "execution_recovery": {
            "resumed_after_sealed_target": last_period,
            "existing_artifacts_rewritten": False,
            "posterior_hash_verified_against_Z_post": True,
            "feature_precomputation_contract": "ALGEBRAICALLY_EQUIVALENT_TO_V0_6_4_REPEATED_SCAN",
        },
        "sequence": sequence,
    }
    write_json_new(output / "RESULT.json", result)
    write_json_new(output / "SEQUENCE.json", sequence)
    write_manifest(output)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = resume(args.output)
    print(f"status={result['status']} transitions={result['transition_count']}")


if __name__ == "__main__":
    main()
