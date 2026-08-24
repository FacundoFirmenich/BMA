from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-10-29"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-10-21/closure/prior_after_2025-10-21.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_EP_29.10.2025.xlsx"
result_raw = EVENT / "raw/Edukad-EP-29.10.2025.xlsx"
offer_path = EVENT / "structured/offer_structured.json"
invalid_result_path = EVENT / "structured/result_v0_3_invalid_do_not_close.json"
candidate_result_path = EVENT / "structured/result_v0_4_candidate.json"
result_path = EVENT / "structured/result.json"
freeze_v05_path = EVENT / "freeze/freeze_v0_5_superseded_pre_result.json"
freeze_wrong_url_path = EVENT / "freeze/freeze_v0_6_wrong_result_url_superseded.json"
freeze_path = EVENT / "freeze/freeze.json"
pre_result_gate_path = EVENT / "gates/pre_result_gate_v2.json"
conflict_gate_path = EVENT / "gates/source_volume_conflict_object_6.json"
url_correction_path = EVENT / "gates/result_url_month_correction.json"
weights_path = EVENT / "gates/offer_anchored_class_weights.json"
repair_path = EVENT / "gates/post_result_pre_scoring_extractor_repair.json"
source_amendment_path = ROOT / "preregistrations/BPM_RMK_SOURCE_VOLUME_GATE_PRECEDENCE_AMENDMENT_20260821.json"
extractor_path = ROOT / ".artifact_probe/extract_rmk_result_v0_4.mjs"
result_test_path = ROOT / "scripts/test_rmk_result_v04_2025_10_29.py"
closure = EVENT / "closure"
scoring_path = closure / "local_scoring.json"
adjudication_path = closure / "adjudication.json"
posterior_path = closure / "prior_after_2025-10-29.json"
z_path = closure / "z_post_2025-10-29.json"

offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
previous, scoring, adjudication = load(PREVIOUS), load(scoring_path), load(adjudication_path)
posterior, z_post = load(posterior_path), load(z_path)
gate, weights, repair = load(pre_result_gate_path), load(weights_path), load(repair_path)

