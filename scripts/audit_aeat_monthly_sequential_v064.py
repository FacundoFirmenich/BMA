#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

from bma.custody import canonical_bytes, sha256_bytes, sha256_file, verify_manifest


def read_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def weighted(rows: list[dict[str, Any]], n_key: str, value_key: str) -> float:
    total = sum(int(row[n_key]) for row in rows)
    return sum(int(row[n_key]) * float(row[value_key]) for row in rows) / total


def audit(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    manifest = verify_manifest(root)
    if manifest["status"] != "PASS":
        failures.append("MANIFEST_FAIL")
    expected_counts = {
        "structured_months": 12,
        "freezes": 11,
        "adjudications": 11,
        "priors": 11,
        "z_post": 11,
    }
    counts = {
        name: len(list((root / name).glob("*")))
        for name in expected_counts
    }
    if counts != expected_counts:
        failures.append("ARTIFACT_COUNTS_FAIL")
    result = json.loads((root / "RESULT.json").read_text(encoding="utf-8"))
    sequence = json.loads((root / "SEQUENCE.json").read_text(encoding="utf-8"))
    if result["transition_count"] != 11 or len(sequence) != 34:
        failures.append("SEQUENCE_LENGTH_FAIL")
    if result["sequence"] != sequence:
        failures.append("RESULT_SEQUENCE_DIVERGENCE")
    for target_month in range(2, 13):
        offset = 1 + (target_month - 2) * 3
        events = sequence[offset : offset + 3]
        target = f"2024-{target_month:02d}"
        training = f"2024-{target_month - 1:02d}"
        if [item["event"] for item in events] != [
            "FREEZE_WRITTEN",
            "TARGET_MONTH_OPENED_AND_STRUCTURED",
            "ADJUDICATION_AND_Z_POST_WRITTEN",
        ]:
            failures.append(f"EVENT_ORDER_FAIL:{target}")
        if events[0]["training_period"] != training or events[0]["target_period"] != target:
            failures.append(f"ONE_MONTH_CONTRACT_FAIL:{target}")
        freeze_path = root / "freezes" / f"freeze_{target}.json.gz"
        outcome_path = root / "structured_months" / f"month_{target}.json.gz"
        adjudication_path = root / "adjudications" / f"adjudication_{target}.json.gz"
        regime = "YEAR_END_UNCALIBRATED" if target_month == 12 else "ORDINARY"
        prior_path = root / "priors" / f"prior_after_{target}_{regime}.json.gz"
        z_path = root / "z_post" / f"z_post_{target}.json"
        freeze = read_gzip(freeze_path)
        adjudication = read_gzip(adjudication_path)
        posterior = read_gzip(prior_path)
        z_post = json.loads(z_path.read_text(encoding="utf-8"))
        if adjudication["freeze_sha256"] != sha256_file(freeze_path):
            failures.append(f"FREEZE_HASH_FAIL:{target}")
        if adjudication["outcome_sha256"] != sha256_file(outcome_path):
            failures.append(f"OUTCOME_HASH_FAIL:{target}")
        if posterior["adjudication_sha256"] != sha256_file(adjudication_path):
            failures.append(f"ADJUDICATION_HASH_FAIL:{target}")
        if z_post["future_prior_sha256"] != sha256_file(prior_path):
            failures.append(f"PRIOR_HASH_FAIL:{target}")
        if z_post["adjudication_sha256"] != sha256_file(adjudication_path):
            failures.append(f"Z_POST_ADJUDICATION_HASH_FAIL:{target}")
        if target_month >= 3:
            previous = f"2024-{target_month - 1:02d}"
            previous_regime = "ORDINARY"
            previous_path = root / "priors" / f"prior_after_{previous}_{previous_regime}.json.gz"
            previous_posterior = read_gzip(previous_path)
            expected_prior_hash = sha256_bytes(canonical_bytes({
                "quantity": previous_posterior["quantity_model"],
                "unit_value": previous_posterior["unit_value_model"],
                "participation": previous_posterior["participation_model"],
                "regime": regime,
            }))
            if freeze["prior_state_sha256"] != expected_prior_hash:
                failures.append(f"POSTERIOR_CARRY_FAIL:{target}")
    transitions = result["transitions"]
    summary = {
        "participation_bma_brier_micro": weighted(transitions, "participation_n", "participation_bma_brier"),
        "participation_control_brier_micro": weighted(transitions, "participation_n", "participation_origin_frozen_brier"),
        "quantity_bma_male_micro": weighted(transitions, "quantity_n", "quantity_bma_male"),
        "quantity_persistence_male_micro": weighted(transitions, "quantity_n", "quantity_persistence_male"),
        "unit_value_bma_male_micro": weighted(transitions, "unit_value_n", "unit_value_bma_male"),
        "unit_value_persistence_male_micro": weighted(transitions, "unit_value_n", "unit_value_persistence_male"),
        "participation_month_wins": sum(row["participation_bma_brier"] < row["participation_origin_frozen_brier"] for row in transitions),
        "participation_month_ties": sum(row["participation_bma_brier"] == row["participation_origin_frozen_brier"] for row in transitions),
        "quantity_month_wins": sum(row["quantity_bma_male"] < row["quantity_persistence_male"] for row in transitions),
        "unit_value_month_wins": sum(row["unit_value_bma_male"] < row["unit_value_persistence_male"] for row in transitions),
        "first_appearance_cells_sum": sum(int(row["first_appearance_cells"]) for row in transitions),
    }
    zip_files = [path.relative_to(root).as_posix() for path in root.rglob("*.zip")]
    if zip_files:
        failures.append("RAW_ZIP_PRESENT")
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "manifest": manifest,
        "counts": counts,
        "sequence_events": len(sequence),
        "summary": summary,
        "zip_files": zip_files,
        "derived_bytes": sum(path.stat().st_size for path in root.rglob("*") if path.is_file()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    report = audit(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
