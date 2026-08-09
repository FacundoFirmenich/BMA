"""Frozen November-2024 holdout for AEAT chapter-72 physical trade.

January--October 2024 are fetched and fitted first. The complete prediction
freeze is written and hashed before the November URL is opened. Source ZIPs are
held one at a time in RAM and are never persisted by the connector.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import random
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

from bma.connectors.aeat_trade import fetch_month
from bma.custody import canonical_bytes, sha256_bytes, write_json_new, write_manifest

SCHEMA = "bma.aeat.chapter72.november-holdout.v0.6.1"
YEAR = 2024
TRAIN_MONTHS = tuple(range(1, 11))
TARGET_MONTH = 11
PARTICIPATION_EXPERTS = ("persistence", "empirical", "hierarchical", "recency")
CONTINUOUS_EXPERTS = ("persistence", "cell_center", "hierarchical", "recency")
PARTICIPATION_MIN_N = 1_000
CONTINUOUS_MIN_N = 250
BOOTSTRAP_REPLICATES = 2_000
BOOTSTRAP_SEED = 20240809


class GateFailure(RuntimeError):
    pass


def _write_gzip_json_new(path: Path, value: Any) -> str:
    if path.exists():
        raise GateFailure(f"immutable artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = gzip.compress(canonical_bytes(value), compresslevel=9, mtime=0)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def _softmax(log_weights: dict[str, float]) -> dict[str, float]:
    high = max(log_weights.values())
    raw = {name: math.exp(value - high) for name, value in log_weights.items()}
    total = sum(raw.values())
    return {name: raw[name] / total for name in raw}


def _cell_maps(documents: list[dict[str, Any]]) -> list[dict[str, dict[str, Any]]]:
    return [{row["cell_id"]: row for row in document["cells"]} for document in documents]


def _metadata(maps: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for month in maps:
        for cell_id, row in month.items():
            result.setdefault(
                cell_id,
                {
                    "flow": row["flow"],
                    "cn8": row["cn8"],
                    "cn4": row["cn4"],
                    "partner_country": row["partner_country"],
                },
            )
    return result


def _participation_context(
    history: list[dict[str, dict[str, Any]]], metadata: dict[str, dict[str, str]]
) -> dict[str, Any]:
    n = len(history)
    outcomes = {cell_id: [int(cell_id in month) for month in history] for cell_id in metadata}
    group_cells: dict[str, dict[tuple[str, ...], int]] = {
        "flow": defaultdict(int),
        "product_flow": defaultdict(int),
        "partner_flow": defaultdict(int),
    }
    group_successes: dict[str, dict[tuple[str, ...], int]] = {
        "flow": defaultdict(int),
        "product_flow": defaultdict(int),
        "partner_flow": defaultdict(int),
    }
    for cell_id, item in metadata.items():
        keys = {
            "flow": (item["flow"],),
            "product_flow": (item["flow"], item["cn8"]),
            "partner_flow": (item["flow"], item["partner_country"]),
        }
        successes = sum(outcomes[cell_id])
        for layer, key in keys.items():
            group_cells[layer][key] += 1
            group_successes[layer][key] += successes
    return {"n": n, "outcomes": outcomes, "group_cells": group_cells, "group_successes": group_successes}


def _participation_predictions(context: dict[str, Any], metadata: dict[str, dict[str, str]], cell_id: str) -> dict[str, float]:
    outcomes = context["outcomes"][cell_id]
    n = context["n"]
    successes = sum(outcomes)
    item = metadata[cell_id]

    def rate(layer: str, key: tuple[str, ...]) -> float:
        trials = n * context["group_cells"][layer][key]
        observed = context["group_successes"][layer][key]
        return (observed + 1.0) / (trials + 2.0)

    flow_rate = rate("flow", (item["flow"],))
    product_flow = rate("product_flow", (item["flow"], item["cn8"]))
    partner_flow = rate("partner_flow", (item["flow"], item["partner_country"]))
    prior_mean = (flow_rate + product_flow + partner_flow) / 3.0
    hierarchical = (successes + 6.0 * prior_mean) / (n + 6.0)
    recency_weights = [0.85 ** (n - 1 - index) for index in range(n)]
    recency = (1.0 + sum(weight * outcome for weight, outcome in zip(recency_weights, outcomes))) / (
        2.0 + sum(recency_weights)
    )
    return {
        "persistence": 0.9 if outcomes[-1] else 0.1,
        "empirical": (successes + 1.0) / (n + 2.0),
        "hierarchical": hierarchical,
        "recency": recency,
    }


def fit_participation_weights(maps: list[dict[str, dict[str, Any]]]) -> dict[str, Any]:
    fold_scores: dict[str, list[float]] = {name: [] for name in PARTICIPATION_EXPERTS}
    fold_counts: list[int] = []
    for target_index in range(3, len(maps)):
        history = maps[:target_index]
        metadata = _metadata(history)
        context = _participation_context(history, metadata)
        target = maps[target_index]
        fold_counts.append(len(metadata))
        sums = dict.fromkeys(PARTICIPATION_EXPERTS, 0.0)
        for cell_id in sorted(metadata):
            actual = int(cell_id in target)
            predictions = _participation_predictions(context, metadata, cell_id)
            for name, probability in predictions.items():
                probability = min(max(probability, 1e-12), 1.0 - 1e-12)
                sums[name] += math.log(probability if actual else 1.0 - probability)
        for name in PARTICIPATION_EXPERTS:
            fold_scores[name].append(sums[name] / max(len(metadata), 1))
    log_weights = {name: math.log(1.0 / len(PARTICIPATION_EXPERTS)) + sum(fold_scores[name]) for name in PARTICIPATION_EXPERTS}
    return {
        "weights": _softmax(log_weights),
        "log_weights": log_weights,
        "fold_mean_log_likelihood": fold_scores,
        "fold_cell_counts": fold_counts,
        "likelihood_tempering": "ONE_MEAN_LOG_LIKELIHOOD_CONTRIBUTION_PER_MONTH",
    }


def _positive_value(row: dict[str, Any], metric: str) -> float | None:
    value = row.get(metric)
    return float(value) if value is not None and float(value) > 0 else None


def _continuous_context(
    history: list[dict[str, dict[str, Any]]], metadata: dict[str, dict[str, str]], metric: str
) -> dict[str, Any]:
    cell_values: dict[str, list[float]] = defaultdict(list)
    product_flow: dict[tuple[str, str], list[float]] = defaultdict(list)
    partner_flow: dict[tuple[str, str], list[float]] = defaultdict(list)
    flow: dict[str, list[float]] = defaultdict(list)
    for month in history:
        for cell_id, row in month.items():
            if cell_id not in metadata:
                continue
            value = _positive_value(row, metric)
            if value is None:
                continue
            logged = math.log(value)
            item = metadata[cell_id]
            cell_values[cell_id].append(logged)
            product_flow[(item["flow"], item["cn8"])].append(logged)
            partner_flow[(item["flow"], item["partner_country"])].append(logged)
            flow[item["flow"]].append(logged)
    return {
        "cell_values": cell_values,
        "product_flow_center": {key: median(values) for key, values in product_flow.items()},
        "partner_flow_center": {key: median(values) for key, values in partner_flow.items()},
        "flow_center": {key: median(values) for key, values in flow.items()},
    }


def _continuous_predictions(
    context: dict[str, Any], metadata: dict[str, dict[str, str]], cell_id: str
) -> dict[str, float] | None:
    cell_values = context["cell_values"].get(cell_id, [])
    if not cell_values:
        return None
    item = metadata[cell_id]
    prior_components = [
        context["product_flow_center"][(item["flow"], item["cn8"])],
        context["partner_flow_center"][(item["flow"], item["partner_country"])],
        context["flow_center"][item["flow"]],
    ]
    prior_center = sum(prior_components) / len(prior_components)
    cell_center = sum(cell_values) / len(cell_values)
    hierarchical = (len(cell_values) * cell_center + 4.0 * prior_center) / (len(cell_values) + 4.0)
    weights = [0.85 ** (len(cell_values) - 1 - index) for index in range(len(cell_values))]
    recency = sum(weight * value for weight, value in zip(weights, cell_values)) / sum(weights)
    return {
        "persistence": cell_values[-1],
        "cell_center": cell_center,
        "hierarchical": hierarchical,
        "recency": recency,
    }


def fit_continuous_weights(maps: list[dict[str, dict[str, Any]]], metric: str) -> dict[str, Any]:
    residuals: dict[str, list[list[float]]] = {name: [] for name in CONTINUOUS_EXPERTS}
    fold_counts: list[int] = []
    for target_index in range(3, len(maps)):
        history = maps[:target_index]
        metadata = _metadata(history)
        context = _continuous_context(history, metadata, metric)
        target = maps[target_index]
        by_expert: dict[str, list[float]] = {name: [] for name in CONTINUOUS_EXPERTS}
        for cell_id in sorted(set(metadata) & set(target)):
            actual_value = _positive_value(target[cell_id], metric)
            predictions = _continuous_predictions(context, metadata, cell_id)
            if actual_value is None or predictions is None:
                continue
            actual = math.log(actual_value)
            for name, prediction in predictions.items():
                by_expert[name].append(actual - prediction)
        count = len(by_expert[CONTINUOUS_EXPERTS[0]])
        fold_counts.append(count)
        for name in CONTINUOUS_EXPERTS:
            residuals[name].append(by_expert[name])
    pooled_absolute = [abs(value) for name in CONTINUOUS_EXPERTS for fold in residuals[name] for value in fold]
    scale = max(median(pooled_absolute) / 0.6744897501960817 if pooled_absolute else 0.0, 0.1)
    fold_log_likelihood: dict[str, list[float]] = {name: [] for name in CONTINUOUS_EXPERTS}
    for name in CONTINUOUS_EXPERTS:
        for fold in residuals[name]:
            fold_log_likelihood[name].append(
                sum(-0.5 * (value / scale) ** 2 - math.log(scale) for value in fold) / max(len(fold), 1)
            )
    log_weights = {name: math.log(1.0 / len(CONTINUOUS_EXPERTS)) + sum(fold_log_likelihood[name]) for name in CONTINUOUS_EXPERTS}
    return {
        "weights": _softmax(log_weights),
        "log_weights": log_weights,
        "common_log_residual_scale": scale,
        "fold_mean_log_likelihood": fold_log_likelihood,
        "fold_observation_counts": fold_counts,
        "likelihood_tempering": "ONE_MEAN_LOG_LIKELIHOOD_CONTRIBUTION_PER_MONTH",
    }


def _brier(actual: int, probability: float) -> float:
    return (actual - probability) ** 2


def _log_loss(actual: int, probability: float) -> float:
    bounded = min(max(probability, 1e-12), 1.0 - 1e-12)
    return -math.log(bounded if actual else 1.0 - bounded)


def _cluster_bootstrap(records: list[dict[str, Any]], difference_field: str) -> dict[str, Any]:
    by_cluster: dict[str, list[float]] = defaultdict(list)
    for row in records:
        by_cluster[row["cn4"]].append(float(row[difference_field]))
    keys = sorted(by_cluster)
    observed = float(np.mean([value for values in by_cluster.values() for value in values])) if keys else None
    if len(keys) < 2:
        return {"clusters": len(keys), "replicates": 0, "mean_difference": observed, "ci95": None}
    cluster_stats = {key: (sum(values), len(values)) for key, values in by_cluster.items()}
    rng = random.Random(BOOTSTRAP_SEED)
    samples: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATES):
        selected = [keys[rng.randrange(len(keys))] for _ in keys]
        numerator = sum(cluster_stats[key][0] for key in selected)
        denominator = sum(cluster_stats[key][1] for key in selected)
        samples.append(numerator / denominator)
    samples.sort()
    lower = samples[int(0.025 * len(samples))]
    upper = samples[int(0.975 * len(samples))]
    return {
        "clusters": len(keys),
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": BOOTSTRAP_SEED,
        "mean_difference": observed,
        "ci95": [lower, upper],
        "probability_difference_below_zero": sum(value < 0 for value in samples) / len(samples),
        "interpretation": "negative favours BMA; CN4 cluster bootstrap is descriptive, not an independence proof",
    }


def _mean(records: list[dict[str, Any]], field: str) -> float | None:
    return float(np.mean([row[field] for row in records])) if records else None


def _participation_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"n": len(records), "positives": sum(row["actual"] for row in records)}
    for name in ("bma", *PARTICIPATION_EXPERTS):
        result[name] = {
            "mean_brier": _mean(records, f"{name}_brier"),
            "mean_log_loss": _mean(records, f"{name}_log_loss"),
        }
    for comparator in PARTICIPATION_EXPERTS:
        result[f"bma_minus_{comparator}_brier"] = _mean(records, f"bma_minus_{comparator}_brier")
        result[f"bootstrap_vs_{comparator}"] = _cluster_bootstrap(records, f"bma_minus_{comparator}_brier")
    if len(records) < PARTICIPATION_MIN_N:
        result["gate"] = "NOT_ESTIMABLE_INSUFFICIENT_SUPPORT"
    elif all(result[f"bma_minus_{name}_brier"] < 0 for name in ("persistence", "empirical")):
        result["gate"] = "FAVOURABLE_DESCRIPTIVE_ONLY"
    elif any(result[f"bma_minus_{name}_brier"] > 0 for name in ("persistence", "empirical")):
        result["gate"] = "MIXED_OR_ADVERSE_DESCRIPTIVE_ONLY"
    else:
        result["gate"] = "LOCAL_TIE_DESCRIPTIVE_ONLY"
    return result


def _continuous_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"n": len(records)}
    for name in ("bma", *CONTINUOUS_EXPERTS):
        result[name] = {"mean_absolute_log_error": _mean(records, f"{name}_absolute_log_error")}
    for comparator in CONTINUOUS_EXPERTS:
        result[f"bma_minus_{comparator}_error"] = _mean(records, f"bma_minus_{comparator}_error")
        result[f"bootstrap_vs_{comparator}"] = _cluster_bootstrap(records, f"bma_minus_{comparator}_error")
    if len(records) < CONTINUOUS_MIN_N:
        result["gate"] = "NOT_ESTIMABLE_INSUFFICIENT_SUPPORT"
    elif all(result[f"bma_minus_{name}_error"] < 0 for name in ("persistence", "cell_center")):
        result["gate"] = "FAVOURABLE_DESCRIPTIVE_ONLY"
    elif any(result[f"bma_minus_{name}_error"] > 0 for name in ("persistence", "cell_center")):
        result["gate"] = "MIXED_OR_ADVERSE_DESCRIPTIVE_ONLY"
    else:
        result["gate"] = "LOCAL_TIE_DESCRIPTIVE_ONLY"
    return result


def _stratify(records: list[dict[str, Any]], summarizer: Callable[[list[dict[str, Any]]], dict[str, Any]]) -> dict[str, Any]:
    by_flow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_cn4: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_flow[row["flow"]].append(row)
        by_cn4[row["cn4"]].append(row)
    return {
        "by_flow": {key: summarizer(by_flow[key]) for key in sorted(by_flow)},
        "by_cn4": {key: summarizer(by_cn4[key]) for key in sorted(by_cn4) if len(by_cn4[key]) >= 20},
    }


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise GateFailure(f"immutable output already exists: {output}")
    output.mkdir(parents=True)
    sequence: list[dict[str, Any]] = []

    training: list[dict[str, Any]] = []
    for month in TRAIN_MONTHS:
        document = fetch_month(YEAR, month)
        training.append(document)
        sequence.append(
            {
                "sequence": len(sequence) + 1,
                "event": "TRAINING_MONTH_FETCHED_IN_MEMORY_AND_AGGREGATED",
                "period": document["period"],
                "archive_sha256": document["source"]["archive_sha256"],
                "raw_archive_persisted": False,
            }
        )
    training_hash = _write_gzip_json_new(output / "TRAINING_AGGREGATES.json.gz", training)
    maps = _cell_maps(training)
    metadata = _metadata(maps)
    participation_fit = fit_participation_weights(maps)
    quantity_fit = fit_continuous_weights(maps, "weight_kg")
    unit_value_fit = fit_continuous_weights(maps, "statistical_unit_value_eur_per_kg")
    participation_context = _participation_context(maps, metadata)
    quantity_context = _continuous_context(maps, metadata, "weight_kg")
    unit_value_context = _continuous_context(maps, metadata, "statistical_unit_value_eur_per_kg")

    participation_freeze: dict[str, Any] = {}
    quantity_freeze: dict[str, Any] = {}
    unit_value_freeze: dict[str, Any] = {}
    for cell_id in sorted(metadata):
        experts = _participation_predictions(participation_context, metadata, cell_id)
        participation_freeze[cell_id] = {
            **metadata[cell_id],
            "experts": experts,
            "bma_probability": sum(participation_fit["weights"][name] * experts[name] for name in PARTICIPATION_EXPERTS),
        }
        for context, fit, target in (
            (quantity_context, quantity_fit, quantity_freeze),
            (unit_value_context, unit_value_fit, unit_value_freeze),
        ):
            experts_continuous = _continuous_predictions(context, metadata, cell_id)
            if experts_continuous is None:
                continue
            bma_log = sum(fit["weights"][name] * experts_continuous[name] for name in CONTINUOUS_EXPERTS)
            target[cell_id] = {
                **metadata[cell_id],
                "experts_log_scale": experts_continuous,
                "bma_log_prediction": bma_log,
                "bma_point": math.exp(bma_log),
            }

    freeze = {
        "schema_version": SCHEMA,
        "status": "FROZEN_BEFORE_NOVEMBER_ARCHIVE_OPENED",
        "training_period": ["2024-01", "2024-10"],
        "target_period": "2024-11",
        "source_finality": "AEAT_2024_DATOS_DEFINITIVOS",
        "training_aggregates_sha256": training_hash,
        "universe_cells": len(metadata),
        "participation_fit": participation_fit,
        "quantity_fit": quantity_fit,
        "statistical_unit_value_fit": unit_value_fit,
        "predictions": {
            "participation": participation_freeze,
            "weight_kg_conditional_on_presence": quantity_freeze,
            "statistical_unit_value_eur_per_kg_conditional_on_positive_weight_and_value": unit_value_freeze,
        },
        "semantics": {
            "statistical_unit_value": "aggregate statistical value divided by net mass; not an auction, spot or firm price",
            "supplementary_units": "retained in aggregates but not modeled because units are commodity-specific",
        },
    }
    freeze_hash = _write_gzip_json_new(output / "TARGET_PREDICTION_FREEZE.json.gz", freeze)
    sequence.append(
        {
            "sequence": len(sequence) + 1,
            "event": "TARGET_PREDICTION_FREEZE_WRITTEN",
            "target_period": "2024-11",
            "sha256": freeze_hash,
        }
    )

    target = fetch_month(YEAR, TARGET_MONTH)
    target_hash = _write_gzip_json_new(output / "TARGET_AGGREGATES.json.gz", target)
    sequence.append(
        {
            "sequence": len(sequence) + 1,
            "event": "TARGET_ARCHIVE_OPENED_IN_MEMORY_AFTER_FREEZE",
            "target_period": target["period"],
            "archive_sha256": target["source"]["archive_sha256"],
            "aggregate_sha256": target_hash,
            "after_freeze_sha256": freeze_hash,
            "raw_archive_persisted": False,
        }
    )
    target_map = {row["cell_id"]: row for row in target["cells"]}

    participation_scores: list[dict[str, Any]] = []
    for cell_id, prediction in participation_freeze.items():
        actual = int(cell_id in target_map)
        row = {**metadata[cell_id], "cell_id": cell_id, "actual": actual}
        probabilities = {"bma": prediction["bma_probability"], **prediction["experts"]}
        for name, probability in probabilities.items():
            row[f"{name}_probability"] = probability
            row[f"{name}_brier"] = _brier(actual, probability)
            row[f"{name}_log_loss"] = _log_loss(actual, probability)
        for comparator in PARTICIPATION_EXPERTS:
            row[f"bma_minus_{comparator}_brier"] = row["bma_brier"] - row[f"{comparator}_brier"]
        participation_scores.append(row)

    def score_continuous(frozen: dict[str, Any], metric: str) -> list[dict[str, Any]]:
        scores: list[dict[str, Any]] = []
        for cell_id in sorted(set(frozen) & set(target_map)):
            actual_value = _positive_value(target_map[cell_id], metric)
            if actual_value is None:
                continue
            actual_log = math.log(actual_value)
            prediction = frozen[cell_id]
            row = {**metadata[cell_id], "cell_id": cell_id, "actual": actual_value}
            values = {"bma": prediction["bma_log_prediction"], **prediction["experts_log_scale"]}
            for name, predicted_log in values.items():
                row[f"{name}_prediction"] = math.exp(predicted_log)
                row[f"{name}_absolute_log_error"] = abs(actual_log - predicted_log)
            for comparator in CONTINUOUS_EXPERTS:
                row[f"bma_minus_{comparator}_error"] = (
                    row["bma_absolute_log_error"] - row[f"{comparator}_absolute_log_error"]
                )
            scores.append(row)
        return scores

    quantity_scores = score_continuous(quantity_freeze, "weight_kg")
    unit_value_scores = score_continuous(unit_value_freeze, "statistical_unit_value_eur_per_kg")
    new_cells = sorted(set(target_map) - set(metadata))
    participation_summary = _participation_summary(participation_scores)
    quantity_summary = _continuous_summary(quantity_scores)
    unit_value_summary = _continuous_summary(unit_value_scores)

    summary = {
        "schema_version": SCHEMA,
        "status": "EXECUTED_RETROSPECTIVE_INDUSTRIAL_HOLDOUT",
        "training_period": ["2024-01", "2024-10"],
        "target_period": "2024-11",
        "source_finality": "AEAT_2024_DATOS_DEFINITIVOS",
        "scope": "all chapter-72 iron-and-steel maximum-detail records aggregated by flow x CN8 x partner",
        "training": {
            "months": len(training),
            "raw_lines": sum(item["source"]["total_lines"] for item in training),
            "chapter72_lines": sum(item["source"]["chapter72_lines"] for item in training),
            "monthly_aggregate_rows": sum(len(item["cells"]) for item in training),
            "universe_cells": len(metadata),
            "archive_sha256": [item["source"]["archive_sha256"] for item in training],
        },
        "target": {
            "raw_lines": target["source"]["total_lines"],
            "chapter72_lines": target["source"]["chapter72_lines"],
            "aggregate_rows": len(target["cells"]),
            "known_cells": len(set(target_map) & set(metadata)),
            "new_out_of_training_universe": len(new_cells),
            "archive_sha256": target["source"]["archive_sha256"],
        },
        "participation": participation_summary,
        "weight_kg_conditional_on_presence": quantity_summary,
        "statistical_unit_value_eur_per_kg": unit_value_summary,
        "subgroups": {
            "participation": _stratify(participation_scores, _participation_summary),
            "weight_kg": _stratify(quantity_scores, _continuous_summary),
            "statistical_unit_value": _stratify(unit_value_scores, _continuous_summary),
        },
        "causal_ordering": {
            "status": "PASS_FREEZE_PRECEDES_TARGET_OPEN",
            "target_prediction_freeze_sha256": freeze_hash,
            "events": sequence,
        },
        "raw_storage": {
            "source_zip_persisted_locally": False,
            "source_zip_persisted_in_artifact": False,
            "one_archive_in_memory_at_a_time": True,
        },
        "claim_boundary": {
            "prospective_validation": False,
            "single_retrospective_holdout": True,
            "industrial_domain_extension": True,
            "transaction_price_validation": False,
            "global_superiority": False,
            "promotion": "NO_PROMOTION_SINGLE_RETROSPECTIVE_MONTH",
        },
    }
    _write_gzip_json_new(output / "PARTICIPATION_SCORES.json.gz", participation_scores)
    _write_gzip_json_new(output / "WEIGHT_SCORES.json.gz", quantity_scores)
    _write_gzip_json_new(output / "UNIT_VALUE_SCORES.json.gz", unit_value_scores)
    write_json_new(output / "CAUSAL_SEQUENCE_LEDGER.json", {"schema_version": SCHEMA, "events": sequence})
    write_json_new(output / "RESULT_SUMMARY.json", summary)
    write_json_new(output / "NEW_TARGET_CELLS.json", {"schema_version": SCHEMA, "cell_ids": new_cells})
    _, manifest_hash = write_manifest(output)
    return {**summary, "manifest_sha256": manifest_hash, "output": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print("BMA_RESULT_SUMMARY=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