require(digest(offer_raw) == "2BE85C38B126DC1A595C473C5310195D59961EB9B5888921501775A76E409F8B", "offer raw hash")
require(digest(result_raw) == "1620F40B4BD2ACDCE86765D02EFDD57F8A20485BE7F064006EDF7C6589B47A67", "result raw hash")
require(digest(offer_path) == "3117929C51B3666A0710A7C123EC51F5F0D20025204A4E6C0080E9A90FE934BD", "structured offer hash")
require(digest(invalid_result_path) == "139C50EC5BE0A10319C73508CF56C6C37D07F4BB634B85F96E75071F295CA573", "invalid extraction preserved")
require(digest(candidate_result_path) == digest(result_path) == "928100550E6CA04901F2A3B61262668A6423D13661E158D01C42D3031B127BE1", "canonical result byte identity")
require(digest(freeze_v05_path) == "E5D3D2246FACF20A1DF5ABCDDA77E851577396259A1416707DEDA4818F07DDA2", "v0.5 freeze preserved")
require(digest(freeze_wrong_url_path) == "3004466F1BDBD946DAB021FD2B9F6A62FA090864029B02E779EA6DD312194920", "wrong-url freeze preserved")
require(digest(freeze_path) == "5407C7504D3D7C2F44BC9572A215CCE6247681E1F651884D28622C51D496B635", "active freeze hash")
require(digest(pre_result_gate_path) == "A2F3CFFC3B73B94C4F2446E80A199A6C1B2CB69964893D118F60AF930F2FC787", "pre-result gate hash")
require(digest(conflict_gate_path) == "D62172819B0713923ECF40F25A3EE636DDBD9546C502099313D105B2488C1EC2", "source conflict gate hash")
require(digest(url_correction_path) == "D4CA1C66F6961BC232C7917E30A6C48D34DBC5159EC9BB07A09961F22C04938D", "URL correction hash")
require(digest(weights_path) == "453BCA6A8E189C21266CD461E9C81E9BA06C53F7005E885B798FC1DA093A2BC3", "offer weights hash")
require(digest(repair_path) == "53BC4D8C69CA2275220D9D18406615455125E40BED480D671642F5F869FBDC83", "extractor repair receipt hash")
require(digest(extractor_path) == "E472C53DD38719617AD7D31E4E6161A3ABC2C618CA8FD71D01A795B65A7102F0", "extractor v0.4 hash")
require(digest(result_test_path) == "E37BC418F455A068C3BE376402C94151E65973CE5FEA113FB7A30735AD11D78B", "result regression test hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "active freeze precedes result")
require(gate["active_freeze_v0_6_sha256"] == digest(freeze_path), "gate active freeze link")
require(gate["result_pairing"]["selected"]["url"] == freeze["paired_result"]["url"], "corrected result URL link")
require(gate["result_pairing"]["unmatched_candidate"]["body_opened"] is False, "unpaired candidate remains unopened")
require(repair["causal_position"] == "RESULT_OPENED_BUT_NO_SCORING_OR_POSTERIOR_UPDATE_WRITTEN", "repair boundary recorded")

require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "freeze prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(offer_path), "freeze offer link")
require(freeze["schema_version"] == "bpm.rmk.event-freeze.v0.6", "active freezer schema")
require(freeze["invalid_delivery_period_objects"] == [] and freeze["source_volume_conflict_objects"] == [6], "offer gate census")
require(freeze["objects_with_prior_base_cell_match"] == 9 and freeze["frozen_destination_predictions"] == 52, "freeze census")
require(all(not item["frozen_local_predictions"] for item in freeze["objects"] if item["object_id"] == 6), "conflicted object has no predictions")
require(next(item for item in freeze["objects"] if item["object_id"] == 6)["no_match_state"] == "NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT", "conflict reason precedence")
require(freeze["M1_price_estimable_predictions"] == freeze["M1_volume_estimable_predictions"] == 0, "M1 abstains pre-result")
require(freeze["M2_price_estimable_predictions"] == freeze["M2_volume_estimable_predictions"] == 0, "M2 abstains pre-result")
require(offer["object_count"] == 17 and offer["advertised_volume_m3"] == 83012, "offer census")
require(sum(item["location_total_matches"] for item in offer["objects"]) == 16, "sixteen verified offer volumes")
require(next(item for item in offer["objects"] if item["object_id"] == 6)["location_sheet_total_m3"] == 5549, "conflicting location total preserved")
require(next(item for item in offer["objects"] if item["object_id"] == 6)["advertised_volume_m3"] == 4686, "conflicting advertised total preserved")

require(result["schema_version"] == "bpm.rmk.result-structured.v0.4", "result schema")
require(result["award_row_count"] == 72 and result["local_outcome_count"] == 62, "result census")
require(result["quarantined_outcome_count"] == 10 and {item["object_id"] for item in result["quarantined_outcomes"]} == {6}, "source outcomes quarantined")
require(all(item["state"] == "NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT" for item in result["quarantined_outcomes"]), "quarantine reason preserved")
require(result["total_awarded_volume_m3"] == 81298, "result volume")
require(not result["extraction_failures"], "result extraction has no failures")
require(result["freeze_used_sha256"] == digest(freeze_path), "result freeze link")
require(sum(row["price_state"] == "ESTIMABLE_OFFER_WEIGHTED_CLASS_PRICE" for row in result["rows"]) == 13, "thirteen offer-weighted price rows")
require(all(math.isclose(sum(values), 1.0, rel_tol=0, abs_tol=1e-12) for values in weights["weights_by_object"].values()), "offer weights sum to one")
require(all(row["product"] == next(item["product"] for item in offer["objects"] if item["object_id"] == row["object_id"]) for row in result["rows"]), "offer product remains canonical")

frozen_keys = {(item["object_id"], prediction["destination"]) for item in freeze["objects"] for prediction in item["frozen_local_predictions"]}
outcome_keys = {(item["object_id"], item["destination"]) for item in result["local_outcomes"]}
score_keys = {(item["object_id"], item["destination"]) for item in scoring["local_scores"]}
require(score_keys == frozen_keys & outcome_keys, "scores equal exact frozen-result intersection")
require(len(score_keys) == 25 and scoring["non_observed_or_unawarded_predictions"] == 27, "score and abstention census")
require(all(item["state"] == "NOT_OBSERVED_EXACT_DESTINATION_OUTCOME" for item in scoring["non_observed"]), "non-observations preserved")
require(scoring["M1_price_scored_predictions"] == scoring["M1_volume_scored_predictions"] == 0, "no M1 score invented")
price_errors = [item["price"]["M0"]["absolute_error_eur_m3"] for item in scoring["local_scores"]]
volume_errors = [item["volume"]["M0"]["absolute_log_error"] for item in scoring["local_scores"]]
require(math.isclose(scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"], statistics.fmean(price_errors), rel_tol=0, abs_tol=1e-12), "price MAE recomputation")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_price_median_absolute_error_eur_m3"], statistics.median(price_errors), rel_tol=0, abs_tol=1e-12), "price median recomputation")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_volume_MALE"], statistics.fmean(volume_errors), rel_tol=0, abs_tol=1e-12), "volume MALE recomputation")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_volume_median_absolute_log_error"], statistics.median(volume_errors), rel_tol=0, abs_tol=1e-12), "volume median recomputation")
require(scoring["global_winner"] is None and scoring["diagnostic_aggregate"]["global_winner"] is None, "no global winner")
require(scoring["density_scores"] == "PARTIAL_MODEL_LOCAL_ONLY_NO_COMMON_M0_M1_M2_SUPPORT", "density comparison abstains")

