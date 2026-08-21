from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-12-05"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-11-28/closure/prior_after_2025-11-28.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_EP_05.12.2025.xlsx"
result_raw = EVENT / "raw/Edukad_EP_05.12.2025.xlsx"
offer_path = EVENT / "structured/offer_structured.json"
result_path = EVENT / "structured/result.json"
freeze_path = EVENT / "freeze/freeze.json"
weights_path = EVENT / "gates/offer_anchored_class_weights.json"
gate_path = EVENT / "gates/pre_result_gate.json"
repair_path = EVENT / "gates/post_result_pre_scoring_trailing_separator_repair.json"
extractor_path = ROOT / ".artifact_probe/extract_rmk_result_v0_5.mjs"
scoring_path = EVENT / "closure/local_scoring.json"
adjudication_path = EVENT / "closure/adjudication.json"
posterior_path = EVENT / "closure/prior_after_2025-12-05.json"
z_path = EVENT / "closure/z_post_2025-12-05.json"

offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
weights, repair = load(weights_path), load(repair_path)
previous, scoring, adjudication = load(PREVIOUS), load(scoring_path), load(adjudication_path)
posterior, z_post = load(posterior_path), load(z_path)

require(digest(offer_raw) == "2F580FE5BD6048412A2ABC461F40E910584E82DC365B142DB80A798FCEF74A81", "offer raw hash")
require(digest(result_raw) == "659E9239ACDA066ED67CDFA82EE492BE3887C81ED47708FB25E7F525AAABE4B7", "result raw hash")
require(digest(offer_path) == "7123BC15A3DE59D3EDE38EA449DF64AC817B7DF312545D9043529D0705E98EDA", "structured offer hash")
require(digest(result_path) == "056611AF6C5F07FA3A2BD48E81C0CF5500ABDCBE1E261203E0B8B860E93E159B", "structured result hash")
require(digest(freeze_path) == "0BD7DDBBE5569E32F2217DFA27F9F32CDC6B86D01996A568E096DA75A80997AF", "freeze hash")
require(digest(weights_path) == "1AA3568D71C3C97A61A74F107A7A9CEBFCBF3D9A86D291F3390BDC528C7F6E2C", "offer weights hash")
require(digest(gate_path) == "A222B84816D4BC22B846774C77724A0D1D5FAB489E70EEA73B93F60BA4A55D54", "pre-result gate hash")
require(digest(repair_path) == "1BEFBFADA7C08870E858118FB3F17E2E0481291C4D3120A4E3F05D790C65E9BD", "trailing separator repair hash")
require(digest(extractor_path) == "16BF1D69C4D37EBFBC3ED7B4893C8962C6B6E6F1BD7F3E7D1E0458B3C02030BB", "extractor v0.5 hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes result")
require(repair["causal_position"] == "RESULT_OPENED_NO_SCORING_OR_POSTERIOR_UPDATE_WRITTEN", "repair boundary")
require(repair["invariants"]["empty_segment_interpreted_as_zero"] is False, "empty suffix not zero")

require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "freeze prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(offer_path), "freeze offer link")
require(result["freeze_used_sha256"] == digest(freeze_path), "result freeze link")
require(result["structured_offer_used_sha256"] == digest(offer_path), "result offer link")
require(offer["object_count"] == 10 and offer["advertised_volume_m3"] == 10978, "offer census")
require(offer["all_location_totals_match"] is True, "all component sums verified")
require(all(item["location_volume_state"] == "VERIFIED_COMPONENT_SUM_NO_STATED_TOTAL" for item in offer["objects"]), "no invented stated totals")
require(all(math.isclose(sum(values), 1.0, rel_tol=0, abs_tol=1e-12) for values in weights["weights_by_object"].values()), "class weights sum to one")

require(freeze["frozen_destination_predictions"] == 18 and freeze["objects_with_prior_base_cell_match"] == 2, "freeze census")
require(freeze["M1_price_estimable_predictions"] == freeze["M1_volume_estimable_predictions"] == 1, "one M1 cell frozen")
require(freeze["M2_price_estimable_predictions"] == freeze["M2_volume_estimable_predictions"] == 0, "M2 abstains")
m1 = [(item["object_id"], pred["destination"]) for item in freeze["objects"] for pred in item["frozen_local_predictions"] if "point" in pred["price"].get("M1", {})]
require(m1 == [(10, "Paldiski")], "M1 frozen identity")

