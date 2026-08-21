"""Verify stocklot offers whose explicit location replaces a component sheet."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


STATE = "VERIFIED_ADVERTISED_STOCKLOT_NO_COMPONENT_SHEET"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--object-ids", required=True, nargs="+", type=int)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    eligible = set(args.object_ids)
    changed = []
    for item in payload["objects"]:
        if item["object_id"] not in eligible:
            continue
        if "LAOKAUP" not in item["quality_and_measurement_standard"].upper():
            raise ValueError(f"object {item['object_id']} is not a stocklot")
        if not item["advertised_region"] or item["advertised_volume_m3"] <= 0:
            raise ValueError(f"object {item['object_id']} lacks explicit location or volume")
        if item["location_sheet_total_m3"] is not None or item["location_component_sum_m3"] is not None:
            raise ValueError(f"object {item['object_id']} unexpectedly has component-sheet values")
        item["location_volume_state"] = STATE
        item["location_total_matches"] = True
        changed.append(item["object_id"])
    if changed != sorted(eligible):
        raise ValueError("eligible object set mismatch")
    payload["all_location_totals_match"] = all(item["location_total_matches"] for item in payload["objects"])
    payload["stocklot_location_semantics_repair"] = {
        "changed_object_ids": changed,
        "advertised_volumes_changed": False,
        "component_values_imputed": False,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["stocklot_location_semantics_repair"], indent=2))


if __name__ == "__main__":
    main()
