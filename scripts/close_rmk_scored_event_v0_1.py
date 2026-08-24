"""Adjudicate a causally frozen RMK event with exact-cell point predictions."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rmk_timber_model_v0_1 import LocalOutcomeState, canonical_phase  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def months(period: str) -> list[int]:
    start_text, end_text = (part.strip() for part in period.split("-"))
    start, end = datetime.strptime(start_text, "%d.%m.%Y"), datetime.strptime(end_text, "%d.%m.%Y")
    year, month = start.year, start.month
    result: set[int] = set()
    while (year, month) <= (end.year, end.month):
        result.add(month)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return sorted(result)


def identifier(descriptor: dict) -> str:
    raw = json.dumps(descriptor, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def phase_state(cell_outcome: dict) -> dict:
    count = len(cell_outcome["observations"])
    phase_counts: dict[str, int] = {}
    for phase in cell_outcome["phases"]:
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
    innovation_counts: dict[str, int] = {}
    for phase, _value in cell_outcome["m1_innovations"]:
        innovation_counts[phase] = innovation_counts.get(phase, 0) + 1
    estimable_phases = sorted(phase for phase, support in innovation_counts.items() if support >= 2)
    return {
        "M0": {"point_support": count, "transition_support": max(0, count - 1), "density_state": "ESTIMABLE" if count >= 4 else "NOT_ESTIMABLE_M0_DENSITY_SUPPORT"},
        "M1": {"observation_support": count, "required": 3, "state": "ESTIMABLE" if count >= 3 else "NOT_ESTIMABLE_M1_SUPPORT"},
        "M2": {
            "same_phase_observation_counts": phase_counts,
            "same_phase_innovation_counts": innovation_counts,
            "required": 2,
            "estimable_phases": estimable_phases,
            "state": "ESTIMABLE_FOR_LISTED_PHASES" if estimable_phases else "NOT_ESTIMABLE_SEASONAL_SUPPORT",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-date", required=True)
    parser.add_argument("--prior", required=True, type=Path)
    parser.add_argument("--raw-result-name", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    event = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events" / args.event_date
    prior_path = args.prior if args.prior.is_absolute() else ROOT / args.prior
    offer_path = event / "structured/offer_structured.json"
    result_path = event / "structured/result.json"
    freeze_path = event / "freeze/freeze.json"
    raw_result_path = event / "raw" / args.raw_result_name
    offer, result, freeze, prior = load(offer_path), load(result_path), load(freeze_path), load(prior_path)

    if freeze["event_date"] != args.event_date or result["event_date"] != args.event_date:
        raise ValueError("event date mismatch")
    if freeze["inputs_sha256"]["prior"] != digest(prior_path):
        raise ValueError("prior hash mismatch")
    if freeze["inputs_sha256"]["structured_offer"] != digest(offer_path):
        raise ValueError("offer hash mismatch")
    if result["source_sha256"] != digest(raw_result_path):
        raise ValueError("raw result hash mismatch")
    if result["structured_offer_used_sha256"] != digest(offer_path):
        raise ValueError("result offer link mismatch")
    if result["extraction_failures"]:
        raise ValueError("result extraction failures")

    outcomes_by_target = {(item["object_id"], item["destination"]): item for item in result["local_outcomes"]}
    object_totals = {item["object_id"]: item for item in result["object_totals"]}
    local_scores = []
    non_observed = []
    for frozen_object in freeze["objects"]:
        for prediction in frozen_object["frozen_local_predictions"]:
            key = (frozen_object["object_id"], prediction["destination"])
            outcome = outcomes_by_target.get(key)
            if outcome is None:
                object_total = object_totals[frozen_object["object_id"]]
                state = "UNAWARDED_OBJECT_NO_POSITIVE_OUTCOME" if object_total["awarded_volume_m3"] == 0 else "NOT_OBSERVED_EXACT_DESTINATION_OUTCOME"
                non_observed.append({
                    "object_id": frozen_object["object_id"],
                    "product": frozen_object["product"],
                    "destination": prediction["destination"],
                    "state": state,
                })
                continue
            predicted_price = float(prediction["price"]["M0"])
            predicted_volume = float(prediction["volume"]["M0"])
            actual_price = float(outcome["effective_weighted_price_eur_m3"])
            actual_volume = float(outcome["awarded_volume_m3"])
            local_scores.append({
                "object_id": frozen_object["object_id"],
                "product": frozen_object["product"],
                "destination": prediction["destination"],
                "phase": frozen_object["calendar_phase"],
                "price": {
                    "M0_point_prediction_eur_m3": predicted_price,
                    "actual_eur_m3": actual_price,
                    "absolute_error_eur_m3": abs(actual_price - predicted_price),
                    "M0_density_state": "NOT_ESTIMABLE_M0_DENSITY_SUPPORT",
                    "M1_state": prediction["price"]["M1"],
                    "M2_state": prediction["price"]["M2"],
                    "BMA_state": prediction["price"]["BMA"],
                },
                "volume": {
                    "M0_point_prediction_m3": predicted_volume,
                    "actual_m3": actual_volume,
                    "absolute_log_error": abs(math.log(actual_volume) - math.log(predicted_volume)),
                    "M0_density_state": "NOT_ESTIMABLE_M0_DENSITY_SUPPORT",
                    "M1_state": prediction["volume"]["M1"],
                    "M2_state": prediction["volume"]["M2"],
                    "BMA_state": prediction["volume"]["BMA"],
                },
            })

    cells = json.loads(json.dumps(prior["local_cells"]))
    updated_cells = 0
    new_cells = 0
    for outcome in result["local_outcomes"]:
        descriptor = {
            "product": outcome["product"],
            "measurement_fingerprint_sha256": outcome["measurement_fingerprint_sha256"],
            "destination": outcome["destination"],
        }
        cell_id = identifier(descriptor)
        phase = canonical_phase(months(outcome["delivery_period"]))
        if cell_id in cells:
            cell = cells[cell_id]
            price_state = LocalOutcomeState(cell["price"]["observations"], cell["price"]["phases"], [tuple(item) for item in cell["price"]["m1_innovations"]])
            volume_state = LocalOutcomeState(cell["volume"]["observations"], cell["volume"]["phases"], [tuple(item) for item in cell["volume"]["m1_innovations"]])
            prior_events = cell.get("observation_events", [cell["source_event"]] * len(price_state.observations))
            price_state.update_after_adjudication(phase, outcome["effective_weighted_price_eur_m3"])
            volume_state.update_after_adjudication(phase, outcome["awarded_volume_m3"])
            cell["price"] = {"observations": price_state.observations, "phases": price_state.phases, "m1_innovations": price_state.m1_innovations}
            cell["volume"] = {"observations": volume_state.observations, "phases": volume_state.phases, "m1_innovations": volume_state.m1_innovations}
            cell["buyers"] = sorted(set(cell.get("buyers", [])) | set(outcome["buyers"]))
            cell["observation_events"] = prior_events + [args.event_date]
            cell["latest_source_event"] = args.event_date
            updated_cells += 1
        else:
            price_state, volume_state = LocalOutcomeState(), LocalOutcomeState()
            price_state.update_after_adjudication(phase, outcome["effective_weighted_price_eur_m3"])
            volume_state.update_after_adjudication(phase, outcome["awarded_volume_m3"])
            cells[cell_id] = {
                "descriptor": descriptor,
                "source_event": args.event_date,
                "source_object_id": outcome["object_id"],
                "buyers": outcome["buyers"],
                "observation_events": [args.event_date],
                "latest_source_event": args.event_date,
                "price": {"observations": price_state.observations, "phases": price_state.phases, "m1_innovations": price_state.m1_innovations},
                "volume": {"observations": volume_state.observations, "phases": volume_state.phases, "m1_innovations": volume_state.m1_innovations},
                "weights": {"activated": False, "common_support_events": 0, "log_evidence": {"M0": 0.0, "M1": 0.0, "M2": 0.0}},
            }
            new_cells += 1

    full = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and item["awarded_volume_m3"] == item["offer_volume_m3"]]
    partial = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and 0 < item["awarded_volume_m3"] < item["offer_volume_m3"]]
    over = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and item["awarded_volume_m3"] > item["offer_volume_m3"]]
    unawarded = [item for item in result["object_totals"] if item["awarded_volume_m3"] == 0]
    not_estimable = [item for item in result["object_totals"] if item["state"] != "ADJUDICABLE"]
    price_errors = [item["price"]["absolute_error_eur_m3"] for item in local_scores]
    volume_errors = [item["volume"]["absolute_log_error"] for item in local_scores]
    scoring = {
        "schema_version": "bpm.rmk.local-scoring.v0.1",
        "event_date": args.event_date,
        "jurisdiction": "EXACT_PRODUCT_MEASUREMENT_FINGERPRINT_DESTINATION_ONLY",
        "frozen_destination_predictions": freeze["frozen_destination_predictions"],
        "scored_exact_destination_predictions": len(local_scores),
        "non_observed_or_unawarded_predictions": len(non_observed),
        "local_scores": local_scores,
        "non_observed": non_observed,
        "diagnostic_aggregate": {
            "M0_price_mean_absolute_error_eur_m3": statistics.fmean(price_errors) if price_errors else None,
            "M0_price_median_absolute_error_eur_m3": statistics.median(price_errors) if price_errors else None,
            "M0_volume_MALE": statistics.fmean(volume_errors) if volume_errors else None,
            "M0_volume_median_absolute_log_error": statistics.median(volume_errors) if volume_errors else None,
            "comparison_model": None,
            "global_winner": None,
        },
        "density_scores": "NOT_ESTIMABLE_NO_M0_DENSITY_AND_NO_COMMON_M0_M1_M2_SUPPORT",
        "global_winner": None,
        "automatic_promotion": False,
    }
    closure = event / "closure"
    scoring_path = closure / "local_scoring.json"
    write(scoring_path, scoring)
    adjudication = {
        "schema_version": "bpm.rmk.event-adjudication.v0.3",
        "event_date": args.event_date,
        "freeze_sha256": digest(freeze_path),
        "raw_result_sha256": digest(raw_result_path),
        "structured_result_sha256": digest(result_path),
        "local_scoring_sha256": digest(scoring_path),
        "award_rows": result["award_row_count"],
        "local_outcomes": result["local_outcome_count"],
        "updated_prior_cells": updated_cells,
        "new_local_cells": new_cells,
        "total_awarded_volume_m3": result["total_awarded_volume_m3"],
        "objects_full_coverage": [item["object_id"] for item in full],
        "objects_partial_coverage": [item["object_id"] for item in partial],
        "objects_over_coverage": [item["object_id"] for item in over],
        "unawarded_objects": [item["object_id"] for item in unawarded],
        "not_estimable_source_objects": [{"object_id": item["object_id"], "state": item["state"]} for item in not_estimable],
        "quarantined_outcomes": result.get("quarantined_outcomes", []),
        "scored_predictions": len(local_scores),
        "scoring_state": "M0_POINT_ONLY_EXACT_LOCAL_DESTINATIONS",
        "posterior_update_authorized": True,
        "global_winner": None,
        "automatic_promotion": False,
    }
    adjudication_path = closure / "adjudication.json"
    write(adjudication_path, adjudication)
    posterior = {
        "schema_version": "bpm.rmk.local-posterior.v0.3",
        "campaign_id": "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
        "after_event": args.event_date,
        "parent_prior_sha256": digest(prior_path),
        "adjudication_sha256": digest(adjudication_path),
        "historical_2023_2024_model_observations": 0,
        "local_cells": cells,
        "local_cell_count": len(cells),
        "price_observation_count": sum(len(cell["price"]["observations"]) for cell in cells.values()),
        "volume_observation_count": sum(len(cell["volume"]["observations"]) for cell in cells.values()),
        "posterior_observation_count": sum(len(cell["price"]["observations"]) + len(cell["volume"]["observations"]) for cell in cells.values()),
        "reset_occurred": False,
        "pooling_occurred": False,
        "global_winner": None,
        "automatic_promotion": False,
    }
    posterior_path = closure / f"prior_after_{args.event_date}.json"
    write(posterior_path, posterior)
    z_cells = {}
    for cell_id, cell in cells.items():
        z_cells[cell_id] = {
            "descriptor": cell["descriptor"],
            "price": phase_state(cell["price"]),
            "volume": phase_state(cell["volume"]),
            "BMA": {
                "state": "ESTIMABLE" if cell["weights"]["activated"] else "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT",
                "common_support_events": cell["weights"]["common_support_events"],
            },
        }
    z_post = {
        "schema_version": "bpm.rmk.model-specific-Z-post.v0.3",
        "after_event": args.event_date,
        "adjudication_sha256": digest(adjudication_path),
        "future_prior_sha256": digest(posterior_path),
        "transition_contract": "OUTCOME_t_UPDATES_ONLY_PRIOR_FOR_NEXT_COMPARABLE_EVENT",
        "Z_post_is_residual_z": False,
        "Z_post_is_Z_XPL": False,
        "Z_XPL_bilateral_thresholds": [0.25, 5.25],
        "reset_occurred": False,
        "pooling_occurred": False,
        "cells": z_cells,
    }
    z_path = closure / f"z_post_{args.event_date}.json"
    write(z_path, z_post)
    print(json.dumps({
        "scored_predictions": len(local_scores),
        "non_observed_predictions": len(non_observed),
        "updated_cells": updated_cells,
        "new_cells": new_cells,
        "local_cells": len(cells),
        "posterior_observations": posterior["posterior_observation_count"],
        "price_MAE": scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"],
        "volume_MALE": scoring["diagnostic_aggregate"]["M0_volume_MALE"],
        "posterior_sha256": digest(posterior_path),
        "z_post_sha256": digest(z_path),
    }, indent=2))


if __name__ == "__main__":
    main()
