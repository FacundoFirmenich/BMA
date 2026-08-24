from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-06-26"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-05-06/closure/prior_after_2025-05-06.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_EP_26.06.2025.xlsx"
result_raw = EVENT / "raw/Edukad_EP_26.06.2025.xlsx"
offer_path = EVENT / "structured/offer_structured.json"
result_path = EVENT / "structured/result.json"
freeze_path = EVENT / "freeze/freeze.json"
closure = EVENT / "closure"
scoring_path = closure / "local_scoring.json"
adjudication_path = closure / "adjudication.json"
posterior_path = closure / "prior_after_2025-06-26.json"
z_path = closure / "z_post_2025-06-26.json"

offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
scoring, adjudication = load(scoring_path), load(adjudication_path)
posterior, z_post = load(posterior_path), load(z_path)

require(digest(offer_raw) == "F075A37E41725A6D98585A513FC8ECCBA7FFA6F5C31BA31D9EFC077DA7B8B02E", "offer raw hash")
require(digest(result_raw) == "60F7A4E63008FD69E16B3985308511807D0D096ECEF63DD2F3FE9CE366F79FA9", "result raw hash")
require(digest(freeze_path) == "67066097104EE8583764CFC780AC8E52FFB1B9358811F88C45036E87B2F198DB", "freeze hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes result")
require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(offer_path), "offer link")
require(freeze["objects_with_prior_base_cell_match"] == 6, "six matching products")
require(freeze["frozen_destination_predictions"] == 15, "fifteen frozen destinations")
require(freeze["paired_result"]["body_opened"] is False, "freeze records closed result")
require(offer["object_count"] == 9 and offer["advertised_volume_m3"] == 106007, "offer census")
require(offer["all_location_totals_match"] is True, "offer location totals")
require(all(len({entry["diameter_or_class"] for entry in item["price_classes"]}) == len(item["price_classes"]) for item in offer["objects"]), "measurement classes unique")
require(result["award_row_count"] == 37 and result["local_outcome_count"] == 23, "result census")
require(result["total_awarded_volume_m3"] == 90109, "result volume")
require(not result["extraction_failures"], "result extraction has no failures")
require(result["quarantined_unpaired_result"] is None, "no unrelated quarantine injected")

score_keys = {(item["object_id"], item["destination"]) for item in scoring["local_scores"]}
expected_keys = {(1, "Ninase"), (2, "Ninase"), (4, "Roomassaare"), (5, "Roomassaare"), (6, "Roomassaare")}
require(score_keys == expected_keys, "exact scored-cell jurisdiction")
require(scoring["scored_exact_destination_predictions"] == 5, "five scored predictions")
require(scoring["non_observed_or_unawarded_predictions"] == 10, "ten preserved abstentions")
require(sum(item["state"] == "UNAWARDED_OBJECT_NO_POSITIVE_OUTCOME" for item in scoring["non_observed"]) == 1, "unawarded state preserved")
require(all("Pärnu sadam" != item["destination"] for item in scoring["local_scores"]), "no post-result harbor-name normalization")

roomassaare_manni = next(item for item in scoring["local_scores"] if item["object_id"] == 6)
expected_weighted_price = (1700 * 55 + 1639 * 57.45) / 3339
require(math.isclose(roomassaare_manni["price"]["actual_eur_m3"], expected_weighted_price, rel_tol=0, abs_tol=1e-12), "Roomassaare price volume weighting")
price_errors = [item["price"]["absolute_error_eur_m3"] for item in scoring["local_scores"]]
volume_errors = [item["volume"]["absolute_log_error"] for item in scoring["local_scores"]]
require(math.isclose(scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"], statistics.fmean(price_errors), rel_tol=0, abs_tol=1e-12), "price MAE recomputation")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_volume_MALE"], statistics.fmean(volume_errors), rel_tol=0, abs_tol=1e-12), "volume MALE recomputation")
require(scoring["diagnostic_aggregate"]["comparison_model"] is None and scoring["global_winner"] is None, "no global or pairwise winner")
require(scoring["density_scores"].startswith("NOT_ESTIMABLE"), "density scores abstain")
require(all(item["price"]["M1_state"] == "NOT_ESTIMABLE_M1_SUPPORT" for item in scoring["local_scores"]), "M1 abstentions")
require(all(item["price"]["M2_state"] == "NOT_ESTIMABLE_SEASONAL_SUPPORT" for item in scoring["local_scores"]), "M2 abstentions")
require(all(item["price"]["BMA_state"] == "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT" for item in scoring["local_scores"]), "BMA abstentions")

require(adjudication["local_scoring_sha256"] == digest(scoring_path), "adjudication scoring link")
require(adjudication["objects_full_coverage"] == [4, 5, 6, 8, 9], "full objects")
require(adjudication["objects_partial_coverage"] == [1, 2, 7], "partial objects")
require(adjudication["objects_over_coverage"] == [], "no over-coverage")
require(adjudication["unawarded_objects"] == [3], "unawarded object")
require(adjudication["updated_prior_cells"] == 5 and adjudication["new_local_cells"] == 18, "posterior update partition")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["local_cell_count"] == 193 and posterior["posterior_observation_count"] == 396, "posterior accumulation")
require(sum(len(cell["price"]["observations"]) == 2 for cell in posterior["local_cells"].values()) == 5, "five cells have second observation")
require(sum(len(cell["price"]["observations"]) >= 3 for cell in posterior["local_cells"].values()) == 0, "M1 still unsupported")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "posterior no reset or pooling")
require(z_post["reset_occurred"] is False and z_post["pooling_occurred"] is False, "Z_post no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no global winner or promotion")

paths = [offer_raw, result_raw, offer_path, result_path, freeze_path, scoring_path, adjudication_path, posterior_path, z_path]
manifest = {
    "schema_version": "bpm.rmk.event-manifest.v0.3",
    "event": "2025-06-26",
    "files": [
        {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
        for path in paths
    ],
}
manifest_path = closure / "MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {
    "schema_version": "bpm.rmk.event-audit.v0.3",
    "event": "2025-06-26",
    "status": "PASS",
    "checks": len(checks),
    "failures": [],
    "manifest_sha256": digest(manifest_path),
}
(closure / "AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