require(result["schema_version"] == "bpm.rmk.result-structured.v0.5", "result schema")
require(result["award_row_count"] == 16 and result["local_outcome_count"] == 14, "result census")
require(result["total_awarded_volume_m3"] == 10943, "result volume")
require(result["extraction_failures"] == [], "no extraction failures")
require(sum(row["price_state"] == "ESTIMABLE_OFFER_WEIGHTED_CLASS_PRICE" for row in result["rows"]) == 4, "weighted rows")
require(next(item for item in result["object_totals"] if item["object_id"] == 5)["awarded_volume_m3"] == 0, "unawarded object preserved")

frozen_keys = {(item["object_id"], pred["destination"]) for item in freeze["objects"] for pred in item["frozen_local_predictions"]}
outcome_keys = {(item["object_id"], item["destination"]) for item in result["local_outcomes"]}
score_keys = {(item["object_id"], item["destination"]) for item in scoring["local_scores"]}
require(score_keys == frozen_keys & outcome_keys, "exact intersection scoring")
require(score_keys == {(9, "Paldiski"), (9, "Pärnu"), (10, "Pärnu")}, "three scored identities")
require(scoring["scored_exact_destination_predictions"] == 3 and scoring["non_observed_or_unawarded_predictions"] == 15, "score census")
require((10, "Paldiski") in {(item["object_id"], item["destination"]) for item in scoring["non_observed"]}, "M1 target nonobserved")
require(scoring["M1_price_scored_predictions"] == scoring["M1_volume_scored_predictions"] == 0, "no M1 score invented")
price_errors = [item["price"]["M0"]["absolute_error_eur_m3"] for item in scoring["local_scores"]]
volume_errors = [item["volume"]["M0"]["absolute_log_error"] for item in scoring["local_scores"]]
require(math.isclose(scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"], statistics.fmean(price_errors), rel_tol=0, abs_tol=1e-12), "price MAE")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_volume_MALE"], statistics.fmean(volume_errors), rel_tol=0, abs_tol=1e-12), "volume MALE")
require(scoring["global_winner"] is None and scoring["automatic_promotion"] is False, "no global winner")

require(adjudication["updated_prior_cells"] == 3 and adjudication["new_local_cells"] == 11, "posterior partition")
require(adjudication["unawarded_objects"] == [5], "unawarded adjudication")
require(previous["local_cell_count"] == 277 and previous["posterior_observation_count"] == 668, "parent census")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["adjudication_sha256"] == digest(adjudication_path), "posterior adjudication link")
require(posterior["local_cell_count"] == 288 and posterior["posterior_observation_count"] == 696, "posterior accumulation")
require(sum(cell.get("observation_events", []).count("2025-12-05") for cell in posterior["local_cells"].values()) == 14, "fourteen outcomes batch-recorded")
require(all("2025-12-05" not in cell["price"].get("m1_innovation_events", []) for cell in posterior["local_cells"].values()), "no unscored M1 innovation")
require(sum(len(cell["price"]["observations"]) == 3 for cell in posterior["local_cells"].values()) == 15, "fifteen M1-supported cells")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(sum(cell["price"]["M1"]["state"] == "ESTIMABLE" for cell in z_post["cells"].values()) == 15, "Z_post M1 census")
require(sum(cell["price"]["M2"]["state"] == "ESTIMABLE_FOR_LISTED_PHASES" for cell in z_post["cells"].values()) == 0, "no premature M2")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no promotion")

paths = [offer_raw, result_raw, offer_path, result_path, freeze_path, weights_path, gate_path, repair_path, extractor_path, scoring_path, adjudication_path, posterior_path, z_path]
manifest = {"schema_version": "bpm.rmk.event-manifest.v0.9", "event": "2025-12-05", "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)} for p in paths]}
manifest_path = EVENT / "closure/MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {"schema_version": "bpm.rmk.event-audit.v0.9", "event": "2025-12-05", "status": "PASS", "checks": len(checks), "failures": [], "manifest_sha256": digest(manifest_path)}
(EVENT / "closure/AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
