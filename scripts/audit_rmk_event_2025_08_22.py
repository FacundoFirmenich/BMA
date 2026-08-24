from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-08-22"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-06-26/closure/prior_after_2025-06-26.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_EP_22.08.2025.xlsx"
result_raw = EVENT / "raw/Edukad_EP_22.08.2025.xlsx"
offer_path = EVENT / "structured/offer_structured.json"
result_path = EVENT / "structured/result.json"
repair_path = EVENT / "structured/RESULT_NULL_DENOMINATOR_REPAIR_RECEIPT.json"
freeze_path = EVENT / "freeze/freeze.json"
closure = EVENT / "closure"
scoring_path = closure / "local_scoring.json"
adjudication_path = closure / "adjudication.json"
posterior_path = closure / "prior_after_2025-08-22.json"
z_path = closure / "z_post_2025-08-22.json"

offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
repair, scoring, adjudication = load(repair_path), load(scoring_path), load(adjudication_path)
posterior, z_post = load(posterior_path), load(z_path)

require(digest(offer_raw) == "809F526D46E89F7D9CC6BDA658D616E93DA8B1A119AB8E47D103308D0B5DEC72", "offer raw hash")
require(digest(result_raw) == "37C1F8EE8B795B960207F5F2367B0879DA260034ABED9CA0D3AC5709F80B272E", "result raw hash")
require(digest(freeze_path) == "48881C255660ECEB251CE9A1CF7E32B2FEA5CE1CDA34B34A8CF3C8DCA014D969", "freeze hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes result")
require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(offer_path), "offer link")
require(freeze["invalid_delivery_period_objects"] == [8, 9], "invalid periods frozen")
require(freeze["source_volume_conflict_objects"] == [2], "source conflict frozen")
require(freeze["objects_with_prior_base_cell_match"] == 8 and freeze["frozen_destination_predictions"] == 37, "freeze census")
require(all(len(item["frozen_local_predictions"]) == 0 for item in freeze["objects"] if item["object_id"] in (8, 9)), "invalid-period objects emit no predictions")
require(offer["object_count"] == 13 and offer["advertised_volume_m3"] == 44861, "offer census")
object2 = next(item for item in offer["objects"] if item["object_id"] == 2)
require(object2["location_component_sum_m3"] == 4340 and object2["location_sheet_total_m3"] == 4095, "object 2 source conflict quantities")
require(object2["location_volume_state"] == "SOURCE_EXACT_DUPLICATE_LOCATION_ROWS", "object 2 duplicate state")
require(len(object2["location_exact_duplicate_rows"]) == 3, "object 2 exact duplicate count")

require(result["award_row_count"] == 40 and result["local_outcome_count"] == 37, "result valid census")
require(result["quarantined_outcome_count"] == 2, "two quarantined outcomes")
require({item["object_id"] for item in result["quarantined_outcomes"]} == {8, 9}, "quarantined object identities")
require(all(item["state"] == "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY" for item in result["quarantined_outcomes"]), "quarantine reason")
require(result["total_awarded_volume_m3"] == 44861, "result volume")
require(not result["extraction_failures"], "result extraction has no failures")
require(result["freeze_used_sha256"] == digest(freeze_path), "result freeze link")
require(repair["discarded_unscored_structured_result_sha256"] == "741A9214546AFC99AC10861EB09992C4FFC29B7F112693B4BEC5A36ADA137AC3", "discarded result preserved")
require(repair["freeze_preserved_sha256"] == digest(freeze_path), "repair preserves freeze")
for object_id in (10, 11, 12, 13):
    item = next(value for value in result["object_totals"] if value["object_id"] == object_id)
    require(item["coverage_offer_denominator"] == 1 and item["coverage_location_sheet_denominator"] is None, f"object {object_id} null total coverage")

