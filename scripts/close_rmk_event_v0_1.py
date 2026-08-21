from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rmk_timber_model_v0_1 import LocalOutcomeState, canonical_phase  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def months_in_period(period: str) -> list[int]:
    start_text, end_text = period.split("-")
    start = datetime.strptime(start_text, "%d.%m.%Y")
    end = datetime.strptime(end_text, "%d.%m.%Y")
    months: set[int] = set()
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.add(month)
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return sorted(months)


def stable_cell_id(descriptor: dict) -> str:
    raw = json.dumps(descriptor, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offer", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--raw-result", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    offer = json.loads(args.offer.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    freeze = json.loads(args.freeze.read_text(encoding="utf-8"))
    prior = json.loads(args.prior.read_text(encoding="utf-8"))
    if freeze["state"] != "FREEZE_WRITTEN_RESULT_STILL_CLOSED":
        raise ValueError("invalid pre-result freeze")
    if freeze["inputs_sha256"]["prior"] != sha256(args.prior):
        raise ValueError("freeze/prior hash mismatch")
    if freeze["inputs_sha256"]["structured_offer"] != sha256(args.offer):
        raise ValueError("freeze/offer hash mismatch")
    if prior["posterior_observation_count"] != 0:
        raise ValueError("first event prior was not empty")
    if result["price_mapping_failures"]:
        raise ValueError("price mapping failures must be adjudicated before posterior update")

    offer_by_id = {item["object_id"]: item for item in offer["objects"]}
    cells: dict[str, dict] = {}
    for outcome in result["local_outcomes"]:
        if outcome["price_state"] != "ESTIMABLE_EXACT_DESTINATION_FALLBACK":
            continue
        obj = offer_by_id[outcome["object_id"]]
        phase = canonical_phase(months_in_period(obj["delivery_period"]))
        descriptor = {
            "product": outcome["product"],
            "measurement_fingerprint_sha256": outcome["measurement_fingerprint_sha256"],
            "destination": outcome["destination"],
        }
        cell_id = stable_cell_id(descriptor)
        if cell_id in cells:
            raise ValueError("more than one same-event observation would enter one local cell")
        price_state = LocalOutcomeState()
        volume_state = LocalOutcomeState()
        price_state.update_after_adjudication(phase, outcome["effective_weighted_price_eur_m3"])
        volume_state.update_after_adjudication(phase, outcome["awarded_volume_m3"])
        cells[cell_id] = {
            "descriptor": descriptor,
            "source_event": "2025-02-26",
            "source_object_id": outcome["object_id"],
            "buyers": outcome["buyers"],
            "price": {
                "observations": price_state.observations,
                "phases": price_state.phases,
                "m1_innovations": price_state.m1_innovations,
            },
            "volume": {
                "observations": volume_state.observations,
                "phases": volume_state.phases,
                "m1_innovations": volume_state.m1_innovations,
            },
            "weights": {
                "activated": False,
                "common_support_events": 0,
                "log_evidence": {"M0": 0.0, "M1": 0.0, "M2": 0.0},
            },
        }

    full = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and item["awarded_volume_m3"] == item["offer_volume_m3"]]
    partial = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and item["awarded_volume_m3"] != item["offer_volume_m3"]]
    source_conflicts = [item for item in result["object_totals"] if item["state"] != "ADJUDICABLE"]

    adjudication = {
        "schema_version": "bpm.rmk.event-adjudication.v0.1",
        "event_date": "2025-02-26",
        "freeze_sha256": sha256(args.freeze),
        "raw_result_sha256": sha256(args.raw_result),
        "structured_result_sha256": sha256(args.result),
        "award_rows": result["award_row_count"],
        "local_outcomes": result["local_outcome_count"],
        "total_awarded_volume_m3": result["total_awarded_volume_m3"],
        "objects_full_coverage": [item["object_id"] for item in full],
        "objects_partial_coverage": [item["object_id"] for item in partial],
        "objects_source_volume_conflict": [item["object_id"] for item in source_conflicts],
        "unawarded_objects": [item["object_id"] for item in result["object_totals"] if item["awarded_volume_m3"] == 0],
        "scored_predictions": 0,
        "scoring_state": "NOT_ESTIMABLE_EMPTY_CAUSAL_PRIOR",
        "price_normalization": "EXACT_DESTINATION_FALLBACK_ONLY_HISTORICAL_2025_TARIFF_VINTAGE_UNAVAILABLE",
        "posterior_update_authorized": True,
        "global_winner": None,
        "automatic_promotion": False,
    }
    adjudication_path = args.output_dir / "adjudication.json"
    write_json(adjudication_path, adjudication)

    posterior = {
        "schema_version": "bpm.rmk.local-posterior.v0.1",
        "campaign_id": "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
        "after_event": "2025-02-26",
        "parent_prior_sha256": sha256(args.prior),
        "adjudication_sha256": sha256(adjudication_path),
        "historical_2023_2024_model_observations": 0,
        "local_cells": cells,
        "local_cell_count": len(cells),
        "price_observation_count": len(cells),
        "volume_observation_count": len(cells),
        "posterior_observation_count": 2 * len(cells),
        "reset_occurred": False,
        "pooling_occurred": False,
        "global_winner": None,
        "automatic_promotion": False,
    }
    posterior_path = args.output_dir / "prior_after_2025-02-26.json"
    write_json(posterior_path, posterior)

    z_cells = {}
    for cell_id, cell in cells.items():
        z_cells[cell_id] = {
            "descriptor": cell["descriptor"],
            "price": {
                "M0": {"point_support": 1, "transition_support": 0, "density": "NOT_ESTIMABLE_M0_DENSITY_SUPPORT"},
                "M1": {"observation_support": 1, "required": 3, "state": "NOT_ESTIMABLE_M1_SUPPORT"},
                "M2": {"same_phase_innovation_support": 0, "required": 2, "state": "NOT_ESTIMABLE_SEASONAL_SUPPORT"},
            },
            "volume": {
                "M0": {"point_support": 1, "transition_support": 0, "density": "NOT_ESTIMABLE_M0_DENSITY_SUPPORT"},
                "M1": {"observation_support": 1, "required": 3, "state": "NOT_ESTIMABLE_M1_SUPPORT"},
                "M2": {"same_phase_innovation_support": 0, "required": 2, "state": "NOT_ESTIMABLE_SEASONAL_SUPPORT"},
            },
            "BMA": {"state": "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT", "common_support_events": 0},
        }
    z_post = {
        "schema_version": "bpm.rmk.model-specific-Z-post.v0.1",
        "after_event": "2025-02-26",
        "adjudication_sha256": sha256(adjudication_path),
        "future_prior_sha256": sha256(posterior_path),
        "transition_contract": "OUTCOME_t_UPDATES_ONLY_PRIOR_FOR_NEXT_COMPARABLE_EVENT",
        "Z_post_is_residual_z": False,
        "Z_post_is_Z_XPL": False,
        "Z_XPL_bilateral_thresholds": [0.25, 5.25],
        "reset_occurred": False,
        "cells": z_cells,
    }
    z_path = args.output_dir / "z_post_2025-02-26.json"
    write_json(z_path, z_post)
    print(
        json.dumps(
            {
                "cells": len(cells),
                "full_coverage_objects": len(full),
                "partial_coverage_objects": len(partial),
                "source_conflict_objects": len(source_conflicts),
                "adjudication_sha256": sha256(adjudication_path),
                "posterior_sha256": sha256(posterior_path),
                "z_post_sha256": sha256(z_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
