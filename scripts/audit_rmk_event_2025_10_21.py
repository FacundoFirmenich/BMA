from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-10-21"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-10-07/closure/prior_after_2025-10-07.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_21.10.2025.xlsx"
result_raw = EVENT / "raw/Edukad_21.10.2025.xlsx"
offer_path = EVENT / "structured/offer_structured.json"
result_extracted_path = EVENT / "structured/result_structured.json"
result_path = EVENT / "structured/result.json"
freeze_path = EVENT / "freeze/freeze.json"
pre_result_gate_path = EVENT / "gates/pre_result_gate.json"
correction_path = ROOT / "preregistrations/BPM_RMK_BLANK_LOCATION_ROW_CORRECTION_20260821.json"
closure = EVENT / "closure"
scoring_path = closure / "local_scoring.json"
adjudication_path = closure / "adjudication.json"
posterior_path = closure / "prior_after_2025-10-21.json"
z_path = closure / "z_post_2025-10-21.json"

offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
gate, correction = load(pre_result_gate_path), load(correction_path)
previous, scoring, adjudication = load(PREVIOUS), load(scoring_path), load(adjudication_path)
posterior, z_post = load(posterior_path), load(z_path)

require(digest(offer_raw) == "FA84AA675EA4789B25F2F82DA735131000983F7B1EB5B4EAAB6EED20BFEFAC2A", "offer raw hash")
require(digest(result_raw) == "4AC3282CC42C9FD0112DA8E119E5084A5C95461A5338BD30038225537793C666", "result raw hash")
require(digest(offer_path) == "11356E2649A87FD897E71972387C199CAB8007728E481F14F4427DDD62D17C29", "structured offer hash")
require(digest(result_extracted_path) == digest(result_path) == "CA1AF9E22C97505B27A571057D8A3FE05E00934EC47DFE0D2157C8331AE30068", "result alias byte identity")
require(digest(freeze_path) == "566CC25637C0EB289D794BA3A4B97BDB7FC607B4E861BD56FEA805672AF9ECB8", "freeze hash")
require(digest(pre_result_gate_path) == "4DEBC02A86A39881DAFED67ED5930269B046B2886872BB8C91F76B6220F7F935", "pre-result gate hash")
require(digest(correction_path) == "7081B81265D7F5D5123FDECC7558D6505C475D4F6354EBE84381954E274E68EE", "pre-freeze correction hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes result")
require(gate["state"] == "FREEZE_HASHED_RESULT_BODY_CLOSED", "gate records closed result")
require(gate["freeze_sha256"] == digest(freeze_path), "gate freeze link")
require(gate["offer_extraction_correction_sha256"] == digest(correction_path), "gate correction link")
require(correction["causal_position"] == "RECORDED_AFTER_OFFER_ONLY_AND_BEFORE_FREEZE_OR_RESULT_ACCESS", "correction causal position")
require(correction["adverse_artifact"]["status"] == "SUPERSEDED_PRE_FREEZE_DO_NOT_USE", "bad pre-freeze artifact quarantined")

require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "freeze prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(offer_path), "freeze offer link")
require(freeze["invalid_delivery_period_objects"] == [] and freeze["source_volume_conflict_objects"] == [], "clean offer gates")
require(freeze["objects_with_prior_base_cell_match"] == 2 and freeze["frozen_destination_predictions"] == 14, "freeze census")
require({item["calendar_phase"] for item in freeze["objects"]} == {"M10-M11-M12"}, "phase parsing")
require(offer["object_count"] == 2 and offer["advertised_volume_m3"] == 33587, "offer census")
require(offer["all_location_totals_match"] is True, "all offer volumes verified")
require(all(not item["location_exact_duplicate_rows"] for item in offer["objects"]), "blank rows excluded from duplicates")

require(freeze["M1_price_estimable_predictions"] == freeze["M1_volume_estimable_predictions"] == 1, "one numeric M1 freeze")
require(freeze["M2_price_estimable_predictions"] == freeze["M2_volume_estimable_predictions"] == 0, "M2 abstains pre-result")
m1_frozen = [
    (item["object_id"], prediction["destination"])
    for item in freeze["objects"]
    for prediction in item["frozen_local_predictions"]
    if prediction["price"]["M1"].get("density_state") == "ESTIMABLE"
]
require(m1_frozen == [(2, "Paldiski")], "M1 frozen cell identity")

require(result["award_row_count"] == 10 and result["local_outcome_count"] == 7, "result census")
require(result["quarantined_outcome_count"] == 0 and result["quarantined_outcomes"] == [], "no quarantined outcomes")
require(result["total_awarded_volume_m3"] == 21645, "result volume")
require(not result["extraction_failures"], "result extraction has no failures")
require(result["freeze_used_sha256"] == digest(freeze_path), "result freeze link")

