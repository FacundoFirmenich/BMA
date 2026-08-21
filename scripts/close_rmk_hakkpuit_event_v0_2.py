from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))
from close_rmk_scored_event_v0_2 import phase_state  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def identifier(descriptor: dict) -> str:
    raw = json.dumps(descriptor, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offer", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--raw-result", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    offer, result, freeze, prior = map(load, (args.offer, args.result, args.freeze, args.prior))
    if result["freeze_used_sha256"] != digest(args.freeze) or freeze["inputs_sha256"]["prior"] != digest(args.prior):
        raise ValueError("custody link mismatch")
    predictions = {item["destination"]: item for item in freeze["object"]["frozen_local_predictions"]}
    outcomes = {item["destination"]: item for item in result["local_outcomes"]}
    score_destinations = sorted(predictions.keys() & outcomes.keys())
    scores = []
    for destination in score_destinations:
        prediction, outcome = predictions[destination], outcomes[destination]
        scores.append({
            "object_id": 1, "product": "Hakkpuit", "destination": destination, "phase": offer["exact_calendar_phase"],
            "price": {"actual_eur_m3": outcome["effective_weighted_price_eur_m3"], "M0": {"point_prediction_eur_m3": prediction["price"]["M0"]["point"], "absolute_error_eur_m3": abs(prediction["price"]["M0"]["point"] - outcome["effective_weighted_price_eur_m3"])}, "M1": prediction["price"]["M1"], "M2": prediction["price"]["M2"], "BMA": prediction["price"]["BMA"]},
            "volume": {"actual_m3": outcome["awarded_volume_m3"], "M0": {"point_prediction_m3": prediction["volume"]["M0"]["point"], "absolute_log_error": abs(math.log(prediction["volume"]["M0"]["point"]) - math.log(outcome["awarded_volume_m3"]))}, "M1": prediction["volume"]["M1"], "M2": prediction["volume"]["M2"], "BMA": prediction["volume"]["BMA"]},
        })
    non_observed = [{"object_id": 1, "product": "Hakkpuit", "destination": value, "state": "NOT_OBSERVED_EXACT_DESTINATION_OUTCOME"} for value in sorted(predictions.keys() - outcomes.keys())]
    price_errors = [item["price"]["M0"]["absolute_error_eur_m3"] for item in scores]
    volume_errors = [item["volume"]["M0"]["absolute_log_error"] for item in scores]
    scoring = {"schema_version": "bpm.rmk.hakkpuit-local-scoring.v0.2", "event_date": offer["event_date"], "jurisdiction": "EXACT_HAKKPUIT_FINGERPRINT_DESTINATION_ONLY", "frozen_destination_predictions": len(predictions), "scored_exact_destination_predictions": len(scores), "non_observed_or_unawarded_predictions": len(non_observed), "local_scores": scores, "non_observed": non_observed, "diagnostic_aggregate": {"M0_price_mean_absolute_error_eur_m3": statistics.fmean(price_errors) if price_errors else None, "M0_volume_MALE": statistics.fmean(volume_errors) if volume_errors else None, "global_winner": None}, "global_winner": None, "automatic_promotion": False}
    scoring_path = args.output_dir / "local_scoring.json"
    write(scoring_path, scoring)
    cells = copy.deepcopy(prior["local_cells"])
    updated = new = 0
    for outcome in result["local_outcomes"]:
        descriptor = {"product": outcome["product"], "measurement_fingerprint_sha256": outcome["measurement_fingerprint_sha256"], "destination": outcome["destination"]}
        key = identifier(descriptor)
        if key in cells:
            cell = cells[key]
            updated += 1
            cell.setdefault("observation_events", []).append(offer["event_date"])
            cell["buyers"] = sorted(set(cell.get("buyers", [])) | set(outcome["buyers"]))
        else:
            new += 1
            cell = {"descriptor": descriptor, "source_event": offer["event_date"], "source_object_id": 1, "buyers": outcome["buyers"], "observation_events": [offer["event_date"]], "price": {"observations": [], "phases": [], "m1_innovations": [], "m1_innovation_events": []}, "volume": {"observations": [], "phases": [], "m1_innovations": [], "m1_innovation_events": []}, "weights": {"activated": False, "common_support_events": 0, "log_evidence": {"M0": 0.0, "M1": 0.0, "M2": 0.0}}}
            cells[key] = cell
        for name, value in (("price", outcome["effective_weighted_price_eur_m3"]), ("volume", outcome["awarded_volume_m3"])):
            cell[name].setdefault("m1_innovation_events", [])
            cell[name]["observations"].append(value)
            cell[name]["phases"].append(outcome["calendar_phase"])
    adjudication = {"schema_version": "bpm.rmk.hakkpuit-event-adjudication.v0.2", "event_date": offer["event_date"], "freeze_sha256": digest(args.freeze), "raw_result_sha256": digest(args.raw_result), "structured_result_sha256": digest(args.result), "local_scoring_sha256": digest(scoring_path), "award_rows": result["award_row_count"], "local_outcomes": len(result["local_outcomes"]), "updated_prior_cells": updated, "new_local_cells": new, "total_awarded_volume_pm3": result["total_awarded_volume_pm3"], "total_awarded_volume_m3": result["total_awarded_volume_m3"], "approximate_coverage_ratio": result["approximate_coverage_ratio"], "coverage_state": result["coverage_state"], "scored_predictions": len(scores), "posterior_update_authorized": True, "global_winner": None, "automatic_promotion": False}
    adjudication_path = args.output_dir / "adjudication.json"
    write(adjudication_path, adjudication)
    posterior = {"schema_version": "bpm.rmk.local-posterior.v0.4", "campaign_id": prior["campaign_id"], "after_event": offer["event_date"], "parent_prior_sha256": digest(args.prior), "adjudication_sha256": digest(adjudication_path), "historical_2023_2024_model_observations": 0, "local_cells": cells, "local_cell_count": len(cells), "price_observation_count": sum(len(c["price"]["observations"]) for c in cells.values()), "volume_observation_count": sum(len(c["volume"]["observations"]) for c in cells.values()), "posterior_observation_count": sum(len(c["price"]["observations"]) + len(c["volume"]["observations"]) for c in cells.values()), "reset_occurred": False, "pooling_occurred": False, "global_winner": None, "automatic_promotion": False}
    posterior_path = args.output_dir / f"prior_after_{offer['event_date']}.json"
    write(posterior_path, posterior)
    z_cells = {key: {"descriptor": cell["descriptor"], "price": phase_state(cell["price"]), "volume": phase_state(cell["volume"]), "BMA": {"state": "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT", "common_support_events": cell["weights"]["common_support_events"]}} for key, cell in cells.items()}
    z_post = {"schema_version": "bpm.rmk.model-specific-Z-post.v0.4", "after_event": offer["event_date"], "adjudication_sha256": digest(adjudication_path), "future_prior_sha256": digest(posterior_path), "transition_contract": "OUTCOME_t_UPDATES_ONLY_PRIOR_FOR_NEXT_COMPARABLE_EVENT", "Z_post_is_residual_z": False, "Z_post_is_Z_XPL": False, "Z_XPL_bilateral_thresholds": [0.25, 5.25], "reset_occurred": False, "pooling_occurred": False, "cells": z_cells}
    z_path = args.output_dir / f"z_post_{offer['event_date']}.json"
    write(z_path, z_post)
    print(json.dumps({"scores": len(scores), "updated": updated, "new": new, "cells": len(cells), "observations": posterior["posterior_observation_count"], "price_MAE": scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"], "volume_MALE": scoring["diagnostic_aggregate"]["M0_volume_MALE"], "posterior_sha256": digest(posterior_path), "z_post_sha256": digest(z_path)}, indent=2))


if __name__ == "__main__":
    main()
