from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def exact_month_set(period: str) -> list[int]:
    start_text, end_text = period.split("-")
    start = datetime.strptime(start_text, "%d.%m.%Y")
    end = datetime.strptime(end_text, "%d.%m.%Y")
    if end < start:
        raise ValueError(f"reversed period {period}")
    year, month = start.year, start.month
    months: set[int] = set()
    while (year, month) <= (end.year, end.month):
        months.add(month)
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return sorted(months)


def phase_label(months: list[int]) -> str:
    return "-".join(f"M{month:02d}" for month in months)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offer", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--software", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    offer = json.loads(args.offer.read_text(encoding="utf-8"))
    prior = json.loads(args.prior.read_text(encoding="utf-8"))
    if prior["posterior_observation_count"] != 0 or prior["local_cells"]:
        raise ValueError("first RMK causal freeze requires a genuinely empty prior")
    if offer["result_payload_opened"]:
        raise ValueError("result was opened before prediction freeze")

    frozen_objects = []
    for obj in offer["objects"]:
        months = exact_month_set(obj["delivery_period"])
        common = {
            "object_id": obj["object_id"],
            "product": obj["product"],
            "measurement_standard": obj["quality_and_measurement_standard"],
            "delivery_period": obj["delivery_period"],
            "calendar_phase": phase_label(months),
            "destination_at_offer": None,
        }
        price_targets = []
        for price_class in obj["price_classes"]:
            price_targets.append(
                {
                    "diameter_or_class": price_class["diameter_or_class"],
                    "starting_price_eur_m3": price_class["starting_price_eur_m3"],
                    "comparability": "ABSTAIN_NOT_COMPARABLE_PRICE_NO_DESTINATION_AT_OFFER",
                    "M0": "NOT_ESTIMABLE_M0_NO_PRIOR_LOCAL_OBSERVATION",
                    "M1": "NOT_ESTIMABLE_M1_SUPPORT",
                    "M2": "NOT_ESTIMABLE_M1_REQUIRED",
                    "BMA": "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT",
                }
            )
        volume_state = (
            "NOT_ESTIMABLE_SOURCE_VOLUME_DISAGREEMENT"
            if not obj["location_total_matches"]
            else "NOT_ESTIMABLE_M0_NO_PRIOR_LOCAL_OBSERVATION"
        )
        frozen_objects.append(
            {
                **common,
                "advertised_volume_m3": obj["advertised_volume_m3"],
                "location_sheet_total_m3": obj["location_sheet_total_m3"],
                "volume_source_state": volume_state,
                "volume_predictions": {
                    "M0": "NOT_ESTIMABLE_M0_NO_PRIOR_LOCAL_OBSERVATION",
                    "M1": "NOT_ESTIMABLE_M1_SUPPORT",
                    "M2": "NOT_ESTIMABLE_M1_REQUIRED",
                    "BMA": "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT",
                },
                "price_targets": price_targets,
            }
        )

    freeze = {
        "schema_version": "bpm.rmk.event-freeze.v0.1",
        "campaign_id": "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
        "event_date": offer["event_date"],
        "state": "FREEZE_WRITTEN_RESULT_STILL_CLOSED",
        "inputs_sha256": {
            "raw_offer": sha256(args.raw),
            "structured_offer": sha256(args.offer),
            "prior": sha256(args.prior),
            "software_addendum": sha256(args.software),
        },
        "historical_2023_2024_model_observations": 0,
        "object_count": len(frozen_objects),
        "price_target_count": sum(len(obj["price_targets"]) for obj in frozen_objects),
        "advertised_volume_m3": offer["advertised_volume_m3"],
        "source_inconsistencies": [
            {
                "object_id": obj["object_id"],
                "offer_volume_m3": obj["advertised_volume_m3"],
                "location_sheet_volume_m3": obj["location_sheet_total_m3"],
                "state": "NOT_ESTIMABLE_SOURCE_VOLUME_DISAGREEMENT",
            }
            for obj in offer["objects"]
            if not obj["location_total_matches"]
        ],
        "frozen_objects": frozen_objects,
        "result": {
            "url": "https://rmk.ee/wp-content/uploads/2025/03/EdukadEP_26.02.2025.xlsx",
            "body_opened": False,
            "opening_authorized_only_after_this_freeze_is_hashed": True,
        },
        "global_winner": None,
        "automatic_promotion": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "objects": freeze["object_count"],
                "price_targets": freeze["price_target_count"],
                "source_inconsistencies": len(freeze["source_inconsistencies"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
