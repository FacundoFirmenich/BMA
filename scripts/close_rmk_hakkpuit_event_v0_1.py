from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cell_id(descriptor: dict) -> str:
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

    offer = json.loads(args.offer.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    freeze = json.loads(args.freeze.read_text(encoding="utf-8"))
    prior = json.loads(args.prior.read_text(encoding="utf-8"))
    if freeze["result"]["body_opened"] is not False or freeze["scorable_predictions"] != 0:
        raise ValueError("invalid pre-result freeze")
    if freeze["inputs_sha256"]["prior_after_2025-02-26"] != digest(args.prior):
        raise ValueError("prior hash mismatch")
    if any(cell["descriptor"]["product"] == "Hakkpuit" for cell in prior["local_cells"].values()):
        raise ValueError("wood-chip history unexpectedly present before first causal wood-chip result")

    cells = json.loads(json.dumps(prior["local_cells"]))
    for outcome in result["local_outcomes"]:
        descriptor = {
            "product": outcome["product"],
            "measurement_fingerprint_sha256": outcome["measurement_fingerprint_sha256"],
            "destination": outcome["destination"],
        }
        identifier = cell_id(descriptor)
        if identifier in cells:
            raise ValueError("unexpected existing wood-chip destination cell")
        phase = outcome["calendar_phase"]
        cells[identifier] = {
            "descriptor": descriptor,
            "source_event": "2025-03-20",
            "source_object_id": 1,
            "buyers": [outcome["buyer"]],
            "price": {"observations": [outcome["awarded_price_eur_m3"]], "phases": [phase], "m1_innovations": []},
            "volume": {"observations": [outcome["awarded_volume_m3"]], "phases": [phase], "m1_innovations": []},
            "weights": {"activated": False, "common_support_events": 0, "log_evidence": {"M0": 0.0, "M1": 0.0, "M2": 0.0}},
        }

    adjudication = {
        "schema_version": "bpm.rmk.event-adjudication.v0.1",
        "event_date": "2025-03-20",
        "freeze_sha256": digest(args.freeze),
        "raw_result_sha256": digest(args.raw_result),
        "structured_result_sha256": digest(args.result),
        "award_rows": 2,
        "new_local_outcomes": 2,
        "total_awarded_volume_pm3": result["total_awarded_volume_pm3"],
        "total_awarded_volume_m3": result["total_awarded_volume_m3"],
        "approximate_offer_volume_m3": result["approximate_offer_volume_m3"],
        "approximate_coverage_ratio": result["approximate_coverage_ratio"],
        "coverage_state": result["coverage_state"],
        "scored_predictions": 0,
        "scoring_state": "NOT_ESTIMABLE_FIRST_CAUSAL_HAKKPUIT_OBSERVATION_PER_DESTINATION",
        "posterior_update_authorized": True,
        "global_winner": None,
        "automatic_promotion": False,
    }
    adjudication_path = args.output_dir / "adjudication.json"
    write_json(adjudication_path, adjudication)

    posterior = {
        "schema_version": "bpm.rmk.local-posterior.v0.1",
        "campaign_id": "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
        "after_event": "2025-03-20",
        "parent_prior_sha256": digest(args.prior),
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
    posterior_path = args.output_dir / "prior_after_2025-03-20.json"
    write_json(posterior_path, posterior)

    z_cells = {}
    for identifier, cell in cells.items():
        z_cells[identifier] = {"descriptor": cell["descriptor"]}
        for outcome_name in ("price", "volume"):
            count = len(cell[outcome_name]["observations"])
            phase_counts = {}
            for phase in cell[outcome_name]["phases"]:
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
            z_cells[identifier][outcome_name] = {
                "M0": {"point_support": count, "transition_support": max(0, count - 1), "density_state": "ESTIMABLE" if count - 1 >= 3 else "NOT_ESTIMABLE_M0_DENSITY_SUPPORT"},
                "M1": {"observation_support": count, "required": 3, "state": "ESTIMABLE" if count >= 3 else "NOT_ESTIMABLE_M1_SUPPORT"},
                "M2": {"same_phase_observation_counts": phase_counts, "same_phase_innovation_support": len(cell[outcome_name]["m1_innovations"]), "required": 2, "state": "NOT_ESTIMABLE_SEASONAL_SUPPORT"},
            }
        z_cells[identifier]["BMA"] = {"state": "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT", "common_support_events": 0}
    z_post = {
        "schema_version": "bpm.rmk.model-specific-Z-post.v0.1",
        "after_event": "2025-03-20",
        "adjudication_sha256": digest(adjudication_path),
        "future_prior_sha256": digest(posterior_path),
        "transition_contract": "OUTCOME_t_UPDATES_ONLY_PRIOR_FOR_NEXT_COMPARABLE_EVENT",
        "Z_post_is_residual_z": False,
        "Z_post_is_Z_XPL": False,
        "Z_XPL_bilateral_thresholds": [0.25, 5.25],
        "reset_occurred": False,
        "cells": z_cells,
    }
    z_path = args.output_dir / "z_post_2025-03-20.json"
    write_json(z_path, z_post)
    print(json.dumps({
        "local_cells": posterior["local_cell_count"],
        "posterior_observations": posterior["posterior_observation_count"],
        "adjudication_sha256": digest(adjudication_path),
        "posterior_sha256": digest(posterior_path),
        "z_post_sha256": digest(z_path),
    }, indent=2))


if __name__ == "__main__":
    main()
