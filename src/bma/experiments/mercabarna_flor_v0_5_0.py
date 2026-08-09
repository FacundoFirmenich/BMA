#!/usr/bin/env python3
"""Mercabarna Flor full-July training and frozen 21-31 July evaluation.

Training uses complete structured observations from 1-20 July 2026. Targets
21-31 are opened only after their freezes. The hurdle separates system activity,
participation conditional on activity, quantity conditional on participation,
and a price layer that remains vetoed when local variation is not identifiable.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from bma.custody import write_json_new, write_manifest
from bma.experiments import mercabarna_flor_v0_4_1 as base

SCHEMA = "bma.mercabarna.flor.full-july.v0.5.0"
TRAIN_START = date(2026, 7, 1)
TRAIN_END = date(2026, 7, 20)
TARGET_START = date(2026, 7, 21)
TARGET_END = date(2026, 7, 31)
COMPLETENESS_WITNESS = "USER_ASSERTED_COMPLETE_VALID_2019_2026"


class GateFailure(RuntimeError):
    pass


def days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def regime_for(day: date) -> str:
    if day == date(2026, 7, 31):
        return "MONTH_END_PRE_AUGUST_UNCALIBRATED"
    if day.weekday() == 5:
        return "SATURDAY"
    if day.weekday() == 6:
        return "SUNDAY_CLOSED"
    return "ORDINARY"


def load_training_day(root: Path, target: date) -> dict[str, Any]:
    directory = root / "observations" / target.isoformat()
    paths = sorted(directory.glob("origin_*.json"))
    if not paths:
        raise GateFailure(f"missing complete training objects for {target.isoformat()}")
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("date") != target.isoformat():
            raise GateFailure(f"training date mismatch: {path}")
        if document.get("completeness_witness") != COMPLETENESS_WITNESS:
            raise GateFailure(f"missing authorized completeness witness: {path}")
        receipts.append(
            {
                "origin_code": str(document["origin_code"]),
                "structured_file": str(path.resolve()),
                "structured_sha256": base.sha256_file(path),
                "row_count": len(document["rows"]),
            }
        )
        for row in document["rows"]:
            cell_id = str(row["cell_id"])
            if cell_id in seen:
                raise GateFailure(f"duplicate training cell {cell_id} on {target.isoformat()}")
            seen.add(cell_id)
            product = str(row["product"])
            rows.append(
                {
                    "cell_id": cell_id,
                    "product": product,
                    "origin_code": str(row["origin_code"]),
                    "origin_label": str(row["origin_label"]),
                    "family": base.family_of(product),
                    "unit_count": int(row["unit_count"]),
                    "price_eur_per_unit": float(row["price_eur_per_unit"]),
                }
            )
    return {
        "schema_version": SCHEMA,
        "date": target.isoformat(),
        "publication_state": "COMPLETE_POSITIVE_ROWS" if rows else "COMPLETE_ZERO_ROWS_FOR_PARTICIPATION_ONLY",
        "completeness_witness": COMPLETENESS_WITNESS,
        "rows": sorted(rows, key=lambda row: row["cell_id"]),
        "source_receipts": receipts,
    }


@dataclass
class ActivityModel:
    successes: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    failures: dict[int, int] = field(default_factory=lambda: defaultdict(int))

    def update(self, day: date, active: bool) -> None:
        (self.successes if active else self.failures)[day.weekday()] += 1

    def predict(self, day: date) -> float:
        success = self.successes[day.weekday()]
        failure = self.failures[day.weekday()]
        return (1.0 + success) / (2.0 + success + failure)

    def clone(self) -> "ActivityModel":
        return copy.deepcopy(self)


@dataclass
class ParticipationModel:
    metadata: dict[str, dict[str, str]]
    success: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    trials: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    last: dict[str, int] = field(default_factory=dict)

    def _keys(self, cell_id: str) -> dict[str, str]:
        item = self.metadata[cell_id]
        return {
            "global": "GLOBAL",
            "family": item["family"],
            "origin": item["origin_code"],
            "product": item["product"],
            "cell": cell_id,
        }

    def update(self, present: set[str]) -> None:
        for cell_id in sorted(self.metadata):
            outcome = int(cell_id in present)
            for layer, key in self._keys(cell_id).items():
                self.success[layer][key] += outcome
                self.trials[layer][key] += 1
            self.last[cell_id] = outcome

    def _rate(self, layer: str, key: str, prior_mean: float, prior_strength: float) -> float:
        return (self.success[layer][key] + prior_strength * prior_mean) / (
            self.trials[layer][key] + prior_strength
        )

    def predict(self, cell_id: str) -> float:
        keys = self._keys(cell_id)
        global_rate = self._rate("global", keys["global"], 0.5, 2.0)
        family_rate = self._rate("family", keys["family"], global_rate, 4.0)
        origin_rate = self._rate("origin", keys["origin"], global_rate, 4.0)
        product_rate = self._rate("product", keys["product"], global_rate, 4.0)
        hyper_mean = (family_rate + origin_rate + product_rate) / 3.0
        return self._rate("cell", keys["cell"], hyper_mean, 6.0)

    def clone(self) -> "ParticipationModel":
        return copy.deepcopy(self)


def brier(actual: int, probability: float) -> float:
    return (actual - probability) ** 2


def log_loss(actual: int, probability: float) -> float:
    bounded = min(max(probability, 1e-9), 1.0 - 1e-9)
    return -(actual * math.log(bounded) + (1 - actual) * math.log(1.0 - bounded))


def initialize_quantity_states(training: list[dict[str, Any]]) -> tuple[
    dict[str, base.RegimeState],
    dict[str, base.BayesianLinearState],
    dict[str, float],
    list[str],
]:
    all_rows = [row for document in training for row in document["rows"]]
    if not all_rows:
        raise GateFailure("training window contains no positive rows")
    origins = sorted({row["origin_code"] for row in all_rows})
    products = sorted({row["product"] for row in all_rows})
    names = base.feature_names(origins, products)
    quantity_logs = [math.log1p(float(row["unit_count"])) for row in all_rows]
    price_logs = [math.log(max(float(row["price_eur_per_unit"]), 1e-12)) for row in all_rows]
    quantity_center, quantity_scale = base.robust_center_scale(quantity_logs)
    price_center, price_scale = base.robust_center_scale(price_logs)

    def new_state() -> base.RegimeState:
        return base.RegimeState(
            base.BayesianLinearState.prior(names, quantity_center, quantity_scale**2),
            base.BayesianLinearState.prior(names, price_center, price_scale**2),
            defaultdict(list),
            {},
        )

    states = {"ORDINARY": new_state(), "SATURDAY": new_state()}

    def design(row: dict[str, Any], target: date, variable: str, state: base.RegimeState) -> np.ndarray:
        center, scale = (quantity_center, quantity_scale) if variable == "quantity" else (price_center, price_scale)
        return base.build_features(
            row,
            target,
            state.history,
            variable,
            names,
            center,
            scale,
            quantity_center,
            quantity_scale,
        )

    for document in training:
        target = date.fromisoformat(document["date"])
        regime = regime_for(target)
        if regime not in states or not document["rows"]:
            continue
        state = states[regime]
        rows = document["rows"]
        quantity_x = np.vstack([design(row, target, "quantity", state) for row in rows])
        quantity_y = np.asarray([base.transformed(float(row["unit_count"]), "quantity") for row in rows])
        state.quantity_model.update(quantity_x, quantity_y)
        eligible_price = [
            row for row in rows if base.price_gate(state.history.get(row["cell_id"], [])) == "SHADOW_IDENTIFIABLE_VARIATION"
        ]
        if eligible_price:
            price_x = np.vstack([design(row, target, "price", state) for row in eligible_price])
            price_y = np.asarray([base.transformed(float(row["price_eur_per_unit"]), "price") for row in eligible_price])
            state.price_model.update(price_x, price_y)
        for row in rows:
            state.known[row["cell_id"]] = row
            state.history.setdefault(row["cell_id"], []).append({**row, "date": target.isoformat()})
    controls = {name: state.quantity_model.clone() for name, state in states.items()}
    scales = {
        "quantity_center": quantity_center,
        "quantity_scale": quantity_scale,
        "price_center": price_center,
        "price_scale": price_scale,
    }
    return states, controls, scales, names


def summarize(records: list[dict[str, Any]], variable: str, comparator: str) -> dict[str, Any]:
    eligible = [record[variable] for record in records if record[variable].get(f"{comparator}_error") is not None]
    return {
        "n": len(eligible),
        "bma_mean_error": float(np.mean([item["bma_error"] for item in eligible])) if eligible else None,
        f"{comparator}_mean_error": float(np.mean([item[f"{comparator}_error"] for item in eligible])) if eligible else None,
        "wins": sum(item[f"bma_vs_{comparator}"] == "LOCAL_WIN" for item in eligible),
        "losses": sum(item[f"bma_vs_{comparator}"] == "LOCAL_LOSS" for item in eligible),
        "ties": sum(item[f"bma_vs_{comparator}"] == "LOCAL_TIE" for item in eligible),
    }


def run(training_root: Path, evaluation_roots: list[Path], output: Path) -> dict[str, Any]:
    if output.exists():
        raise GateFailure(f"immutable output already exists: {output}")
    output.mkdir(parents=True)
    training = [load_training_day(training_root, target) for target in days(TRAIN_START, TRAIN_END)]
    all_training_rows = [row for document in training for row in document["rows"]]
    metadata = {
        row["cell_id"]: {
            "product": row["product"],
            "origin_code": row["origin_code"],
            "family": row["family"],
        }
        for row in all_training_rows
    }
    quantity_states, quantity_controls, scales, names = initialize_quantity_states(training)
    activity = ActivityModel()
    participation_by_regime = {
        "ORDINARY": ParticipationModel(metadata),
        "SATURDAY": ParticipationModel(metadata),
    }
    for document in training:
        target = date.fromisoformat(document["date"])
        active = bool(document["rows"])
        activity.update(target, active)
        regime = regime_for(target)
        if active and regime in participation_by_regime:
            participation_by_regime[regime].update({row["cell_id"] for row in document["rows"]})
    activity_control = activity.clone()
    participation_controls = {name: model.clone() for name, model in participation_by_regime.items()}
    sequence: list[dict[str, Any]] = []
    activity_scores: list[dict[str, Any]] = []
    participation_scores: list[dict[str, Any]] = []
    quantity_scores: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []
    sequence_number = 0

    def design(row: dict[str, Any], target: date, variable: str, state: base.RegimeState) -> np.ndarray:
        center = scales[f"{variable}_center"]
        scale = scales[f"{variable}_scale"]
        return base.build_features(
            row,
            target,
            state.history,
            variable,
            names,
            center,
            scale,
            scales["quantity_center"],
            scales["quantity_scale"],
        )

    for target in days(TARGET_START, TARGET_END):
        target_key = target.isoformat()
        regime = regime_for(target)
        if regime == "MONTH_END_PRE_AUGUST_UNCALIBRATED" and regime not in quantity_states:
            quantity_states[regime] = quantity_states["ORDINARY"].fork()
            quantity_controls[regime] = quantity_controls["ORDINARY"].clone()
            participation_by_regime[regime] = participation_by_regime["ORDINARY"].clone()
            participation_controls[regime] = participation_controls["ORDINARY"].clone()
        model_regime = regime if regime in quantity_states else "ORDINARY"
        state = quantity_states[model_regime]
        control = quantity_controls[model_regime]
        participation_model = participation_by_regime.get(model_regime, participation_by_regime["ORDINARY"])
        participation_control = participation_controls.get(model_regime, participation_controls["ORDINARY"])
        activity_probability = activity.predict(target)
        activity_origin_probability = activity_control.predict(target)
        participation_predictions = {
            cell_id: {
                "bma_probability": participation_model.predict(cell_id),
                "origin_frozen_probability": participation_control.predict(cell_id),
                "last_same_regime": participation_model.last.get(cell_id),
            }
            for cell_id in sorted(metadata)
        }
        candidates = [state.known[key] for key in sorted(state.known)] if regime != "SUNDAY_CLOSED" else []
        frozen_quantity: list[dict[str, Any]] = []
        if candidates:
            quantity_x = np.vstack([design(row, target, "quantity", state) for row in candidates])
            adaptive_predictions = state.quantity_model.predict(quantity_x)
            control_predictions = control.predict(quantity_x)
            for row, adaptive, frozen, vector in zip(candidates, adaptive_predictions, control_predictions, quantity_x):
                history = state.history[row["cell_id"]]
                last = history[-1]
                strong = base.strong_baseline(row, state.history, "quantity")
                frozen_quantity.append(
                    {
                        "cell_id": row["cell_id"],
                        "product": row["product"],
                        "origin_code": row["origin_code"],
                        "bma": base.prediction_value(adaptive, "quantity"),
                        "origin_frozen": base.prediction_value(frozen, "quantity"),
                        "persistence": float(last["unit_count"]),
                        "strong": strong,
                        "history_count": len(history),
                        "design_vector": vector.tolist(),
                    }
                )
        freeze = {
            "schema_version": SCHEMA,
            "target_date": target_key,
            "regime": regime,
            "knowledge_cut": (target - timedelta(days=1)).isoformat(),
            "training_range": [TRAIN_START.isoformat(), TRAIN_END.isoformat()],
            "activity": {
                "bma_probability": activity_probability,
                "origin_frozen_probability": activity_origin_probability,
            },
            "participation_conditional_on_activity": participation_predictions,
            "quantity_conditional_on_participation": frozen_quantity,
            "price": {"status": "DEGENERATE_METRIC_VETO"},
            "status": "FROZEN_BEFORE_TARGET_STRUCTURED_SOURCE_OPENED",
        }
        freeze_hash = write_json_new(output / "freezes" / f"freeze_{target_key}.json", freeze)
        sequence_number += 1
        sequence.append({"sequence": sequence_number, "event": "FREEZE_WRITTEN", "target_date": target_key, "sha256": freeze_hash})
        outcome, outcome_hash = base.compile_structured_day(evaluation_roots, target, output)
        sequence_number += 1
        sequence.append(
            {
                "sequence": sequence_number,
                "event": "TARGET_STRUCTURED_SOURCE_OPENED_AND_COMPILED",
                "target_date": target_key,
                "sha256": outcome_hash,
                "after_freeze_sha256": freeze_hash,
            }
        )
        active = bool(outcome["rows"])
        activity_scores.append(
            {
                "date": target_key,
                "actual": int(active),
                "bma_probability": activity_probability,
                "origin_frozen_probability": activity_origin_probability,
                "bma_brier": brier(int(active), activity_probability),
                "origin_frozen_brier": brier(int(active), activity_origin_probability),
            }
        )
        activity.update(target, active)
        observed_by = {row["cell_id"]: row for row in outcome["rows"]}
        if active:
            for cell_id, prediction in participation_predictions.items():
                actual = int(cell_id in observed_by)
                item = {
                    "date": target_key,
                    "regime": regime,
                    "cell_id": cell_id,
                    "actual": actual,
                    "bma_probability": prediction["bma_probability"],
                    "origin_frozen_probability": prediction["origin_frozen_probability"],
                    "bma_brier": brier(actual, prediction["bma_probability"]),
                    "origin_frozen_brier": brier(actual, prediction["origin_frozen_probability"]),
                    "bma_log_loss": log_loss(actual, prediction["bma_probability"]),
                    "origin_frozen_log_loss": log_loss(actual, prediction["origin_frozen_probability"]),
                }
                participation_scores.append(item)
            participation_model.update(set(observed_by) & set(metadata))
        frozen_by = {row["cell_id"]: row for row in frozen_quantity}
        day_quantity_scores: list[dict[str, Any]] = []
        for cell_id in sorted(frozen_by.keys() & observed_by.keys()):
            prediction = frozen_by[cell_id]
            actual = float(observed_by[cell_id]["unit_count"])
            point = float(prediction["bma"]["point_median"])
            model_error, persistence_error, persistence_verdict = base._score_value(
                actual, point, float(prediction["persistence"]), "quantity"
            )
            _, origin_error, origin_verdict = base._score_value(
                actual, point, float(prediction["origin_frozen"]["point_median"]), "quantity"
            )
            strong = prediction["strong"]
            if strong is None:
                strong_error = None
                strong_verdict = "NOT_ESTIMABLE"
            else:
                _, strong_error, strong_verdict = base._score_value(actual, point, float(strong), "quantity")
            item = {
                "date": target_key,
                "regime": regime,
                "cell_id": cell_id,
                "quantity": {
                    "actual": actual,
                    "bma_point": point,
                    "bma_error": model_error,
                    "persistence_error": persistence_error,
                    "origin_frozen_error": origin_error,
                    "strong_error": strong_error,
                    "bma_vs_persistence": persistence_verdict,
                    "bma_vs_origin_frozen": origin_verdict,
                    "bma_vs_strong": strong_verdict,
                },
            }
            quantity_scores.append(item)
            day_quantity_scores.append(item)
        if active and regime in quantity_states and outcome["rows"]:
            update_rows = outcome["rows"]
            update_x = np.vstack([design(row, target, "quantity", state) for row in update_rows])
            update_y = np.asarray([base.transformed(float(row["unit_count"]), "quantity") for row in update_rows])
            state.quantity_model.update(update_x, update_y)
            for row in update_rows:
                state.known[row["cell_id"]] = row
                state.history.setdefault(row["cell_id"], []).append({**row, "date": target_key})
        adjudication = {
            "schema_version": SCHEMA,
            "target_date": target_key,
            "regime": regime,
            "freeze_sha256": freeze_hash,
            "outcome_sha256": outcome_hash,
            "activity_actual": active,
            "participation_scored": len(metadata) if active else 0,
            "quantity_scored": len(day_quantity_scores),
            "new_out_of_training_universe": sorted(set(observed_by) - set(metadata)),
            "price_status": "DEGENERATE_METRIC_VETO",
            "status": "ADJUDICATED_COMPLETE_OUTCOME",
        }
        write_json_new(output / "adjudications" / f"adjudication_{target_key}.json", adjudication)
        daily.append(
            {
                "date": target_key,
                "regime": regime,
                "active": active,
                "participation_scored": adjudication["participation_scored"],
                "quantity_scored": adjudication["quantity_scored"],
                "new_cells": len(adjudication["new_out_of_training_universe"]),
            }
        )

    activity_summary = {
        "n": len(activity_scores),
        "bma_mean_brier": float(np.mean([item["bma_brier"] for item in activity_scores])),
        "origin_frozen_mean_brier": float(np.mean([item["origin_frozen_brier"] for item in activity_scores])),
    }
    participation_summary = {
        "n": len(participation_scores),
        "bma_mean_brier": float(np.mean([item["bma_brier"] for item in participation_scores])),
        "origin_frozen_mean_brier": float(np.mean([item["origin_frozen_brier"] for item in participation_scores])),
        "bma_mean_log_loss": float(np.mean([item["bma_log_loss"] for item in participation_scores])),
        "origin_frozen_mean_log_loss": float(np.mean([item["origin_frozen_log_loss"] for item in participation_scores])),
    }
    quantity_origin = summarize(quantity_scores, "quantity", "origin_frozen")
    summary = {
        "schema_version": SCHEMA,
        "status": "EXECUTED_RETROSPECTIVE_DEVELOPMENT_REPLAY",
        "training_range": [TRAIN_START.isoformat(), TRAIN_END.isoformat()],
        "target_range": [TARGET_START.isoformat(), TARGET_END.isoformat()],
        "training": {
            "days": len(training),
            "active_days": sum(bool(document["rows"]) for document in training),
            "positive_rows": len(all_training_rows),
            "cells": len(metadata),
            "products": len({item["product"] for item in metadata.values()}),
            "origins": len({item["origin_code"] for item in metadata.values()}),
            "completeness_witness": COMPLETENESS_WITNESS,
        },
        "daily": daily,
        "activity": activity_summary,
        "participation": participation_summary,
        "quantity_vs_origin_frozen": quantity_origin,
        "quantity_vs_persistence": summarize(quantity_scores, "quantity", "persistence"),
        "quantity_vs_strong": summarize(quantity_scores, "quantity", "strong"),
        "adaptive_gain_vs_origin_frozen": (
            quantity_origin["origin_frozen_mean_error"] - quantity_origin["bma_mean_error"]
            if quantity_origin["n"]
            else None
        ),
        "price": {
            "status": "DEGENERATE_METRIC_VETO",
            "training_cells_with_two_or_more_distinct_prices": sum(
                len({row["price_eur_per_unit"] for document in training for row in document["rows"] if row["cell_id"] == cell_id})
                >= 2
                for cell_id in metadata
            ),
        },
        "causal_ordering": {
            "status": "PASS_SEQUENCE_LEDGER",
            "freeze_precedes_target_open_for_every_target": True,
            "events": sequence,
        },
        "claim_boundary": {
            "prospective_evidence": False,
            "global_superiority": False,
            "commercial_validation": False,
            "canonical_product_promotion": "PENDING_INDEPENDENT_REVIEW",
            "activity_and_participation_model": "MODULAR_EMPIRICAL_BAYES_HURDLE",
        },
    }
    write_json_new(output / "RESULT_SUMMARY.json", summary)
    write_json_new(output / "ACTIVITY_SCORES.json", {"schema_version": SCHEMA, "scores": activity_scores})
    write_json_new(output / "PARTICIPATION_SCORES.json", {"schema_version": SCHEMA, "scores": participation_scores})
    write_json_new(output / "QUANTITY_SCORES.json", {"schema_version": SCHEMA, "scores": quantity_scores})
    write_json_new(output / "CAUSAL_SEQUENCE_LEDGER.json", {"schema_version": SCHEMA, "events": sequence})
    _, manifest_hash = write_manifest(output)
    return {**summary, "manifest_sha256": manifest_hash, "output": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--source-v01", type=Path, required=True)
    parser.add_argument("--source-v02", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.training, [args.source_v01, args.source_v02], args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
