"""Apply a pre-result policy that quarantines outcomes lacking class weights."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_FAILURE = "NOT_ESTIMABLE_PRICE_ENCODING_OR_MISSING_OFFER_WEIGHTS"
QUARANTINE_STATE = "NOT_ESTIMABLE_UNWEIGHTED_MULTICLASS_PRICE"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    probe, policy = load(args.probe), load(args.policy)
    if probe["event_date"] != policy["event_date"]:
        raise ValueError("event date mismatch")
    if policy["state"] != "FROZEN_BEFORE_RESULT_BODY_OPEN":
        raise ValueError("policy was not frozen before result")
    failures = list(probe["extraction_failures"])
    if any(item.get("state") != EXPECTED_FAILURE for item in failures):
        raise ValueError("unexpected extraction failure cannot be repaired")

    retained = []
    moved = []
    for outcome in probe["local_outcomes"]:
        if outcome["price_state"] == "NOT_ESTIMABLE_PARTIAL_PRICE_SUPPORT":
            moved.append({**outcome, "state": QUARANTINE_STATE})
        else:
            if outcome["effective_weighted_price_eur_m3"] is None:
                raise ValueError("null price outside governed quarantine")
            retained.append(outcome)

    repaired = json.loads(json.dumps(probe))
    repaired["schema_version"] = "bpm.rmk.result-structured.v0.6"
    repaired["parent_probe_sha256"] = digest(args.probe)
    repaired["pre_result_policy_sha256"] = digest(args.policy)
    repaired["unweighted_multiclass_price_failures"] = failures
    repaired["extraction_failures"] = []
    repaired["local_outcomes"] = retained
    repaired["local_outcome_count"] = len(retained)
    repaired["quarantined_outcomes"] = list(probe["quarantined_outcomes"]) + moved
    repaired["quarantined_outcome_count"] = len(repaired["quarantined_outcomes"])
    repaired["post_result_repair"] = {
        "scope": "UNWEIGHTED_MULTICLASS_PRICE_ONLY",
        "moved_local_outcomes_to_quarantine": len(moved),
        "preserved_raw_rows": len(repaired["rows"]),
        "posterior_update_occurred_before_repair": False,
        "predictions_changed": False,
    }

    args.output.write_text(json.dumps(repaired, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "local_outcomes": len(retained),
        "quarantined_outcomes": len(repaired["quarantined_outcomes"]),
        "moved_unweighted_outcomes": len(moved),
        "original_failures_preserved": len(failures),
    }, indent=2))


if __name__ == "__main__":
    main()
