from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))
from freeze_rmk_offer_v0_6 import frozen_outcome, weight_payload  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offer", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offer-sha256", required=True)
    parser.add_argument("--prior-sha256", required=True)
    parser.add_argument("--event-date", required=True)
    parser.add_argument("--result-url", required=True)
    args = parser.parse_args()
    if digest(args.offer) != args.offer_sha256 or digest(args.prior) != args.prior_sha256:
        raise ValueError("input hash mismatch")
    offer = json.loads(args.offer.read_text(encoding="utf-8"))
    prior = json.loads(args.prior.read_text(encoding="utf-8"))
    source_valid = offer["location_total_matches"] is True
    matches = [] if not source_valid else [
        cell for cell in prior["local_cells"].values()
        if cell["descriptor"]["product"] == offer["product"]
        and cell["descriptor"]["measurement_fingerprint_sha256"] == offer["measurement_fingerprint_sha256"]
    ]
    predictions = []
    for cell in matches:
        predictions.append({
            "destination": cell["descriptor"]["destination"],
            "price": {**frozen_outcome(cell, "price", offer["exact_calendar_phase"]), "BMA": weight_payload(cell)},
            "volume": {**frozen_outcome(cell, "volume", offer["exact_calendar_phase"]), "BMA": weight_payload(cell)},
        })
    freeze = {
        "schema_version": "bpm.rmk.hakkpuit-event-freeze.v0.2",
        "campaign_id": "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
        "event_date": args.event_date,
        "state": "FREEZE_WRITTEN_RESULT_STILL_CLOSED",
        "inputs_sha256": {"structured_offer": args.offer_sha256, "prior": args.prior_sha256},
        "object": {
            "object_id": offer["object_id"],
            "product": offer["product"],
            "measurement_fingerprint_sha256": offer["measurement_fingerprint_sha256"],
            "advertised_volume_m3": offer["advertised_volume_m3"],
            "delivery_period": offer["delivery_period"],
            "calendar_phase": offer["exact_calendar_phase"],
            "source_volume_state": "VERIFIED" if source_valid else "NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT",
            "prior_matching_destinations": sorted(cell["descriptor"]["destination"] for cell in matches),
            "frozen_local_predictions": sorted(predictions, key=lambda item: item["destination"]),
        },
        "unit_conversions_frozen_before_result": offer["frozen_conversions"],
        "frozen_destination_predictions": len(predictions),
        "M1_price_estimable_predictions": sum("point" in item["price"].get("M1", {}) for item in predictions),
        "M1_volume_estimable_predictions": sum("point" in item["volume"].get("M1", {}) for item in predictions),
        "M2_price_estimable_predictions": sum("point" in item["price"].get("M2", {}) for item in predictions),
        "M2_volume_estimable_predictions": sum("point" in item["volume"].get("M2", {}) for item in predictions),
        "result": {"url": args.result_url, "body_opened": False, "opening_authorized_only_after_this_freeze_is_hashed": True},
        "global_winner": None,
        "automatic_promotion": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "destinations": len(predictions),
        "M1_price": freeze["M1_price_estimable_predictions"],
        "M2_price": freeze["M2_price_estimable_predictions"],
    }, indent=2))


if __name__ == "__main__":
    main()
