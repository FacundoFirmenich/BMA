"""Matched N:N monthly games over AEAT Chapter 72 data.

This is a bounded monthly-scale exploration, not the primary daily BMA model.
Every game trains on N consecutive months and adjudicates N consecutive target
months. Target months are added one at a time and can only reinform later months
inside the same game. No state or metric from invalid experiment v0.6.1 is read.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import numpy as np

from bma.connectors.aeat_trade import fetch_month
from bma.custody import write_json_new, write_manifest
from bma.experiments.aeat_steel_v0_6_1 import (
    CONTINUOUS_EXPERTS,
    PARTICIPATION_EXPERTS,
    _cell_maps,
    _continuous_context,
    _continuous_predictions,
    _log_loss,
    _metadata,
    _participation_context,
    _participation_predictions,
    _positive_value,
    _write_gzip_json_new,
    fit_continuous_weights,
    fit_participation_weights,
)

SCHEMA = "bma.aeat.chapter72.monthly-matched-games.v0.6.2"
YEAR = 2024
MONTHS = tuple(range(1, 13))
TRAINING_LENGTHS = (1, 2, 3, 4, 5, 6)


class GateFailure(RuntimeError):
    pass


def matched_games(months: tuple[int, ...], lengths: tuple[int, ...]) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for length in lengths:
        if length < 1:
            raise GateFailure("training length must be positive")
        for start in range(0, len(months) - 2 * length + 1):
            training = months[start : start + length]
            targets = months[start + length : start + 2 * length]
            if len(training) != len(targets):
                raise GateFailure("N:N block measure violated")
            games.append(
                {
                    "game_id": f"N{length:02d}_START{training[0]:02d}",
                    "n": length,
                    "training_months": list(training),
                    "target_months": list(targets),
                }
            )
    return games


def _forecast(history: list[dict[str, Any]], target_month: int, game_id: str) -> dict[str, Any]:
    maps = _cell_maps(history)
    metadata = _metadata(maps)
    participation_fit = fit_participation_weights(maps)
    participation_context = _participation_context(maps, metadata)
    continuous_fits = {
        metric: fit_continuous_weights(maps, metric)
        for metric in ("weight_kg", "statistical_unit_value_eur_per_kg")
    }
    continuous_contexts = {
        metric: _continuous_context(maps, metadata, metric)
        for metric in continuous_fits
    }
    participation: dict[str, Any] = {}
    continuous: dict[str, dict[str, Any]] = {metric: {} for metric in continuous_fits}
    for cell_id in sorted(metadata):
        experts = _participation_predictions(participation_context, metadata, cell_id)
        participation[cell_id] = {
            "experts": experts,
            "bma": sum(
                participation_fit["weights"][name] * experts[name]
                for name in PARTICIPATION_EXPERTS
            ),
        }
        for metric, context in continuous_contexts.items():
            predictions = _continuous_predictions(context, metadata, cell_id)
            if predictions is None:
                continue
            continuous[metric][cell_id] = {
                "experts": predictions,
                "bma": sum(
                    continuous_fits[metric]["weights"][name] * predictions[name]
                    for name in CONTINUOUS_EXPERTS
                ),
            }
    return {
        "schema_version": SCHEMA,
        "game_id": game_id,
        "target_month": target_month,
        "knowledge_months": [int(item["period"][-2:]) for item in history],
        "universe_cells": len(metadata),
        "participation_fit": participation_fit,
        "continuous_fits": continuous_fits,
        "metadata": metadata,
        "predictions": {"participation": participation, "continuous": continuous},
    }


def _average(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _score_participation(forecast: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    target_cells = {row["cell_id"] for row in target["cells"]}
    losses: dict[str, list[float]] = {name: [] for name in ("bma", *PARTICIPATION_EXPERTS)}
    log_losses: dict[str, list[float]] = {name: [] for name in losses}
    for cell_id, prediction in forecast["predictions"]["participation"].items():
        actual = int(cell_id in target_cells)
        probabilities = {"bma": prediction["bma"], **prediction["experts"]}
        for name, probability in probabilities.items():
            losses[name].append((actual - probability) ** 2)
            log_losses[name].append(_log_loss(actual, probability))
    return {
        "temporal_unit": "month",
        "n_cells": len(forecast["predictions"]["participation"]),
        "brier": {name: _average(values) for name, values in losses.items()},
        "log_loss": {name: _average(values) for name, values in log_losses.items()},
    }


def _score_continuous(
    forecast: dict[str, Any], target: dict[str, Any], metric: str
) -> dict[str, Any]:
    target_map = {row["cell_id"]: row for row in target["cells"]}
    losses: dict[str, list[float]] = {name: [] for name in ("bma", *CONTINUOUS_EXPERTS)}
    for cell_id, prediction in forecast["predictions"]["continuous"][metric].items():
        if cell_id not in target_map:
            continue
        actual_value = _positive_value(target_map[cell_id], metric)
        if actual_value is None:
            continue
        actual = math.log(actual_value)
        predictions = {"bma": prediction["bma"], **prediction["experts"]}
        for name, value in predictions.items():
            losses[name].append(abs(actual - value))
    return {
        "temporal_unit": "month",
        "n_cells": len(losses["bma"]),
        "mean_absolute_log_error": {
            name: _average(values) for name, values in losses.items()
        },
    }


def score_month(forecast: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_period": target["period"],
        "regime": "YEAR_END" if target["period"].endswith("-12") else "ORDINARY_UNCALIBRATED",
        "participation": _score_participation(forecast, target),
        "weight_kg": _score_continuous(forecast, target, "weight_kg"),
        "statistical_unit_value": _score_continuous(
            forecast, target, "statistical_unit_value_eur_per_kg"
        ),
        "Z_post": "TARGET_MONTH_ADDED_ONCE_TO_SAME_UNIT_HISTORY_FOR_LATER_MONTHS",
    }


def _game_summary(game: dict[str, Any]) -> dict[str, Any]:
    scores = game["monthly_scores"]

    def collect(section: str, metric: str, model: str) -> list[float]:
        values = [row[section][metric][model] for row in scores]
        return [float(value) for value in values if value is not None]

    return {
        "target_months_scored": len(scores),
        "participation_brier": {
            name: _average(collect("participation", "brier", name))
            for name in ("bma", *PARTICIPATION_EXPERTS)
        },
        "weight_kg_male": {
            name: _average(collect("weight_kg", "mean_absolute_log_error", name))
            for name in ("bma", *CONTINUOUS_EXPERTS)
        },
        "statistical_unit_value_male": {
            name: _average(
                collect("statistical_unit_value", "mean_absolute_log_error", name)
            )
            for name in ("bma", *CONTINUOUS_EXPERTS)
        },
        "inference": "DESCRIPTIVE_MONTH_UNITS_ONLY_NO_CROSS_SECTIONAL_PSEUDOREPLICATION",
    }


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise GateFailure(f"immutable output already exists: {output}")
    output.mkdir(parents=True)
    documents: dict[int, dict[str, Any]] = {}
    sequence: list[dict[str, Any]] = []
    for month in range(1, 12):
        document = fetch_month(YEAR, month)
        documents[month] = document
        sequence.append(
            {
                "sequence": len(sequence) + 1,
                "event": "MONTH_FETCHED_IN_MEMORY_AND_AGGREGATED",
                "period": document["period"],
                "archive_sha256": document["source"]["archive_sha256"],
                "raw_archive_persisted": False,
            }
        )

    games = matched_games(MONTHS, TRAINING_LENGTHS)
    states: dict[str, dict[str, Any]] = {}
    december_freezes: dict[str, Any] = {}
    for definition in games:
        game_id = definition["game_id"]
        history = [documents[month] for month in definition["training_months"]]
        state = {**definition, "monthly_scores": []}
        for target_month in definition["target_months"]:
            forecast = _forecast(history, target_month, game_id)
            if target_month == 12:
                december_freezes[game_id] = forecast
                break
            target = documents[target_month]
            state["monthly_scores"].append(score_month(forecast, target))
            history.append(target)
        state["history_before_december"] = [int(item["period"][-2:]) for item in history]
        states[game_id] = state

    freeze = {
        "schema_version": SCHEMA,
        "status": "FROZEN_BEFORE_DECEMBER_ARCHIVE_OPEN",
        "invalid_v061_state_reused": False,
        "same_block_measure": True,
        "december_predictions": december_freezes,
    }
    freeze_sha256 = _write_gzip_json_new(output / "DECEMBER_PREDICTION_FREEZE.json.gz", freeze)
    sequence.append(
        {
            "sequence": len(sequence) + 1,
            "event": "ALL_DECEMBER_GAME_PREDICTIONS_FROZEN",
            "sha256": freeze_sha256,
        }
    )

    december = fetch_month(YEAR, 12)
    documents[12] = december
    sequence.append(
        {
            "sequence": len(sequence) + 1,
            "event": "DECEMBER_ARCHIVE_OPENED_AFTER_FREEZE",
            "period": december["period"],
            "archive_sha256": december["source"]["archive_sha256"],
            "after_freeze_sha256": freeze_sha256,
            "raw_archive_persisted": False,
        }
    )
    for game_id, forecast in december_freezes.items():
        states[game_id]["monthly_scores"].append(score_month(forecast, december))

    completed_games = []
    for definition in games:
        state = states[definition["game_id"]]
        if len(state["monthly_scores"]) != definition["n"]:
            raise GateFailure(f"incomplete N:N game {definition['game_id']}")
        state["summary"] = _game_summary(state)
        state["same_block_measure"] = True
        completed_games.append(state)

    aggregate_sha256 = _write_gzip_json_new(
        output / "MONTHLY_AGGREGATES_2024.json.gz",
        [documents[month] for month in MONTHS],
    )
    result = {
        "schema_version": SCHEMA,
        "status": "EXECUTED_MATCHED_MONTHLY_EXPLORATION",
        "year": YEAR,
        "game_count": len(completed_games),
        "training_lengths": list(TRAINING_LENGTHS),
        "games": completed_games,
        "causal_boundary": {
            "january_to_november": "RETROSPECTIVE_ALREADY_OPENED_DEVELOPMENT_DATA",
            "december": "PREDICTIONS_FROZEN_BEFORE_ARCHIVE_OPEN",
            "december_freeze_sha256": freeze_sha256,
        },
        "information_contract": {
            "invalid_v061_metrics_weights_posteriors_reused": False,
            "same_atomic_unit": "month",
            "same_block_measure": "N training months x N target months",
            "Z_post": "each target month added once and only after its score",
            "cross_section_used_as_temporal_sample_size": False,
        },
        "raw_storage": {
            "source_zip_persisted": False,
            "one_archive_in_memory_at_a_time": True,
            "normalized_aggregates_sha256": aggregate_sha256,
        },
        "claim_boundary": {
            "primary_daily_model_evidence": False,
            "monthly_scale_exploration_only": True,
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
    print(
        f"status={result['status']} games={result['game_count']} "
        f"december_freeze={result['causal_boundary']['december_freeze_sha256']}"
    )


if __name__ == "__main__":
    main()
