"""Close one causally frozen RMK event with zero prior comparable base cells."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
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
    start_text, end_text = period.split("-")
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-date", required=True)
    parser.add_argument("--prior", required=True, type=Path)
    parser.add_argument("--raw-result-name", required=True)
    parser.add_argument("--repaired-offer-name", default="offer_structured_v2_location_repair.json")
    parser.add_argument("--repair-receipt-name", default="OFFER_LOCATION_TOTAL_REPAIR_RECEIPT.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    event = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events" / args.event_date
    prior_path = args.prior if args.prior.is_absolute() else ROOT / args.prior
    frozen_offer_path = event / "structured/offer_structured.json"
    repaired_offer_path = event / "structured" / args.repaired_offer_name
    repair_receipt_path = event / "structured" / args.repair_receipt_name
    result_path = event / "structured/result.json"
    freeze_path = event / "freeze/freeze.json"
    raw_result_path = event / "raw" / args.raw_result_name

    frozen_offer = load(frozen_offer_path)
    repaired_offer = load(repaired_offer_path)
    repair_receipt = load(repair_receipt_path)
    result = load(result_path)
    freeze = load(freeze_path)
    prior = load(prior_path)

    if freeze["event_date"] != args.event_date or result["event_date"] != args.event_date:
        raise ValueError("event date mismatch")
    if freeze["frozen_destination_predictions"] != 0 or freeze["objects_with_prior_base_cell_match"] != 0:
        raise ValueError("zero-match closer cannot close a scored freeze")
    if freeze["inputs_sha256"]["prior"] != digest(prior_path):
        raise ValueError("prior hash mismatch")
    if freeze["inputs_sha256"]["structured_offer"] != digest(frozen_offer_path):
        raise ValueError("frozen structured-offer hash mismatch")
    if repair_receipt["frozen_offer_preserved_sha256"] != digest(frozen_offer_path):
        raise ValueError("repair receipt frozen-offer link mismatch")
    if repair_receipt["repaired_offer_sha256"] != digest(repaired_offer_path):
        raise ValueError("repair receipt repaired-offer link mismatch")
    if result["source_sha256"] != digest(raw_result_path):
        raise ValueError("raw-result hash mismatch")
    if result["structured_offer_used_sha256"] != digest(repaired_offer_path):
        raise ValueError("result repaired-offer link mismatch")
    if result["extraction_failures"]:
        raise ValueError("result extraction failures")
    if freeze["quarantined_unpaired_result"]["body_opened"] is not False:
        raise ValueError("unpaired result was opened")

    frozen_by_id = {item["object_id"]: item for item in freeze["objects"]}
    for outcome in result["local_outcomes"]:
        frozen = frozen_by_id[outcome["object_id"]]
        if outcome["product"] != frozen["product"]:
            raise ValueError("outcome product differs from freeze")
        if outcome["measurement_fingerprint_sha256"] != frozen["measurement_fingerprint_sha256"]:
            raise ValueError("outcome measurement fingerprint differs from freeze")

    cells = json.loads(json.dumps(prior["local_cells"]))
    new_cells = 0
    phase_by_cell: dict[str, str] = {}
    for outcome in result["local_outcomes"]:
        descriptor = {
            "product": outcome["product"],
            "measurement_fingerprint_sha256": outcome["measurement_fingerprint_sha256"],
            "destination": outcome["destination"],
        }
        cell_id = identifier(descriptor)
        if cell_id in cells:
            raise ValueError("outcome matched a prior cell despite zero-match freeze")
        phase = canonical_phase(months(outcome["delivery_period"]))
        price_state, volume_state = LocalOutcomeState(), LocalOutcomeState()
        price_state.update_after_adjudication(phase, outcome["effective_weighted_price_eur_m3"])
        volume_state.update_after_adjudication(phase, outcome["awarded_volume_m3"])
        cells[cell_id] = {
            "descriptor": descriptor,
            "source_event": args.event_date,
            "source_object_id": outcome["object_id"],
            "buyers": outcome["buyers"],
            "price": {"observations": price_state.observations, "phases": price_state.phases, "m1_innovations": price_state.m1_innovations},
            "volume": {"observations": volume_state.observations, "phases": volume_state.phases, "m1_innovations": volume_state.m1_innovations},
            "weights": {"activated": False, "common_support_events": 0, "log_evidence": {"M0": 0.0, "M1": 0.0, "M2": 0.0}},
        }
        phase_by_cell[cell_id] = phase
        new_cells += 1

    full = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and item["awarded_volume_m3"] == item["offer_volume_m3"]]
    partial = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and 0 < item["awarded_volume_m3"] < item["offer_volume_m3"]]
    over = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and item["awarded_volume_m3"] > item["offer_volume_m3"]]
    unawarded = [item for item in result["object_totals"] if item["awarded_volume_m3"] == 0]
    not_estimable = [item for item in result["object_totals"] if item["state"] != "ADJUDICABLE"]
    closure = event / "closure"
    adjudication = {
        "schema_version": "bpm.rmk.event-adjudication.v0.2",
        "event_date": args.event_date,
        "freeze_sha256": digest(freeze_path),
        "raw_result_sha256": digest(raw_result_path),
        "structured_result_sha256": digest(result_path),
        "offer_repair_receipt_sha256": digest(repair_receipt_path),
        "award_rows": result["award_row_count"],
        "new_local_outcomes": new_cells,
        "total_awarded_volume_m3": result["total_awarded_volume_m3"],
        "objects_full_coverage": [item["object_id"] for item in full],
        "objects_partial_coverage": [item["object_id"] for item in partial],
        "objects_over_coverage": [item["object_id"] for item in over],
        "unawarded_objects": [item["object_id"] for item in unawarded],
        "not_estimable_source_objects": [item["object_id"] for item in not_estimable],
        "scored_predictions": 0,
        "scoring_state": "NOT_ESTIMABLE_NO_PRIOR_COMPARABLE_BASE_CELL",
        "posterior_update_authorized": True,
        "quarantined_unpaired_result": result["quarantined_unpaired_result"],
        "global_winner": None,
        "automatic_promotion": False,
    }
    adjudication_path = closure / "adjudication.json"
    write(adjudication_path, adjudication)

    posterior = {
        "schema_version": "bpm.rmk.local-posterior.v0.2",
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
        z_cells[cell_id] = {"descriptor": cell["descriptor"]}
        for name in ("price", "volume"):
            count = len(cell[name]["observations"])
            phase_counts: dict[str, int] = {}
            for phase in cell[name]["phases"]:
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
            innovation_counts: dict[str, int] = {}
            for phase, _value in cell[name]["m1_innovations"]:
                innovation_counts[phase] = innovation_counts.get(phase, 0) + 1
            estimable_phases = sorted(phase for phase, support in innovation_counts.items() if support >= 2)
            z_cells[cell_id][name] = {
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
        z_cells[cell_id]["BMA"] = {
            "state": "ESTIMABLE" if cell["weights"]["activated"] else "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT",
            "common_support_events": cell["weights"]["common_support_events"],
        }
    z_post = {
        "schema_version": "bpm.rmk.model-specific-Z-post.v0.2",
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
        "new_cells": new_cells,
        "local_cells": len(cells),
        "posterior_observations": posterior["posterior_observation_count"],
        "full_objects": len(full),
        "partial_objects": len(partial),
        "over_objects": [item["object_id"] for item in over],
        "unawarded_objects": [item["object_id"] for item in unawarded],
        "posterior_sha256": digest(posterior_path),
        "z_post_sha256": digest(z_path),
    }, indent=2))


if __name__ == "__main__":
    main()
