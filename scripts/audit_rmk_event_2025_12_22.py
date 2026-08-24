from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-12-22"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-12-05/closure/prior_after_2025-12-05.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_EP_22.12.2025.xlsx"
result_raw = EVENT / "raw/Edukad_EP_22.12.2025.xlsx"
offer_path = EVENT / "structured/offer_structured.json"
result_path = EVENT / "structured/result.json"
pre_offer_path = EVENT / "gates/pre_offer_2025-12-22.json"
gate_path = EVENT / "gates/pre_result_gate.json"
freeze_path = EVENT / "freeze/freeze.json"
extractor_path = ROOT / ".artifact_probe/extract_rmk_result_v0_5.mjs"
scoring_path = EVENT / "closure/local_scoring.json"
adjudication_path = EVENT / "closure/adjudication.json"
posterior_path = EVENT / "closure/prior_after_2025-12-22.json"
z_path = EVENT / "closure/z_post_2025-12-22.json"

offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
previous, scoring = load(PREVIOUS), load(scoring_path)
adjudication, posterior, z_post = load(adjudication_path), load(posterior_path), load(z_path)

require(digest(pre_offer_path) == "281E56040522B59B49A29117BCCE0B023E958332D9347BB9F94271AEFFADAA9A", "pre-offer gate hash")
require(digest(offer_raw) == "541B7E4CA45A34183901C2FE19519A7A1207DC500506B19C9815E395AB534C42", "offer raw hash")
require(digest(offer_path) == "3EDAB2E900E638919BB6150C56D4C47B22457A190848A3E234CCF176350CCBD7", "structured offer hash")
require(digest(freeze_path) == "18C528F8D3031A33B5962D19D2DF8B54C5773B4A556D4701C11BD833D7A366D1", "freeze hash")
require(digest(gate_path) == "ABEC177293B0FD3DDEAB4521A76850EFC2C14C35520B5974E34E78CC2B4614A4", "pre-result gate hash")
require(digest(result_raw) == "3D7C83393787217A0DE1B7B69F01365983E56CAB4A38172595C28B09393185CA", "result raw hash")
require(digest(result_path) == "2976663D39BA0ADAA725DB9BAF6285A6789C3B911C355E6061C20B1A56BE594D", "structured result hash")
require(digest(extractor_path) == "16BF1D69C4D37EBFBC3ED7B4893C8962C6B6E6F1BD7F3E7D1E0458B3C02030BB", "extractor v0.5 hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes result")

require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "freeze prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(offer_path), "freeze offer link")
require(result["freeze_used_sha256"] == digest(freeze_path), "result freeze link")
require(result["structured_offer_used_sha256"] == digest(offer_path), "result offer link")
require(offer["object_count"] == 14 and offer["advertised_volume_m3"] == 114085, "offer census")
require(offer["all_location_totals_match"] is True, "all location totals verified")
require(all(item["location_volume_state"] == "VERIFIED_STATED_TOTAL_AND_COMPONENT_SUM" for item in offer["objects"]), "stated totals and components agree")

require(freeze["objects_with_prior_base_cell_match"] == 14, "all objects have prior base matches")
require(freeze["frozen_destination_predictions"] == 121, "freeze destination census")
require(freeze["M1_price_estimable_predictions"] == freeze["M1_volume_estimable_predictions"] == 8, "eight M1 predictions frozen")
require(freeze["M2_price_estimable_predictions"] == freeze["M2_volume_estimable_predictions"] == 0, "M2 abstains")
require(freeze["invalid_delivery_period_objects"] == [] and freeze["source_volume_conflict_objects"] == [], "no source quarantine")
m1 = [(item["object_id"], item["product"], pred["destination"]) for item in freeze["objects"] for pred in item["frozen_local_predictions"] if "point" in pred["price"].get("M1", {})]
require(m1 == [(1, "Haavapaberipuit", "Kunda"), (2, "Haavapaberipuit", "Kunda"), (3, "Kasepaberipuit", "Pärnu"), (4, "Kasepaberipuit", "Pärnu"), (5, "Kasepaberipuit", "Pärnu"), (6, "Kuusepaberipuit", "Paldiski"), (7, "Kuusepaberipuit", "Paldiski"), (8, "Kuusepaberipuit", "Paldiski")], "M1 frozen identities")

