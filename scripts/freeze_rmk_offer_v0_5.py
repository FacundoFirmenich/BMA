"""Freeze exact-cell RMK predictions using the preregistered Python model core."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rmk_timber_model_v0_1 import CommonSupportWeights, LocalOutcomeState, canonical_phase  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def measurement_fingerprint(obj: dict) -> str:
    descriptor = {
        "quality": obj["quality_and_measurement_standard"],
        "price_classes": [item["diameter_or_class"] for item in obj["price_classes"]],
        "class_weights": None,
    }
    raw = json.dumps(descriptor, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def delivery_phase(period: str, event_date: str) -> tuple[str, str | None]:
    try:
        start_text, end_text = (part.strip() for part in period.split("-"))
        start = datetime.strptime(start_text, "%d.%m.%Y")
        end = datetime.strptime(end_text, "%d.%m.%Y")
        event = datetime.strptime(event_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_ENCODING", None
    if end < start or start < event:
        return "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY", None
    year, month = start.year, start.month
    months: set[int] = set()
    while (year, month) <= (end.year, end.month):
        months.add(month)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return "VALID", canonical_phase(months)


def local_state(payload: dict) -> LocalOutcomeState:
    return LocalOutcomeState(
        observations=list(payload["observations"]),
        phases=list(payload["phases"]),
        m1_innovations=[tuple(item) for item in payload["m1_innovations"]],
    )


def frozen_outcome(cell: dict, outcome_name: str, phase: str) -> dict:
    payload = local_state(cell[outcome_name]).freeze_predictions(phase)
    innovations = cell[outcome_name]["m1_innovations"]
    events = cell[outcome_name].get("m1_innovation_events", [])
    distinct_events = {
        events[index]
        for index, (innovation_phase, _value) in enumerate(innovations)
        if innovation_phase == phase and index < len(events)
    }
    if "point" in payload.get("M2", {}) and len(distinct_events) < 2:
        payload["M2"] = {
            "state": "NOT_ESTIMABLE_SEASONAL_DISTINCT_EVENT_SUPPORT",
            "distinct_event_support": len(distinct_events),
            "required_distinct_events": 2,
        }
    else:
        payload.setdefault("M2", {})["distinct_event_support"] = len(distinct_events)
        payload["M2"]["required_distinct_events"] = 2
    return payload


def weight_payload(cell: dict) -> dict:
    source = cell["weights"]
    weights = CommonSupportWeights(
        activated=source["activated"],
        common_support_events=source["common_support_events"],
        log_evidence=dict(source["log_evidence"]),
    )
    probabilities = weights.probabilities()
    return {
        "state": "ESTIMABLE" if probabilities is not None else "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT",
        "probabilities": probabilities,
        "common_support_events": weights.common_support_events,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offer", required=True, type=Path)
    parser.add_argument("--prior", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--raw-offer-sha256", required=True)
    parser.add_argument("--structured-offer-sha256", required=True)
    parser.add_argument("--prior-sha256", required=True)
    parser.add_argument("--software-amendment-sha256", required=True)
    parser.add_argument("--event-date", required=True)
    parser.add_argument("--result-url", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    offer, prior = load(args.offer), load(args.prior)
    if digest(args.offer) != args.structured_offer_sha256:
        raise ValueError("structured offer hash mismatch")
    if digest(args.prior) != args.prior_sha256:
        raise ValueError("prior hash mismatch")
    prior_cells = list(prior["local_cells"].values())
    objects = []
    for obj in offer["objects"]:
        period_state, phase = delivery_phase(obj["delivery_period"], args.event_date)
        fingerprint = measurement_fingerprint(obj)
        matches = [] if period_state != "VALID" else [
            cell for cell in prior_cells
            if cell["descriptor"]["product"] == obj["product"]
            and cell["descriptor"]["measurement_fingerprint_sha256"] == fingerprint
        ]
        predictions = []
        for cell in matches:
            predictions.append({
                "destination": cell["descriptor"]["destination"],
                "price": {
                    **frozen_outcome(cell, "price", phase),
                    "BMA": weight_payload(cell),
                },
                "volume": {
                    **frozen_outcome(cell, "volume", phase),
                    "BMA": weight_payload(cell),
                },
            })
        objects.append({
            "object_id": obj["object_id"],
            "product": obj["product"],
            "delivery_period": obj["delivery_period"],
            "delivery_period_state": period_state,
            "calendar_phase": phase,
            "source_volume_state": obj.get("location_volume_state"),
            "measurement_fingerprint_sha256": fingerprint,
            "prior_matching_destinations": sorted(cell["descriptor"]["destination"] for cell in matches),
            "frozen_local_predictions": sorted(predictions, key=lambda item: item["destination"]),
            "no_match_state": period_state if period_state != "VALID" else ("NOT_ESTIMABLE_NO_PRIOR_COMPARABLE_BASE_CELL" if not matches else None),
        })
    freeze = {
        "schema_version": "bpm.rmk.event-freeze.v0.5",
        "campaign_id": "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
        "event_date": args.event_date,
        "state": "FREEZE_WRITTEN_PAIRED_RESULT_STILL_CLOSED",
        "inputs_sha256": {"raw_offer": args.raw_offer_sha256, "structured_offer": args.structured_offer_sha256, "prior": args.prior_sha256},
        "software_amendment_sha256": args.software_amendment_sha256,
        "object_count": len(objects),
        "invalid_delivery_period_objects": [item["object_id"] for item in objects if item["delivery_period_state"] != "VALID"],
        "source_volume_conflict_objects": [item["object_id"] for item in objects if not str(item["source_volume_state"]).startswith("VERIFIED_")],
        "objects_with_prior_base_cell_match": sum(bool(item["prior_matching_destinations"]) for item in objects),
        "frozen_destination_predictions": sum(len(item["frozen_local_predictions"]) for item in objects),
        "M1_price_estimable_predictions": sum("point" in prediction["price"].get("M1", {}) for item in objects for prediction in item["frozen_local_predictions"]),
        "M1_volume_estimable_predictions": sum("point" in prediction["volume"].get("M1", {}) for item in objects for prediction in item["frozen_local_predictions"]),
        "M2_price_estimable_predictions": sum("point" in prediction["price"].get("M2", {}) for item in objects for prediction in item["frozen_local_predictions"]),
        "M2_volume_estimable_predictions": sum("point" in prediction["volume"].get("M2", {}) for item in objects for prediction in item["frozen_local_predictions"]),
        "objects": objects,
        "paired_result": {"url": args.result_url, "body_opened": False, "opening_authorized_only_after_this_freeze_is_hashed": True},
        "global_winner": None,
        "automatic_promotion": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: freeze[key] for key in ("object_count", "objects_with_prior_base_cell_match", "frozen_destination_predictions", "M1_price_estimable_predictions", "M1_volume_estimable_predictions", "M2_price_estimable_predictions", "M2_volume_estimable_predictions")}, indent=2))


if __name__ == "__main__":
    main()