require(adjudication["updated_prior_cells"] == 25 and adjudication["new_local_cells"] == 37, "posterior update partition")
require(adjudication["not_estimable_source_objects"] == [{"object_id": 6, "state": "NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT"}], "source conflict adjudication")
require(len(adjudication["quarantined_outcomes"]) == 10, "quarantine survives closure")
require(previous["local_cell_count"] == 237 and previous["posterior_observation_count"] == 536, "parent prior census")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["adjudication_sha256"] == digest(adjudication_path), "posterior adjudication link")
require(posterior["local_cell_count"] == 274 and posterior["posterior_observation_count"] == 660, "posterior accumulation")
require(sum(cell.get("observation_events", []).count("2025-10-29") for cell in posterior["local_cells"].values()) == 62, "sixty-two local outcomes batch-recorded")
require(all("2025-10-29" not in cell["price"].get("m1_innovation_events", []) for cell in posterior["local_cells"].values()), "no unscored M1 innovation")
require(sum(len(cell["price"]["observations"]) == 3 for cell in posterior["local_cells"].values()) == 14, "fourteen M1-supported cells")
require(sum(len(cell["price"]["observations"]) == 2 for cell in posterior["local_cells"].values()) == 28, "twenty-eight two-observation cells")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(sum(cell["price"]["M1"]["state"] == "ESTIMABLE" for cell in z_post["cells"].values()) == 14, "Z_post exposes fourteen M1 price cells")
require(sum(cell["price"]["M2"]["state"] == "ESTIMABLE_FOR_LISTED_PHASES" for cell in z_post["cells"].values()) == 0, "Z_post exposes no premature M2 cells")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "posterior no reset or pooling")
require(z_post["reset_occurred"] is False and z_post["pooling_occurred"] is False, "Z_post no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no global winner or promotion")

paths = [offer_raw, result_raw, offer_path, invalid_result_path, result_path, freeze_v05_path, freeze_wrong_url_path, freeze_path, pre_result_gate_path, conflict_gate_path, url_correction_path, weights_path, repair_path, source_amendment_path, extractor_path, result_test_path, scoring_path, adjudication_path, posterior_path, z_path]
manifest = {
    "schema_version": "bpm.rmk.event-manifest.v0.7",
    "event": "2025-10-29",
    "files": [{"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)} for path in paths],
}
manifest_path = closure / "MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {
    "schema_version": "bpm.rmk.event-audit.v0.7",
    "event": "2025-10-29",
    "status": "PASS",
    "checks": len(checks),
    "failures": [],
    "manifest_sha256": digest(manifest_path),
}
(closure / "AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
