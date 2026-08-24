from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rmk_timber_model_v0_1 import LocalOutcomeState, canonical_phase  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-04-24"
PRIOR_PATH = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-03-20/closure/prior_after_2025-03-20.json"


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
    result = set()
    while (year, month) <= (end.year, end.month):
        result.add(month)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return sorted(result)


def identifier(descriptor: dict) -> str:
    raw = json.dumps(descriptor, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


offer_path, result_path = EVENT / "structured/offer.json", EVENT / "structured/result.json"
freeze_path, raw_result = EVENT / "freeze/freeze.json", EVENT / "raw/Edukad_KLH_24.04.2025.xlsx"
offer, result, freeze, prior = load(offer_path), load(result_path), load(freeze_path), load(PRIOR_PATH)
if freeze["frozen_destination_predictions"] != 0 or freeze["objects_with_prior_base_cell_match"] != 0:
    raise ValueError("this closure is authorized only for a zero-match freeze")
if freeze["inputs_sha256"]["prior_after_2025_03_20"] != digest(PRIOR_PATH):
    raise ValueError("prior hash mismatch")
if result["price_mapping_failures"]:
    raise ValueError("price mapping failures")

cells = json.loads(json.dumps(prior["local_cells"]))
new_cells = 0
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
        "source_event": "2025-04-24",
        "source_object_id": outcome["object_id"],
        "buyers": outcome["buyers"],
        "price": {"observations": price_state.observations, "phases": price_state.phases, "m1_innovations": price_state.m1_innovations},
        "volume": {"observations": volume_state.observations, "phases": volume_state.phases, "m1_innovations": volume_state.m1_innovations},
        "weights": {"activated": False, "common_support_events": 0, "log_evidence": {"M0": 0.0, "M1": 0.0, "M2": 0.0}},
    }
    new_cells += 1

full = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and item["awarded_volume_m3"] == item["offer_volume_m3"]]
partial = [item for item in result["object_totals"] if item["state"] == "ADJUDICABLE" and 0 < item["awarded_volume_m3"] < item["offer_volume_m3"]]
unawarded = [item for item in result["object_totals"] if item["awarded_volume_m3"] == 0]
closure = EVENT / "closure"
adjudication = {
    "schema_version": "bpm.rmk.event-adjudication.v0.1",
    "event_date": "2025-04-24",
    "freeze_sha256": digest(freeze_path),
    "raw_result_sha256": digest(raw_result),
    "structured_result_sha256": digest(result_path),
    "award_rows": result["award_row_count"],
    "new_local_outcomes": new_cells,
    "total_awarded_volume_m3": result["total_awarded_volume_m3"],
    "objects_full_coverage": [item["object_id"] for item in full],
    "objects_partial_coverage": [item["object_id"] for item in partial],
    "unawarded_objects": [item["object_id"] for item in unawarded],
    "scored_predictions": 0,
    "scoring_state": "NOT_ESTIMABLE_NO_PRIOR_COMPARABLE_BASE_CELL",
    "posterior_update_authorized": True,
    "global_winner": None,
    "automatic_promotion": False,
}
adjudication_path = closure / "adjudication.json"
write(adjudication_path, adjudication)
posterior = {
    "schema_version": "bpm.rmk.local-posterior.v0.1",
    "campaign_id": "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
    "after_event": "2025-04-24",
    "parent_prior_sha256": digest(PRIOR_PATH),
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
posterior_path = closure / "prior_after_2025-04-24.json"
write(posterior_path, posterior)
z_cells = {}
for cell_id, cell in cells.items():
    z_cells[cell_id] = {"descriptor": cell["descriptor"]}
    for name in ("price", "volume"):
        count = len(cell[name]["observations"])
        phase_counts = {}
        for phase in cell[name]["phases"]:
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        z_cells[cell_id][name] = {
            "M0": {"point_support": count, "transition_support": max(0, count - 1), "density_state": "ESTIMABLE" if count >= 4 else "NOT_ESTIMABLE_M0_DENSITY_SUPPORT"},
            "M1": {"observation_support": count, "required": 3, "state": "ESTIMABLE" if count >= 3 else "NOT_ESTIMABLE_M1_SUPPORT"},
            "M2": {"same_phase_observation_counts": phase_counts, "same_phase_innovation_support": len(cell[name]["m1_innovations"]), "required": 2, "state": "NOT_ESTIMABLE_SEASONAL_SUPPORT"},
        }
    z_cells[cell_id]["BMA"] = {"state": "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT", "common_support_events": 0}
z_post = {
    "schema_version": "bpm.rmk.model-specific-Z-post.v0.1",
    "after_event": "2025-04-24",
    "adjudication_sha256": digest(adjudication_path),
    "future_prior_sha256": digest(posterior_path),
    "transition_contract": "OUTCOME_t_UPDATES_ONLY_PRIOR_FOR_NEXT_COMPARABLE_EVENT",
    "Z_post_is_residual_z": False,
    "Z_post_is_Z_XPL": False,
    "Z_XPL_bilateral_thresholds": [0.25, 5.25],
    "reset_occurred": False,
    "cells": z_cells,
}
z_path = closure / "z_post_2025-04-24.json"
write(z_path, z_post)
print(json.dumps({
    "new_cells": new_cells,
    "local_cells": len(cells),
    "posterior_observations": posterior["posterior_observation_count"],
    "full_objects": len(full),
    "partial_objects": len(partial),
    "unawarded_objects": [item["object_id"] for item in unawarded],
    "posterior_sha256": digest(posterior_path),
    "z_post_sha256": digest(z_path),
}, indent=2))
