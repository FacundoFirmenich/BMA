#!/usr/bin/env python3
"""AEAT Chapter 72 retrospective replay with the canonical BMA cycle.

This is the Mercabarna/lonja cycle with one and only one substitution: the
atomic clock is a calendar month instead of a calendar day.  January informs a
freeze for February; February is opened, adjudicated and absorbed through
Z_post; the same posterior then informs March, and so on through December.

The transport archives are read into RAM one at a time and are never persisted.
The run is retrospective development evidence because the historical releases
were already public before execution.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from bma.connectors.aeat_trade import fetch_month
from bma.custody import canonical_bytes, sha256_bytes, write_json_new, write_manifest
from bma.experiments.mercabarna_flor_v0_4_1 import BayesianLinearState, robust_center_scale

SCHEMA = "bma.aeat.chapter72.monthly-sequential.v0.6.3"
YEAR = 2024
FIRST_MONTH = 1
LAST_MONTH = 12


class GateFailure(RuntimeError):
    pass


def one_to_one_transitions() -> list[tuple[int, int]]:
    pairs = [(month, month + 1) for month in range(FIRST_MONTH, LAST_MONTH)]
    if len(pairs) != 11 or any(target - training != 1 for training, target in pairs):
        raise GateFailure("the 1 month -> 1 month contract was violated")
    return pairs


def period_index(period: str) -> int:
    year, month = period.split("-")
    return int(year) * 12 + int(month)


def transformed(value: float, variable: str) -> float:
    if variable == "weight_kg":
        return math.log1p(max(value, 0.0))
    if value <= 0:
        raise GateFailure(f"{variable} requires a positive value")
    return math.log(value)


def inverse_transformed(value: float, variable: str) -> float:
    return max(0.0, math.expm1(value) if variable == "weight_kg" else math.exp(value))


def row_value(row: dict[str, Any], variable: str) -> float | None:
    value = row.get(variable)
    if value is None:
        return None
    numeric = float(value)
    if variable == "statistical_unit_value_eur_per_kg" and numeric <= 0:
        return None
    if variable == "weight_kg" and numeric < 0:
        return None
    return numeric


def feature_names(initial_rows: list[dict[str, Any]]) -> list[str]:
    cn4 = sorted({str(row["cn4"]) for row in initial_rows})
    partners = sorted({str(row["partner_country"]) for row in initial_rows})
    return (
        ["intercept", "flow:I", "flow:E"]
        + [f"cn4:{value}" for value in cn4]
        + [f"partner:{value}" for value in partners]
        + [
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
    )


@dataclass
class MonthlyState:
    quantity_model: BayesianLinearState
    unit_value_model: BayesianLinearState
    history: dict[str, list[dict[str, Any]]]
    known: dict[str, dict[str, Any]]

    def fork(self) -> "MonthlyState":
        return MonthlyState(
            self.quantity_model.clone(),
            self.unit_value_model.clone(),
            copy.deepcopy(self.history),
            copy.deepcopy(self.known),
        )


@dataclass
class ParticipationState:
    metadata: dict[str, dict[str, str]] = field(default_factory=dict)
    success: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    trials: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    last: dict[str, int] = field(default_factory=dict)

    def fork(self) -> "ParticipationState":
        return copy.deepcopy(self)

    def admit(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.metadata.setdefault(
                str(row["cell_id"]),
                {
                    "flow": str(row["flow"]),
                    "cn8": str(row["cn8"]),
                    "cn4": str(row["cn4"]),
                    "partner_country": str(row["partner_country"]),
                },
            )

    def _keys(self, cell_id: str) -> dict[str, str]:
        item = self.metadata[cell_id]
        return {
            "global": "GLOBAL",
            "flow": item["flow"],
            "product_flow": f"{item['flow']}|{item['cn8']}",
            "partner_flow": f"{item['flow']}|{item['partner_country']}",
            "cell": cell_id,
        }

    def update(self, present: set[str]) -> None:
        for cell_id in sorted(self.metadata):
            outcome = int(cell_id in present)
            for layer, key in self._keys(cell_id).items():
                self.success[layer][key] += outcome
                self.trials[layer][key] += 1
            self.last[cell_id] = outcome

    def _rate(self, layer: str, key: str, mean: float, strength: float) -> float:
        return (self.success[layer][key] + strength * mean) / (
            self.trials[layer][key] + strength
        )

    def predict(self, cell_id: str) -> float:
        keys = self._keys(cell_id)
        global_rate = self._rate("global", keys["global"], 0.5, 2.0)
        flow_rate = self._rate("flow", keys["flow"], global_rate, 4.0)
        product_rate = self._rate("product_flow", keys["product_flow"], global_rate, 4.0)
        partner_rate = self._rate("partner_flow", keys["partner_flow"], global_rate, 4.0)
        hierarchical_mean = (flow_rate + product_rate + partner_rate) / 3.0
        return self._rate("cell", keys["cell"], hierarchical_mean, 6.0)

    def serializable(self) -> dict[str, Any]:
        return {
            "metadata": {key: self.metadata[key] for key in sorted(self.metadata)},
            "success": {
                layer: {key: values[key] for key in sorted(values)}
                for layer, values in sorted(self.success.items())
            },
            "trials": {
                layer: {key: values[key] for key in sorted(values)}
                for layer, values in sorted(self.trials.items())
            },
            "last": {key: self.last[key] for key in sorted(self.last)},
        }


def build_features(
    row: dict[str, Any],
    target_period: str,
    variable: str,
    state: MonthlyState,
    names: list[str],
    center: float,
    scale: float,
    weight_center: float,
    weight_scale: float,
) -> np.ndarray:
    target_index = period_index(target_period)
    full_history = state.history.get(str(row["cell_id"]), [])
    prior = [item for item in full_history if period_index(str(item["period"])) < target_index]
    if len(prior) != len(full_history):
        raise GateFailure("future month entered feature history")
    last = prior[-1] if prior else None
    last_value = row_value(last, variable) if last else None
    lag = transformed(last_value, variable) if last_value is not None else center
    gap = target_index - period_index(str(last["period"])) if last else 12

    product_cross: list[float] = []
    partner_cross: list[float] = []
    for records in state.history.values():
        candidates = [item for item in records if period_index(str(item["period"])) < target_index]
        if not candidates:
            continue
        candidate = candidates[-1]
        value = row_value(candidate, variable)
        if value is None:
            continue
        encoded = transformed(value, variable)
        if candidate["flow"] == row["flow"] and candidate["cn8"] == row["cn8"]:
            product_cross.append(encoded)
        if candidate["flow"] == row["flow"] and candidate["partner_country"] == row["partner_country"]:
            partner_cross.append(encoded)
    product_value = float(np.median(product_cross)) if product_cross else center
    partner_value = float(np.median(partner_cross)) if partner_cross else center
    last_weight = row_value(last, "weight_kg") if last else None
    lag_weight = math.log1p(last_weight) if last_weight is not None else weight_center
    month = int(target_period[-2:])

    mapping = {name: 0.0 for name in names}
    mapping["intercept"] = 1.0
    for categorical in (
        f"flow:{row['flow']}",
        f"cn4:{row['cn4']}",
        f"partner:{row['partner_country']}",
    ):
        if categorical in mapping:
            mapping[categorical] = 1.0
    mapping["num:lag"] = (lag - center) / scale
    mapping["num:cross_product_flow"] = (product_value - center) / scale
    mapping["num:cross_partner_flow"] = (partner_value - center) / scale
    mapping["num:gap_months"] = min(max(gap, 1), 12) / 12.0
    mapping["num:lag_available"] = float(last_value is not None)
    mapping["num:month_sin"] = math.sin(2.0 * math.pi * (month - 1) / 12.0)
    mapping["num:month_cos"] = math.cos(2.0 * math.pi * (month - 1) / 12.0)
    mapping["num:year_end"] = float(month == 12)
    mapping["num:lag_weight"] = (lag_weight - weight_center) / weight_scale
    return np.asarray([mapping[name] for name in names], dtype=float)


def prediction(distribution: dict[str, float], variable: str) -> dict[str, float]:
    return {
        **distribution,
        "point_median": inverse_transformed(distribution["location"], variable),
        "lower_90_natural": inverse_transformed(distribution["lower_90"], variable),
        "upper_90_natural": inverse_transformed(distribution["upper_90"], variable),
    }


def gzip_json_new(path: Path, value: Any) -> str:
    if path.exists():
        raise GateFailure(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = gzip.compress(canonical_bytes(value), compresslevel=9, mtime=0)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def brier(actual: int, probability: float) -> float:
    return (actual - probability) ** 2


def log_loss(actual: int, probability: float) -> float:
    bounded = min(max(probability, 1e-12), 1.0 - 1e-12)
    return -math.log(bounded if actual else 1.0 - bounded)


def local_verdict(model_error: float, baseline_error: float) -> str:
    delta = model_error - baseline_error
    if delta < -1e-12:
        return "LOCAL_WIN"
    if delta > 1e-12:
        return "LOCAL_LOSS"
    return "LOCAL_TIE"


def initialize(initial: dict[str, Any]) -> tuple[
    MonthlyState, ParticipationState, list[str], dict[str, float]
]:
    rows = initial["cells"]
    if not rows:
        raise GateFailure("initial month contains no Chapter 72 cells")
    names = feature_names(rows)
    quantity_values = [transformed(float(row["weight_kg"]), "weight_kg") for row in rows]
    unit_values = [
        transformed(float(row["statistical_unit_value_eur_per_kg"]), "statistical_unit_value_eur_per_kg")
        for row in rows
        if row_value(row, "statistical_unit_value_eur_per_kg") is not None
    ]
    quantity_center, quantity_scale = robust_center_scale(quantity_values)
    unit_center, unit_scale = robust_center_scale(unit_values)
    state = MonthlyState(
        BayesianLinearState.prior(names, quantity_center, quantity_scale**2),
        BayesianLinearState.prior(names, unit_center, unit_scale**2),
        defaultdict(list),
        {},
    )
    scales = {
        "quantity_center": quantity_center,
        "quantity_scale": quantity_scale,
        "unit_value_center": unit_center,
        "unit_value_scale": unit_scale,
    }

    def design(row: dict[str, Any], variable: str) -> np.ndarray:
        center, scale = (
            (quantity_center, quantity_scale)
            if variable == "weight_kg"
            else (unit_center, unit_scale)
        )
        return build_features(
            row,
            initial["period"],
            variable,
            state,
            names,
            center,
            scale,
            quantity_center,
            quantity_scale,
        )

    quantity_x = np.vstack([design(row, "weight_kg") for row in rows])
    quantity_y = np.asarray(quantity_values)
    state.quantity_model.update(quantity_x, quantity_y)
    value_rows = [row for row in rows if row_value(row, "statistical_unit_value_eur_per_kg") is not None]
    value_x = np.vstack([design(row, "statistical_unit_value_eur_per_kg") for row in value_rows])
    value_y = np.asarray(
        [
            transformed(float(row["statistical_unit_value_eur_per_kg"]), "statistical_unit_value_eur_per_kg")
            for row in value_rows
        ]
    )
    state.unit_value_model.update(value_x, value_y)
    for row in rows:
        state.known[str(row["cell_id"])] = row
        state.history[str(row["cell_id"])].append({**row, "period": initial["period"]})

    participation = ParticipationState()
    participation.admit(rows)
    participation.update({str(row["cell_id"]) for row in rows})
    return state, participation, names, scales


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise GateFailure(f"immutable output already exists: {output}")
    output.mkdir(parents=True)
    sequence: list[dict[str, Any]] = []

    initial = fetch_month(YEAR, FIRST_MONTH)
    initial_hash = gzip_json_new(output / "structured_months" / f"month_{initial['period']}.json.gz", initial)
    sequence.append(
        {
            "sequence": 1,
            "event": "INITIAL_MONTH_OPENED_AND_STRUCTURED",
            "period": initial["period"],
            "sha256": initial_hash,
            "raw_archive_persisted": False,
        }
    )
    ordinary, ordinary_participation, names, scales = initialize(initial)
    states = {"ORDINARY": ordinary}
    participation_states = {"ORDINARY": ordinary_participation}
    controls = {
        "quantity": ordinary.quantity_model.clone(),
        "unit_value": ordinary.unit_value_model.clone(),
        "participation": ordinary_participation.fork(),
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
    monthly_results: list[dict[str, Any]] = []

    for training_month, target_month in one_to_one_transitions():
        training_period = f"{YEAR:04d}-{training_month:02d}"
        target_period = f"{YEAR:04d}-{target_month:02d}"
        regime = "YEAR_END_UNCALIBRATED" if target_month == 12 else "ORDINARY"
        if regime not in states:
            states[regime] = states["ORDINARY"].fork()
            participation_states[regime] = participation_states["ORDINARY"].fork()
        state = states[regime]
        participation = participation_states[regime]
        if max(period_index(item[-1]["period"]) for item in state.history.values() if item) != period_index(training_period):
            raise GateFailure("posterior knowledge cut is not the immediately preceding month")

        candidates = [state.known[key] for key in sorted(state.known)]
        if not candidates:
            raise GateFailure(f"no forecastable cells before {target_period}")
        # Extend structural identity after first appearance without updating
        # the January-frozen control with any later outcome counts.
        controls["participation"].admit(candidates)

        def design(row: dict[str, Any], variable: str) -> np.ndarray:
            center, scale = (
                (scales["quantity_center"], scales["quantity_scale"])
                if variable == "weight_kg"
                else (scales["unit_value_center"], scales["unit_value_scale"])
            )
            return build_features(
                row,
                target_period,
                variable,
                state,
                names,
                center,
                scale,
                scales["quantity_center"],
                scales["quantity_scale"],
            )

        quantity_x = np.vstack([design(row, "weight_kg") for row in candidates])
        value_x = np.vstack([design(row, "statistical_unit_value_eur_per_kg") for row in candidates])
        quantity_predictions = state.quantity_model.predict(quantity_x)
        value_predictions = state.unit_value_model.predict(value_x)
        frozen_rows: list[dict[str, Any]] = []
        for row, qdist, vdist in zip(candidates, quantity_predictions, value_predictions):
            cell_id = str(row["cell_id"])
            last = state.history[cell_id][-1]
            frozen_rows.append(
                {
                    "cell_id": cell_id,
                    "participation_probability": participation.predict(cell_id),
                    "quantity": prediction(qdist, "weight_kg"),
                    "statistical_unit_value": prediction(vdist, "statistical_unit_value_eur_per_kg"),
                    "persistence": {
                        "weight_kg": row_value(last, "weight_kg"),
                        "statistical_unit_value_eur_per_kg": row_value(
                            last, "statistical_unit_value_eur_per_kg"
                        ),
                    },
                    "last_observation_period": last["period"],
                }
            )
        prior_state = {
            "quantity": state.quantity_model.serializable(),
            "unit_value": state.unit_value_model.serializable(),
            "participation": participation.serializable(),
            "regime": regime,
        }
        prior_hash = sha256_bytes(canonical_bytes(prior_state))
        freeze = {
            "schema_version": SCHEMA,
            "transition": f"{training_period}->{target_period}",
            "training_observation_unit": training_period,
            "target_prediction_unit": target_period,
            "block_contract": "EXACTLY_ONE_MONTH_TO_EXACTLY_ONE_MONTH",
            "knowledge_cut": training_period,
            "prior_state_sha256": prior_hash,
            "origin_frozen_state_sha256": control_hash,
            "regime": regime,
            "predictions": frozen_rows,
            "status": "FROZEN_BEFORE_TARGET_ARCHIVE_OPENED_IN_THIS_REPLAY",
            "claim_boundary": "retrospective replay; historical releases were public before execution",
        }
        freeze_hash = gzip_json_new(
            output / "freezes" / f"freeze_{target_period}.json.gz", freeze
        )
        sequence.append(
            {
                "sequence": len(sequence) + 1,
                "event": "FREEZE_WRITTEN",
                "training_period": training_period,
                "target_period": target_period,
                "sha256": freeze_hash,
            }
        )

        outcome = fetch_month(YEAR, target_month)
        if outcome.get("period") != target_period:
            raise GateFailure(
                f"target period mismatch {outcome.get('period')!r} != {target_period!r}"
            )
        outcome_hash = gzip_json_new(
            output / "structured_months" / f"month_{target_period}.json.gz", outcome
        )
        sequence.append(
            {
                "sequence": len(sequence) + 1,
                "event": "TARGET_MONTH_OPENED_AND_STRUCTURED",
                "target_period": target_period,
                "sha256": outcome_hash,
                "after_freeze_sha256": freeze_hash,
                "raw_archive_persisted": False,
            }
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
            participation_scores.append(
                {
                    "cell_id": cell_id,
                    "actual": actual_presence,
                    "bma_probability": probability,
                    "origin_frozen_probability": control_probability,
                    "bma_brier": brier(actual_presence, probability),
                    "origin_frozen_brier": brier(actual_presence, control_probability),
                    "bma_log_loss": log_loss(actual_presence, probability),
                    "origin_frozen_log_loss": log_loss(actual_presence, control_probability),
                }
            )
            if not actual_presence:
                continue
            actual = observed_by[cell_id]
            for variable, frozen_key, score_target in (
                ("weight_kg", "quantity", quantity_scores),
                (
                    "statistical_unit_value_eur_per_kg",
                    "statistical_unit_value",
                    value_scores,
                ),
            ):
                actual_value = row_value(actual, variable)
                persistence_value = frozen["persistence"][variable]
                if actual_value is None or persistence_value is None:
                    continue
                point = float(frozen[frozen_key]["point_median"])
                model_error = abs(transformed(actual_value, variable) - transformed(point, variable))
                baseline_error = abs(
                    transformed(actual_value, variable) - transformed(float(persistence_value), variable)
                )
                score_target.append(
                    {
                        "cell_id": cell_id,
                        "actual": actual_value,
                        "bma_point": point,
                        "persistence": persistence_value,
                        "bma_error": model_error,
                        "persistence_error": baseline_error,
                        "bma_vs_persistence": local_verdict(model_error, baseline_error),
                        "covered_90": frozen[frozen_key]["lower_90_natural"]
                        <= actual_value
                        <= frozen[frozen_key]["upper_90_natural"],
                    }
                )

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
        quantity_update_x = np.vstack([design(row, "weight_kg") for row in update_rows])
        quantity_update_y = np.asarray(
            [transformed(float(row["weight_kg"]), "weight_kg") for row in update_rows]
        )
        state.quantity_model.update(quantity_update_x, quantity_update_y)
        value_rows = [
            row
            for row in update_rows
            if row_value(row, "statistical_unit_value_eur_per_kg") is not None
        ]
        value_update_x = np.vstack(
            [design(row, "statistical_unit_value_eur_per_kg") for row in value_rows]
        )
        value_update_y = np.asarray(
            [
                transformed(
                    float(row["statistical_unit_value_eur_per_kg"]),
                    "statistical_unit_value_eur_per_kg",
                )
                for row in value_rows
            ]
        )
        state.unit_value_model.update(value_update_x, value_update_y)
        participation.admit(update_rows)
        participation.update(set(observed_by))
        for row in update_rows:
            state.known[str(row["cell_id"])] = row
            state.history.setdefault(str(row["cell_id"]), []).append(
                {**row, "period": target_period}
            )

        posterior = {
            "schema_version": SCHEMA,
            "compiled_from_target": target_period,
            "adjudication_sha256": adjudication_hash,
            "knowledge_effect": "FUTURE_ONLY_ONE_MONTH_STEP",
            "next_training_observation_unit": target_period,
            "quantity_model": state.quantity_model.serializable(),
            "unit_value_model": state.unit_value_model.serializable(),
            "participation_model": participation.serializable(),
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
        z_post_hash = write_json_new(output / "z_post" / f"z_post_{target_period}.json", z_post)
        sequence.append(
            {
                "sequence": len(sequence) + 1,
                "event": "ADJUDICATION_AND_Z_POST_WRITTEN",
                "target_period": target_period,
                "adjudication_sha256": adjudication_hash,
                "prior_sha256": posterior_hash,
                "z_post_sha256": z_post_hash,
            }
        )
        monthly_results.append(
            {
                "training_period": training_period,
                "target_period": target_period,
                "regime": regime,
                "participation_n": len(participation_scores),
                "participation_bma_brier": mean([item["bma_brier"] for item in participation_scores]),
                "participation_origin_frozen_brier": mean(
                    [item["origin_frozen_brier"] for item in participation_scores]
                ),
                "quantity_n": len(quantity_scores),
                "quantity_bma_male": mean([item["bma_error"] for item in quantity_scores]),
                "quantity_persistence_male": mean(
                    [item["persistence_error"] for item in quantity_scores]
                ),
                "quantity_wins": sum(
                    item["bma_vs_persistence"] == "LOCAL_WIN" for item in quantity_scores
                ),
                "quantity_losses": sum(
                    item["bma_vs_persistence"] == "LOCAL_LOSS" for item in quantity_scores
                ),
                "unit_value_n": len(value_scores),
                "unit_value_bma_male": mean([item["bma_error"] for item in value_scores]),
                "unit_value_persistence_male": mean(
                    [item["persistence_error"] for item in value_scores]
                ),
                "unit_value_wins": sum(
                    item["bma_vs_persistence"] == "LOCAL_WIN" for item in value_scores
                ),
                "unit_value_losses": sum(
                    item["bma_vs_persistence"] == "LOCAL_LOSS" for item in value_scores
                ),
                "first_appearance_cells": len(observed_by.keys() - frozen_by.keys()),
            }
        )

    result = {
        "schema_version": SCHEMA,
        "status": "EXECUTED_RETROSPECTIVE_ONE_MONTH_TO_ONE_MONTH_REPLAY",
        "transition_count": len(monthly_results),
        "transitions": monthly_results,
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
    result = run(args.output)
    print(f"status={result['status']} transitions={result['transition_count']}")


if __name__ == "__main__":
    main()