require(result["schema_version"] == "bpm.rmk.result-structured.v0.5", "result schema")
require(result["award_row_count"] == 52 and result["local_outcome_count"] == 32, "result census")
require(result["quarantined_outcome_count"] == 0 and result["quarantined_outcomes"] == [], "no quarantined result")
require(result["total_awarded_volume_m3"] == 114085, "result volume")
require(result["extraction_failures"] == [], "no extraction failures")
require(all(math.isclose(item["coverage_offer_denominator"], 1.0, rel_tol=0, abs_tol=1e-12) for item in result["object_totals"]), "full object coverage")

frozen_keys = {(item["object_id"], pred["destination"]) for item in freeze["objects"] for pred in item["frozen_local_predictions"]}
outcome_keys = {(item["object_id"], item["destination"]) for item in result["local_outcomes"]}
score_keys = {(item["object_id"], item["destination"]) for item in scoring["local_scores"]}
require(score_keys == frozen_keys & outcome_keys, "exact intersection scoring")
require(scoring["scored_exact_destination_predictions"] == 18 and scoring["non_observed_or_unawarded_predictions"] == 103, "score census")
require(scoring["M1_price_scored_predictions"] == scoring["M1_volume_scored_predictions"] == 1, "one M1 cell scored")
m1_scores = [item for item in scoring["local_scores"] if "point_prediction_eur_m3" in item["price"].get("M1", {})]
require(len(m1_scores) == 1 and (m1_scores[0]["object_id"], m1_scores[0]["destination"]) == (3, "Pärnu"), "M1 scored identity")
m1_score = m1_scores[0]
require(m1_score["price"]["local_point_comparison"] == "M1", "M1 price local win")
require(m1_score["volume"]["local_point_comparison"] == "M0", "M1 volume local loss")
require(math.isclose(m1_score["price"]["M1"]["absolute_error_eur_m3"], 0.08372424006402213, rel_tol=0, abs_tol=1e-12), "M1 price error")
require(math.isclose(m1_score["volume"]["M1"]["absolute_log_error"], 2.3473864329172445, rel_tol=0, abs_tol=1e-12), "M1 volume error")
price_errors = [item["price"]["M0"]["absolute_error_eur_m3"] for item in scoring["local_scores"]]
volume_errors = [item["volume"]["M0"]["absolute_log_error"] for item in scoring["local_scores"]]
require(math.isclose(scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"], statistics.fmean(price_errors), rel_tol=0, abs_tol=1e-12), "price MAE")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_volume_MALE"], statistics.fmean(volume_errors), rel_tol=0, abs_tol=1e-12), "volume MALE")
require(scoring["global_winner"] is None and scoring["automatic_promotion"] is False, "no global winner")

require(adjudication["updated_prior_cells"] == 18 and adjudication["new_local_cells"] == 14, "posterior partition")
require(adjudication["objects_full_coverage"] == list(range(1, 15)), "all objects full coverage")
require(adjudication["unawarded_objects"] == [] and adjudication["not_estimable_source_objects"] == [], "no missing or invalid object")
require(previous["local_cell_count"] == 288 and previous["posterior_observation_count"] == 696, "parent census")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["adjudication_sha256"] == digest(adjudication_path), "posterior adjudication link")
require(posterior["local_cell_count"] == 302 and posterior["posterior_observation_count"] == 760, "posterior accumulation")
require(sum(cell.get("observation_events", []).count("2025-12-22") for cell in posterior["local_cells"].values()) == 32, "thirty-two outcomes batch-recorded")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(sum(cell["price"]["M1"]["state"] == "ESTIMABLE" for cell in z_post["cells"].values()) == 22, "Z_post M1 census")
require(sum(cell["price"]["M2"]["state"] == "ESTIMABLE_FOR_LISTED_PHASES" for cell in z_post["cells"].values()) == 0, "no premature M2")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no promotion")

paths = [pre_offer_path, offer_raw, offer_path, freeze_path, gate_path, result_raw, result_path, extractor_path, scoring_path, adjudication_path, posterior_path, z_path]
manifest = {"schema_version": "bpm.rmk.event-manifest.v0.10", "event": "2025-12-22", "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)} for p in paths]}
manifest_path = EVENT / "closure/MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {"schema_version": "bpm.rmk.event-audit.v0.10", "event": "2025-12-22", "status": "PASS", "checks": len(checks), "failures": [], "manifest_sha256": digest(manifest_path)}
(EVENT / "closure/AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