frozen_keys = {
    (item["object_id"], prediction["destination"])
    for item in freeze["objects"]
    for prediction in item["frozen_local_predictions"]
}
outcome_keys = {(item["object_id"], item["destination"]) for item in result["local_outcomes"]}
score_keys = {(item["object_id"], item["destination"]) for item in scoring["local_scores"]}
require(score_keys == frozen_keys & outcome_keys, "scores equal exact frozen-result intersection")
require(scoring["scored_exact_destination_predictions"] == 18, "eighteen scored predictions")
require(scoring["non_observed_or_unawarded_predictions"] == 19, "nineteen preserved non-observations")
require(all(item["object_id"] not in (8, 9) for item in scoring["local_scores"]), "quarantined outcomes never scored")
require(all(item["state"] == "NOT_OBSERVED_EXACT_DESTINATION_OUTCOME" for item in scoring["non_observed"]), "non-observed destinations preserved")
price_errors = [item["price"]["absolute_error_eur_m3"] for item in scoring["local_scores"]]
volume_errors = [item["volume"]["absolute_log_error"] for item in scoring["local_scores"]]
require(math.isclose(scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"], statistics.fmean(price_errors), rel_tol=0, abs_tol=1e-12), "price MAE recomputation")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_volume_MALE"], statistics.fmean(volume_errors), rel_tol=0, abs_tol=1e-12), "volume MALE recomputation")
require(scoring["diagnostic_aggregate"]["M0_price_median_absolute_error_eur_m3"] == statistics.median(price_errors), "price median recomputation")
require(scoring["diagnostic_aggregate"]["comparison_model"] is None and scoring["global_winner"] is None, "no global or pairwise winner")
require(scoring["density_scores"].startswith("NOT_ESTIMABLE"), "density scores abstain")
require(all(item["price"]["M1_state"] == "NOT_ESTIMABLE_M1_SUPPORT" for item in scoring["local_scores"]), "M1 abstentions")
require(all(item["price"]["M2_state"] == "NOT_ESTIMABLE_SEASONAL_SUPPORT" for item in scoring["local_scores"]), "M2 abstentions")
require(all(item["price"]["BMA_state"] == "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT" for item in scoring["local_scores"]), "BMA abstentions")

require(adjudication["local_scoring_sha256"] == digest(scoring_path), "adjudication scoring link")
require(adjudication["objects_full_coverage"] == [1, 3, 4, 5, 6, 7, 10, 11, 12, 13], "full valid objects")
require(adjudication["objects_partial_coverage"] == [] and adjudication["objects_over_coverage"] == [], "no partial or over coverage")
require(adjudication["unawarded_objects"] == [], "no unawarded objects")
not_estimable = {item["object_id"]: item["state"] for item in adjudication["not_estimable_source_objects"]}
require(not_estimable == {2: "NOT_ESTIMABLE_SOURCE_VOLUME_UNVERIFIED_OR_DISAGREEMENT", 8: "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY", 9: "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY"}, "not-estimable source objects")
require({item["object_id"] for item in adjudication["quarantined_outcomes"]} == {8, 9}, "quarantine propagated")
require(adjudication["updated_prior_cells"] == 18 and adjudication["new_local_cells"] == 19, "posterior update partition")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["local_cell_count"] == 212 and posterior["posterior_observation_count"] == 470, "posterior accumulation")
require(sum(len(cell["price"]["observations"]) == 2 for cell in posterior["local_cells"].values()) == 23, "twenty-three cells have two observations")
require(sum(len(cell["price"]["observations"]) >= 3 for cell in posterior["local_cells"].values()) == 0, "M1 still unsupported")
kase_heltermaa = [cell for cell in posterior["local_cells"].values() if cell["descriptor"]["product"] == "Kasepaberipuit" and cell["descriptor"]["destination"] == "Heltermaa"]
require(len(kase_heltermaa) == 1 and len(kase_heltermaa[0]["price"]["observations"]) == 1, "invalid object 9 did not update posterior")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "posterior no reset or pooling")
require(z_post["reset_occurred"] is False and z_post["pooling_occurred"] is False, "Z_post no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no global winner or promotion")

paths = [offer_raw, result_raw, offer_path, result_path, repair_path, freeze_path, scoring_path, adjudication_path, posterior_path, z_path]
manifest = {
    "schema_version": "bpm.rmk.event-manifest.v0.4",
    "event": "2025-08-22",
    "files": [
        {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
        for path in paths
    ],
}
manifest_path = closure / "MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {
    "schema_version": "bpm.rmk.event-audit.v0.4",
    "event": "2025-08-22",
    "status": "PASS",
    "checks": len(checks),
    "failures": [],
    "manifest_sha256": digest(manifest_path),
}
(closure / "AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
