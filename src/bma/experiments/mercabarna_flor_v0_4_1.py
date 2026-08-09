#!/usr/bin/env python3
"""Corrected, bounded Mercabarna Flor retrospective replay.

This module is an experiment, not the BMA product definition. It consumes only
the structured JSON observations produced by the historical connector. For each
target day it writes the freeze before opening that target's structured source
objects, then adjudicates and updates only the corresponding regime state.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.stats import t as student_t

from bma.custody import canonical_bytes, sha256_bytes, sha256_file, write_json_new, write_manifest

SCHEMA = "bma.mercabarna.flor.retrospective.v0.4.1"
START = date(2026, 7, 20)
END = date(2026, 7, 31)


class GateFailure(RuntimeError):
    pass


def family_of(product: str) -> str:
    upper = product.upper()
    if "ARBOLES, VERDES Y COMPLEMENTOS" in upper:
        return "ARBOLES_VERDES_COMPLEMENTOS"
    if "FLORES I PLANTAS" in upper:
        return "FLORES_I_PLANTAS"
    return "OTHER"


def product_feature(product: str) -> str:
    return f"product:{hashlib.sha256(product.encode('utf-8')).hexdigest()[:16]}"


def regime_for(day: date) -> str:
    if day == date(2026, 7, 31):
        return "MONTH_END_PRE_AUGUST_UNCALIBRATED"
    if day.weekday() == 5:
        return "SATURDAY_ACTIVE_UNCALIBRATED"
    return "ORDINARY"


def observation_paths(source_roots: Iterable[Path], target: date) -> list[Path]:
    paths: list[Path] = []
    relative = Path("observations") / target.isoformat()
    for root in source_roots:
        directory = root / relative
        if directory.is_dir():
            paths.extend(sorted(directory.glob("origin_*.json")))
    if not paths:
        raise GateFailure(f"no structured observation objects for {target.isoformat()}")
    return paths


def compile_structured_day(source_roots: list[Path], target: date, output: Path) -> tuple[dict[str, Any], str]:
    """Open and compile one target day. The caller controls causal ordering."""
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    seen_cells: set[str] = set()
    seen_origin_hash: dict[str, str] = {}
    for path in observation_paths(source_roots, target):
        digest = sha256_file(path)
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        if document.get("date") != target.isoformat():
            raise GateFailure(f"target date mismatch in {path}")
        if not isinstance(document.get("rows"), list):
            raise GateFailure(f"missing rows in {path}")
        discarded = document.get("metadata", {}).get("forbidden_accumulated_columns_discarded")
        if not isinstance(discarded, list) or len(discarded) != 2:
            raise GateFailure(f"accumulated-column exclusion not evidenced in {path}")
        origin = str(document.get("origin_code"))
        if origin == "32" or any(str(row.get("origin_label", "")).upper() == "ARGENTINA" for row in document["rows"]):
            raise GateFailure("Argentina is outside the authorized replay scope")
        if origin in seen_origin_hash:
            if seen_origin_hash[origin] == digest:
                continue
            raise GateFailure(f"conflicting duplicate origin {origin} on {target.isoformat()}")
        seen_origin_hash[origin] = digest
        receipts.append(
            {
                "origin_code": origin,
                "structured_file": str(path.resolve()),
                "structured_sha256": digest,
                "row_count": len(document["rows"]),
            }
        )
        for source_row in document["rows"]:
            cell_id = str(source_row["cell_id"])
            if cell_id in seen_cells:
                raise GateFailure(f"duplicate cell {cell_id} on {target.isoformat()}")
            seen_cells.add(cell_id)
            units = int(source_row["unit_count"])
            price = float(source_row["price_eur_per_unit"])
            if units <= 0 or price < 0 or not math.isfinite(price):
                raise GateFailure(f"invalid positive transaction: {cell_id}")
            product = str(source_row["product"])
            rows.append(
                {
                    "cell_id": cell_id,
                    "product": product,
                    "origin_code": origin,
                    "origin_label": str(source_row["origin_label"]),
                    "family": family_of(product),
                    "unit_count": units,
                    "price_eur_per_unit": price,
                }
            )
    publication_state = "POSITIVE_ROWS" if rows else "PENDING_EMPTY_NOT_ZERO"
    compiled = {
        "schema_version": SCHEMA,
        "date": target.isoformat(),
        "publication_state": publication_state,
        "rows": sorted(rows, key=lambda row: row["cell_id"]),
        "source_receipts": sorted(receipts, key=lambda item: item["origin_code"]),
        "custody_boundary": "compiled from structured JSON only; raw source was not opened by BMA",
    }
    path = output / "structured_days" / f"market_day_{target.isoformat()}.json"
    return compiled, write_json_new(path, compiled)


@dataclass
class BayesianLinearState:
    names: list[str]
    precision: np.ndarray
    eta: np.ndarray
    a: float
    b: float
    observations: int = 0

    @classmethod
    def prior(cls, names: list[str], intercept: float, variance: float) -> "BayesianLinearState":
        size = len(names)
        diagonal = np.full(size, 4.0, dtype=float)
        diagonal[0] = 0.04
        for index, name in enumerate(names):
            if name.startswith("num:"):
                diagonal[index] = 1.0
        precision = np.diag(diagonal)
        mean = np.zeros(size, dtype=float)
        mean[0] = intercept
        a = 2.5
        b = max(variance, 0.04) * (a - 1.0)
        return cls(names, precision, precision @ mean, a, b)

    def clone(self) -> "BayesianLinearState":
        return BayesianLinearState(self.names[:], self.precision.copy(), self.eta.copy(), self.a, self.b, self.observations)

    def update(self, design: np.ndarray, outcome: np.ndarray) -> None:
        if len(outcome) == 0:
            return
        old_mean = np.linalg.solve(self.precision, self.eta)
        old_quadratic = float(old_mean @ self.precision @ old_mean)
        precision = self.precision + design.T @ design
        eta = self.eta + design.T @ outcome
        mean = np.linalg.solve(precision, eta)
        quadratic = float(mean @ precision @ mean)
        b = self.b + 0.5 * (float(outcome @ outcome) + old_quadratic - quadratic)
        if not math.isfinite(b) or b <= 0:
            raise GateFailure("invalid conjugate scale update")
        self.precision = precision
        self.eta = eta
        self.a += len(outcome) / 2.0
        self.b = b
        self.observations += len(outcome)

    def predict(self, design: np.ndarray) -> list[dict[str, float]]:
        inverse = np.linalg.inv(self.precision)
        mean = inverse @ self.eta
        degrees = 2.0 * self.a
        variance = self.b / self.a
        predictions: list[dict[str, float]] = []
        for row in design:
            location = float(row @ mean)
            scale = math.sqrt(max(variance * (1.0 + float(row @ inverse @ row)), 1e-12))
            predictions.append(
                {
                    "location": location,
                    "scale": scale,
                    "df": degrees,
                    "lower_90": float(student_t.ppf(0.05, df=degrees, loc=location, scale=scale)),
                    "upper_90": float(student_t.ppf(0.95, df=degrees, loc=location, scale=scale)),
                }
            )
        return predictions

    def serializable(self) -> dict[str, Any]:
        return {
            "feature_names": self.names,
            "precision": self.precision.tolist(),
            "eta": self.eta.tolist(),
            "a": self.a,
            "b": self.b,
            "observations_ingested": self.observations,
        }


@dataclass
class RegimeState:
    quantity_model: BayesianLinearState
    price_model: BayesianLinearState
    history: dict[str, list[dict[str, Any]]]
    known: dict[str, dict[str, Any]]

    def fork(self) -> "RegimeState":
        return RegimeState(
            self.quantity_model.clone(),
            self.price_model.clone(),
            copy.deepcopy(self.history),
            copy.deepcopy(self.known),
        )


def robust_center_scale(values: list[float]) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    center = float(np.median(array))
    mad = float(np.median(np.abs(array - center)))
    return center, max(1.4826 * mad, float(np.std(array)), 0.25)


def feature_names(origins: list[str], products: list[str]) -> list[str]:
    product_names = [product_feature(product) for product in products]
    if len(product_names) != len(set(product_names)):
        raise GateFailure("product feature digest collision")
    return (
        ["intercept"]
        + [f"origin:{origin}" for origin in origins]
        + ["family:FLORES_I_PLANTAS", "family:ARBOLES_VERDES_COMPLEMENTOS", "family:OTHER"]
        + product_names
        + [
            "num:lag",
            "num:rolling3",
            "num:cross_product",
            "num:gap7",
            "num:lag_available",
            "num:cross_available",
            "num:dow_sin",
            "num:dow_cos",
            "num:saturday",
            "num:month_end",
            "num:lag_quantity",
        ]
    )


def value_of(record: dict[str, Any], variable: str) -> float:
    return float(record["unit_count"] if variable == "quantity" else record["price_eur_per_unit"])


def build_features(
    row: dict[str, Any],
    target: date,
    history: dict[str, list[dict[str, Any]]],
    variable: str,
    names: list[str],
    center: float,
    scale: float,
    quantity_center: float,
    quantity_scale: float,
) -> np.ndarray:
    full_history = history.get(row["cell_id"], [])
    prior = [item for item in full_history if date.fromisoformat(item["date"]) < target]
    if len(prior) != len(full_history):
        raise GateFailure("future observation entered feature history")
    last = prior[-1] if prior else None
    values = [math.log1p(value_of(item, variable)) for item in prior]
    lag = values[-1] if values else center
    rolling = float(np.mean(values[-3:])) if values else center
    gap = (target - date.fromisoformat(last["date"])).days if last else 99
    cross: list[float] = []
    for records in history.values():
        candidates = [
            item
            for item in records
            if item["product"] == row["product"] and date.fromisoformat(item["date"]) < target
        ]
        if candidates:
            cross.append(math.log1p(value_of(candidates[-1], variable)))
    cross_value = float(np.median(cross)) if cross else center
    lag_quantity = math.log1p(float(last["unit_count"])) if last else quantity_center
    mapping = {name: 0.0 for name in names}
    mapping["intercept"] = 1.0
    origin_name = f"origin:{row['origin_code']}"
    if origin_name in mapping:
        mapping[origin_name] = 1.0
    family_name = f"family:{row['family']}"
    if family_name in mapping:
        mapping[family_name] = 1.0
    product_name = product_feature(row["product"])
    if product_name in mapping:
        mapping[product_name] = 1.0
    mapping["num:lag"] = (lag - center) / scale
    mapping["num:rolling3"] = (rolling - center) / scale
    mapping["num:cross_product"] = (cross_value - center) / scale
    mapping["num:gap7"] = min(gap, 35) / 7.0
    mapping["num:lag_available"] = float(bool(last))
    mapping["num:cross_available"] = float(bool(cross))
    mapping["num:dow_sin"] = math.sin(2.0 * math.pi * target.weekday() / 7.0)
    mapping["num:dow_cos"] = math.cos(2.0 * math.pi * target.weekday() / 7.0)
    mapping["num:saturday"] = float(target.weekday() == 5)
    mapping["num:month_end"] = float(target.day == 31)
    mapping["num:lag_quantity"] = (lag_quantity - quantity_center) / quantity_scale
    return np.asarray([mapping[name] for name in names], dtype=float)


def transformed(value: float, variable: str) -> float:
    return math.log1p(value) if variable == "quantity" else math.log(max(value, 1e-12))


def prediction_value(distribution: dict[str, float], variable: str) -> dict[str, float]:
    inverse = math.expm1 if variable == "quantity" else math.exp
    return {
        **distribution,
        "point_median": max(0.0, inverse(distribution["location"])),
        "lower_90_natural": max(0.0, inverse(distribution["lower_90"])),
        "upper_90_natural": max(0.0, inverse(distribution["upper_90"])),
    }


def price_gate(history: list[dict[str, Any]]) -> str:
    values = [round(float(item["price_eur_per_unit"]), 12) for item in history]
    return "SHADOW_IDENTIFIABLE_VARIATION" if len(values) >= 3 and len(set(values)) >= 2 else "DEGENERATE_METRIC_VETO"


def strong_baseline(row: dict[str, Any], history: dict[str, list[dict[str, Any]]], variable: str) -> float | None:
    by_product: list[float] = []
    by_origin: list[float] = []
    for records in history.values():
        if not records:
            continue
        last = records[-1]
        if last["product"] == row["product"]:
            by_product.append(value_of(last, variable))
        if last["origin_code"] == row["origin_code"]:
            by_origin.append(value_of(last, variable))
    values = by_product or by_origin
    return float(np.median(values)) if values else None


def local_verdict(model_error: float, baseline_error: float, tolerance: float = 1e-12) -> str:
    delta = model_error - baseline_error
    if delta < -tolerance:
        return "LOCAL_WIN"
    if delta > tolerance:
        return "LOCAL_LOSS"
    return "LOCAL_TIE"


def _score_value(actual: float, point: float, baseline: float, variable: str) -> tuple[float, float, str]:
    model_error = abs(transformed(actual, variable) - transformed(point, variable))
    baseline_error = abs(transformed(actual, variable) - transformed(baseline, variable))
    return model_error, baseline_error, local_verdict(model_error, baseline_error)


def _summarize(scores: list[dict[str, Any]], variable: str, baseline: str, regime: str | None = None) -> dict[str, Any]:
    eligible = [
        score[variable]
        for score in scores
        if (regime is None or score["regime"] == regime) and score[variable].get(f"{baseline}_error") is not None
    ]
    model_errors = [item["bma_error"] for item in eligible]
    baseline_errors = [item[f"{baseline}_error"] for item in eligible]
    verdict_key = f"bma_vs_{baseline}"
    return {
        "n": len(eligible),
        "bma_mean_absolute_transformed_error": float(np.mean(model_errors)) if eligible else None,
        f"{baseline}_mean_absolute_transformed_error": float(np.mean(baseline_errors)) if eligible else None,
        "local_wins": sum(item[verdict_key] == "LOCAL_WIN" for item in eligible),
        "local_losses": sum(item[verdict_key] == "LOCAL_LOSS" for item in eligible),
        "local_ties": sum(item[verdict_key] == "LOCAL_TIE" for item in eligible),
    }


def replay(source_roots: list[Path], output: Path, initial: dict[str, Any]) -> dict[str, Any]:
    origins = sorted({row["origin_code"] for row in initial["rows"]})
    products = sorted({row["product"] for row in initial["rows"]})
    names = feature_names(origins, products)
    quantity_logs = [math.log1p(float(row["unit_count"])) for row in initial["rows"]]
    price_logs = [math.log(max(float(row["price_eur_per_unit"]), 1e-12)) for row in initial["rows"]]
    quantity_center, quantity_scale = robust_center_scale(quantity_logs)
    price_center, price_scale = robust_center_scale(price_logs)
    ordinary = RegimeState(
        BayesianLinearState.prior(names, quantity_center, quantity_scale**2),
        BayesianLinearState.prior(names, price_center, price_scale**2),
        defaultdict(list),
        {},
    )

    def design(row: dict[str, Any], target: date, variable: str, state: RegimeState) -> np.ndarray:
        center, scale = (quantity_center, quantity_scale) if variable == "quantity" else (price_center, price_scale)
        return build_features(
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

    initial_quantity_x: list[np.ndarray] = []
    initial_price_x: list[np.ndarray] = []
    initial_quantity_y: list[float] = []
    initial_price_y: list[float] = []
    for row in initial["rows"]:
        initial_quantity_x.append(design(row, START, "quantity", ordinary))
        initial_price_x.append(design(row, START, "price", ordinary))
        initial_quantity_y.append(transformed(float(row["unit_count"]), "quantity"))
        initial_price_y.append(transformed(float(row["price_eur_per_unit"]), "price"))
        ordinary.known[row["cell_id"]] = row
    ordinary.quantity_model.update(np.vstack(initial_quantity_x), np.asarray(initial_quantity_y))
    ordinary.price_model.update(np.vstack(initial_price_x), np.asarray(initial_price_y))
    for row in initial["rows"]:
        ordinary.history[row["cell_id"]].append({**row, "date": START.isoformat()})

    origin_frozen_quantity = ordinary.quantity_model.clone()
    origin_frozen_quantity_sha256 = sha256_bytes(canonical_bytes(origin_frozen_quantity.serializable()))
    regime_states: dict[str, RegimeState] = {"ORDINARY": ordinary}
    sequence: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []
    zledger: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "win_vs_persistence": 0,
            "loss_vs_persistence": 0,
            "tie_vs_persistence": 0,
            "win_vs_origin_frozen": 0,
            "loss_vs_origin_frozen": 0,
            "tie_vs_origin_frozen": 0,
        }
    )
    day = date(2026, 7, 21)
    sequence_number = 0
    while day <= END:
        day_key = day.isoformat()
        regime = regime_for(day)
        if regime not in regime_states:
            regime_states[regime] = ordinary.fork()
        state = regime_states[regime]
        candidates = [state.known[key] for key in sorted(state.known)]
        if not candidates:
            raise GateFailure(f"no forecastable cells before {day_key}")
        quantity_x = np.vstack([design(row, day, "quantity", state) for row in candidates])
        price_x = np.vstack([design(row, day, "price", state) for row in candidates])
        quantity_predictions = state.quantity_model.predict(quantity_x)
        origin_predictions = origin_frozen_quantity.predict(quantity_x)
        price_predictions = state.price_model.predict(price_x)
        frozen_rows: list[dict[str, Any]] = []
        for row, qdist, odist, pdist, qx, px in zip(
            candidates, quantity_predictions, origin_predictions, price_predictions, quantity_x, price_x
        ):
            history = state.history[row["cell_id"]]
            last = history[-1]
            authority = (
                "SHADOW_UNCALIBRATED_REGIME"
                if regime != "ORDINARY"
                else ("SHADOW_COLD_START" if len(history) < 3 else "IN_SUPPORT_REPLAY_ONLY")
            )
            frozen_rows.append(
                {
                    "cell_id": row["cell_id"],
                    "product": row["product"],
                    "origin_code": row["origin_code"],
                    "origin_label": row["origin_label"],
                    "family": row["family"],
                    "authority_quantity": authority,
                    "authority_price": price_gate(history),
                    "quantity": prediction_value(qdist, "quantity"),
                    "price": prediction_value(pdist, "price"),
                    "baselines": {
                        "PERSISTENCE": {
                            "quantity": float(last["unit_count"]),
                            "price": float(last["price_eur_per_unit"]),
                        },
                        "BMA_ORIGIN_FROZEN": {
                            "quantity": prediction_value(odist, "quantity")["point_median"],
                            "parameter_state_sha256": origin_frozen_quantity_sha256,
                            "training_cut": START.isoformat(),
                            "feature_history_cut": (day.fromordinal(day.toordinal() - 1)).isoformat(),
                        },
                        "CROSS_SECTIONAL_LAG": {
                            "quantity": strong_baseline(row, state.history, "quantity"),
                            "price": strong_baseline(row, state.history, "price"),
                        },
                    },
                    "design_vector_quantity": qx.tolist(),
                    "design_vector_price": px.tolist(),
                    "history_count_before_target": len(history),
                    "last_observation_date": last["date"],
                }
            )
        prior_hash = sha256_bytes(
            canonical_bytes(
                {
                    "quantity": state.quantity_model.serializable(),
                    "price": state.price_model.serializable(),
                    "regime": regime,
                }
            )
        )
        freeze = {
            "schema_version": SCHEMA,
            "target_date": day_key,
            "regime": regime,
            "knowledge_cut": (day.fromordinal(day.toordinal() - 1)).isoformat(),
            "prior_state_sha256": prior_hash,
            "origin_frozen_parameter_state_sha256": origin_frozen_quantity_sha256,
            "predictions": frozen_rows,
            "status": "FROZEN_BEFORE_TARGET_STRUCTURED_SOURCE_OPENED",
            "claim_boundary": "retrospective development replay; not a live prospective freeze",
        }
        freeze_path = output / "freezes" / f"freeze_{day_key}.json"
        freeze_hash = write_json_new(freeze_path, freeze)
        sequence_number += 1
        sequence.append({"sequence": sequence_number, "event": "FREEZE_WRITTEN", "target_date": day_key, "sha256": freeze_hash})

        outcome, outcome_hash = compile_structured_day(source_roots, day, output)
        sequence_number += 1
        sequence.append(
            {
                "sequence": sequence_number,
                "event": "TARGET_STRUCTURED_SOURCE_OPENED_AND_COMPILED",
                "target_date": day_key,
                "sha256": outcome_hash,
                "after_freeze_sha256": freeze_hash,
            }
        )
        if outcome["publication_state"] == "PENDING_EMPTY_NOT_ZERO":
            adjudication = {
                "schema_version": SCHEMA,
                "target_date": day_key,
                "regime": regime,
                "freeze_sha256": freeze_hash,
                "outcome_sha256": outcome_hash,
                "status": "PENDING_EMPTY_NOT_ZERO",
                "economic_update_performed": False,
                "reason": "zero structured rows do not establish zero trade or publication completeness",
            }
            write_json_new(output / "adjudications" / f"adjudication_{day_key}.json", adjudication)
            daily.append({"date": day_key, "regime": regime, "status": adjudication["status"], "scored": 0})
            day = day.fromordinal(day.toordinal() + 1)
            continue

        frozen_by = {row["cell_id"]: row for row in frozen_rows}
        observed_by = {row["cell_id"]: row for row in outcome["rows"]}
        scores: list[dict[str, Any]] = []
        for cell_id in sorted(frozen_by.keys() & observed_by.keys()):
            prediction = frozen_by[cell_id]
            actual = observed_by[cell_id]
            record: dict[str, Any] = {
                "cell_id": cell_id,
                "product": actual["product"],
                "origin_code": actual["origin_code"],
                "regime": regime,
            }
            for variable, field in (("quantity", "unit_count"), ("price", "price_eur_per_unit")):
                actual_value = float(actual[field])
                point = float(prediction[variable]["point_median"])
                persistence = float(prediction["baselines"]["PERSISTENCE"][variable])
                model_error, persistence_error, persistence_verdict = _score_value(
                    actual_value, point, persistence, variable
                )
                strong = prediction["baselines"]["CROSS_SECTIONAL_LAG"][variable]
                if strong is None:
                    strong_error = None
                    strong_verdict = "NOT_ESTIMABLE"
                else:
                    _, strong_error, strong_verdict = _score_value(actual_value, point, float(strong), variable)
                item: dict[str, Any] = {
                    "actual": actual_value,
                    "bma_point": point,
                    "persistence": persistence,
                    "strong": strong,
                    "bma_error": model_error,
                    "persistence_error": persistence_error,
                    "strong_error": strong_error,
                    "bma_vs_persistence": persistence_verdict,
                    "bma_vs_strong": strong_verdict,
                    "covered_90": prediction[variable]["lower_90_natural"]
                    <= actual_value
                    <= prediction[variable]["upper_90_natural"],
                    "authority": prediction[f"authority_{variable}"],
                }
                if variable == "quantity":
                    origin_point = float(prediction["baselines"]["BMA_ORIGIN_FROZEN"]["quantity"])
                    _, origin_error, origin_verdict = _score_value(actual_value, point, origin_point, variable)
                    item.update(
                        {
                            "origin_frozen": origin_point,
                            "origin_frozen_error": origin_error,
                            "bma_vs_origin_frozen": origin_verdict,
                        }
                    )
                    ledger = zledger[cell_id]
                    for comparator, verdict in (
                        ("persistence", persistence_verdict),
                        ("origin_frozen", origin_verdict),
                    ):
                        prefix = {"LOCAL_WIN": "win", "LOCAL_LOSS": "loss", "LOCAL_TIE": "tie"}[verdict]
                        ledger[f"{prefix}_vs_{comparator}"] += 1
                record[variable] = item
            scores.append(record)

        adjudication = {
            "schema_version": SCHEMA,
            "target_date": day_key,
            "regime": regime,
            "freeze_sha256": freeze_hash,
            "outcome_sha256": outcome_hash,
            "status": "ADJUDICATED_STRUCTURED_OUTCOME",
            "scored_cells": len(scores),
            "unscored_first_appearance_cells": sorted(observed_by.keys() - frozen_by.keys()),
            "frozen_cells_without_positive_row": sorted(frozen_by.keys() - observed_by.keys()),
            "absence_semantics": "not scored as zero; no Bernoulli absence without a completeness witness",
            "participation_layer_status": "BLOCKED_NO_COMPLETENESS_WITNESS",
            "scores": scores,
        }
        adjudication_hash = write_json_new(
            output / "adjudications" / f"adjudication_{day_key}.json", adjudication
        )

        update_rows = outcome["rows"]
        quantity_update_x = np.vstack([design(row, day, "quantity", state) for row in update_rows])
        quantity_update_y = np.asarray(
            [transformed(float(row["unit_count"]), "quantity") for row in update_rows]
        )
        state.quantity_model.update(quantity_update_x, quantity_update_y)
        eligible_price_rows = [
            row for row in update_rows if price_gate(state.history.get(row["cell_id"], [])) == "SHADOW_IDENTIFIABLE_VARIATION"
        ]
        if eligible_price_rows:
            price_update_x = np.vstack([design(row, day, "price", state) for row in eligible_price_rows])
            price_update_y = np.asarray(
                [transformed(float(row["price_eur_per_unit"]), "price") for row in eligible_price_rows]
            )
            state.price_model.update(price_update_x, price_update_y)
        for row in update_rows:
            state.known[row["cell_id"]] = row
            state.history.setdefault(row["cell_id"], []).append({**row, "date": day_key})

        next_prior = {
            "schema_version": SCHEMA,
            "compiled_from_target": day_key,
            "regime_state_updated": regime,
            "ordinary_state_modified": regime == "ORDINARY",
            "adjudication_sha256": adjudication_hash,
            "knowledge_effect": "FUTURE_ONLY_WITHIN_REGIME",
            "quantity_model": state.quantity_model.serializable(),
            "price_model": state.price_model.serializable(),
            "price_rows_ingested_this_target": len(eligible_price_rows),
            "participation_layer_status": "BLOCKED_NO_COMPLETENESS_WITNESS",
            "evaluation_ledger_is_not_economic_posterior": True,
        }
        prior_hash = write_json_new(output / "priors" / f"prior_after_{day_key}_{regime}.json", next_prior)
        write_json_new(
            output / "z_post" / f"z_post_{day_key}.json",
            {
                "schema_version": SCHEMA,
                "target_date": day_key,
                "regime": regime,
                "adjudication_sha256": adjudication_hash,
                "economic_prior_sha256": prior_hash,
                "role": "evaluation_and_local_cartography_only",
                "local_quantity_ledger": {key: zledger[key] for key in sorted(zledger)},
                "global_winner": None,
            },
        )
        daily.append(
            {
                "date": day_key,
                "regime": regime,
                "status": adjudication["status"],
                "scored": len(scores),
                "new_cells": len(observed_by.keys() - frozen_by.keys()),
                "price_rows_ingested": len(eligible_price_rows),
            }
        )
        day = day.fromordinal(day.toordinal() + 1)

    all_scores: list[dict[str, Any]] = []
    for path in sorted((output / "adjudications").glob("adjudication_*.json")):
        all_scores.extend(json.loads(path.read_text(encoding="utf-8")).get("scores", []))
    regimes = ["ORDINARY", "SATURDAY_ACTIVE_UNCALIBRATED", "MONTH_END_PRE_AUGUST_UNCALIBRATED"]
    quantity_vs_origin = _summarize(all_scores, "quantity", "origin_frozen")
    summary = {
        "schema_version": SCHEMA,
        "status": "EXECUTED_RETROSPECTIVE_DEVELOPMENT_REPLAY",
        "initial_knowledge_date": START.isoformat(),
        "final_target_date": END.isoformat(),
        "daily": daily,
        "quantity_vs_persistence": _summarize(all_scores, "quantity", "persistence"),
        "quantity_vs_strong": _summarize(all_scores, "quantity", "strong"),
        "quantity_vs_origin_frozen": quantity_vs_origin,
        "quantity_vs_origin_frozen_by_regime": {
            regime: _summarize(all_scores, "quantity", "origin_frozen", regime) for regime in regimes
        },
        "adaptive_gain_vs_origin_frozen": (
            quantity_vs_origin["origin_frozen_mean_absolute_transformed_error"]
            - quantity_vs_origin["bma_mean_absolute_transformed_error"]
            if quantity_vs_origin["n"]
            else None
        ),
        "price_vs_persistence": _summarize(all_scores, "price", "persistence"),
        "price_degenerate_veto_fraction": (
            sum(score["price"]["authority"] == "DEGENERATE_METRIC_VETO" for score in all_scores) / len(all_scores)
            if all_scores
            else 1.0
        ),
        "regime_state_observations": {
            name: {
                "quantity": state.quantity_model.observations,
                "price": state.price_model.observations,
                "known_cells": len(state.known),
            }
            for name, state in regime_states.items()
        },
        "causal_ordering": {
            "status": "PASS_SEQUENCE_LEDGER",
            "freeze_precedes_target_open_for_every_target": True,
            "events": sequence,
        },
        "participation_layer": "BLOCKED_NO_COMPLETENESS_WITNESS",
        "corrections_from_v0_4": [
            "BMA_ORIGIN_FROZEN_PARAMETER_CONTROL",
            "TARGET_OPEN_AFTER_FREEZE",
            "REGIME_PARAMETER_AND_HISTORY_ISOLATION",
            "NO_PRICE_UPDATE_WHILE_CELL_HISTORY_IS_DEGENERATE",
            "EXACT_PRODUCT_EFFECTS_WITH_COLLISION_CHECK",
            "PARTICIPATION_BLOCKED_INSTEAD_OF_SIMULATED",
        ],
        "claim_boundary": {
            "prospective_evidence": False,
            "global_superiority": False,
            "commercial_validation": False,
            "canonical_product_promotion": "PENDING_INDEPENDENT_REVIEW",
            "quantity_result_role": "retrospective development evidence",
            "price_result_role": "diagnostic only where the published target is degenerate",
        },
    }
    write_json_new(output / "RESULT_SUMMARY.json", summary)
    write_json_new(
        output / "CAUSAL_SEQUENCE_LEDGER.json",
        {"schema_version": SCHEMA, "events": sequence, "status": "PASS_SEQUENCE_LEDGER"},
    )
    return summary


def run(source_roots: list[Path], output: Path) -> dict[str, Any]:
    if output.exists():
        raise GateFailure(f"immutable output already exists: {output}")
    output.mkdir(parents=True)
    initial, _ = compile_structured_day(source_roots, START, output)
    if initial["publication_state"] != "POSITIVE_ROWS":
        raise GateFailure("20 July must contain the initial structured market state")
    summary = replay(source_roots, output, initial)
    _, manifest_sha256 = write_manifest(output)
    return {**summary, "manifest_sha256": manifest_sha256, "output": str(output)}