frozen_keys = {(item["object_id"], prediction["destination"]) for item in freeze["objects"] for prediction in item["frozen_local_predictions"]}
outcome_keys = {(item["object_id"], item["destination"]) for item in result["local_outcomes"]}
score_keys = {(item["object_id"], item["destination"]) for item in scoring["local_scores"]}
require(score_keys == frozen_keys & outcome_keys, "scores equal exact frozen-result intersection")
require(score_keys == {(1, "Paldiski sadam"), (1, "Pärnu"), (2, "Pärnu sadam")}, "three exact scored targets")
require(scoring["scored_exact_destination_predictions"] == 3 and scoring["non_observed_or_unawarded_predictions"] == 11, "score and abstention census")
require(all(item["state"] == "NOT_OBSERVED_EXACT_DESTINATION_OUTCOME" for item in scoring["non_observed"]), "destination non-observations preserved")
require((2, "Paldiski") in {(item["object_id"], item["destination"]) for item in scoring["non_observed"]}, "M1 target explicitly nonobserved")
require(scoring["M1_price_scored_predictions"] == scoring["M1_volume_scored_predictions"] == 0, "no M1 score invented")
price_errors = [item["price"]["M0"]["absolute_error_eur_m3"] for item in scoring["local_scores"]]
volume_errors = [item["volume"]["M0"]["absolute_log_error"] for item in scoring["local_scores"]]
require(math.isclose(scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"], statistics.fmean(price_errors), rel_tol=0, abs_tol=1e-12), "price MAE recomputation")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_volume_MALE"], statistics.fmean(volume_errors), rel_tol=0, abs_tol=1e-12), "volume MALE recomputation")
require(scoring["diagnostic_aggregate"]["global_winner"] is None and scoring["global_winner"] is None, "no global winner")
require(scoring["density_scores"] == "PARTIAL_MODEL_LOCAL_ONLY_NO_COMMON_M0_M1_M2_SUPPORT", "density comparison abstains")
require(all(item["price"]["BMA"]["state"] == "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT" for item in scoring["local_scores"]), "BMA abstentions")

require(adjudication["objects_full_coverage"] == [2] and adjudication["objects_partial_coverage"] == [1], "coverage partition")
require(adjudication["objects_over_coverage"] == [] and adjudication["unawarded_objects"] == [], "no over or unawarded objects")
require(adjudication["not_estimable_source_objects"] == [], "all sources adjudicable")
require(adjudication["updated_prior_cells"] == 3 and adjudication["new_local_cells"] == 4, "posterior update partition")
require(previous["local_cell_count"] == 233 and previous["posterior_observation_count"] == 522, "parent prior census")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["adjudication_sha256"] == digest(adjudication_path), "posterior adjudication link")
require(posterior["local_cell_count"] == 237 and posterior["posterior_observation_count"] == 536, "posterior accumulation")
require(sum(cell.get("observation_events", []).count("2025-10-21") for cell in posterior["local_cells"].values()) == 7, "seven outcomes batch-recorded")
require(all("2025-10-21" not in cell["price"].get("m1_innovation_events", []) for cell in posterior["local_cells"].values()), "no unscored M1 innovation")
require(sum(len(cell["price"]["observations"]) == 3 for cell in posterior["local_cells"].values()) == 2, "two M1-supported cells retained")
require(sum(len(cell["price"]["observations"]) == 2 for cell in posterior["local_cells"].values()) == 27, "twenty-seven cells have two observations")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(sum(cell["price"]["M1"]["state"] == "ESTIMABLE" for cell in z_post["cells"].values()) == 2, "Z_post exposes two M1 price cells")
require(sum(cell["price"]["M2"]["state"] == "ESTIMABLE_FOR_LISTED_PHASES" for cell in z_post["cells"].values()) == 0, "Z_post exposes no premature M2 cells")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "posterior no reset or pooling")
require(z_post["reset_occurred"] is False and z_post["pooling_occurred"] is False, "Z_post no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no global winner or promotion")

paths = [offer_raw, result_raw, offer_path, result_extracted_path, result_path, freeze_path, pre_result_gate_path, correction_path, scoring_path, adjudication_path, posterior_path, z_path]
manifest = {
    "schema_version": "bpm.rmk.event-manifest.v0.6",
    "event": "2025-10-21",
    "files": [{"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)} for path in paths],
}
manifest_path = closure / "MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {
    "schema_version": "bpm.rmk.event-audit.v0.6",
    "event": "2025-10-21",
    "status": "PASS",
    "checks": len(checks),
    "failures": [],
    "manifest_sha256": digest(manifest_path),
}
(closure / "AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
