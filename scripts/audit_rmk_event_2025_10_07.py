from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-10-07"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-08-22/closure/prior_after_2025-08-22.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_EP_07.10.2025.xlsx"
result_raw = EVENT / "raw/Edukad_EP_07.10.2025_II.xlsx"
offer_path = EVENT / "structured/offer_structured.json"
result_path = EVENT / "structured/result.json"
freeze_path = EVENT / "freeze/freeze.json"
closure = EVENT / "closure"
scoring_path = closure / "local_scoring.json"
adjudication_path = closure / "adjudication.json"
posterior_path = closure / "prior_after_2025-10-07.json"
z_path = closure / "z_post_2025-10-07.json"

offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
scoring, adjudication = load(scoring_path), load(adjudication_path)
posterior, z_post = load(posterior_path), load(z_path)

require(digest(offer_raw) == "B380B4A0E95FEDCB285EC6644A0B5FDAD0C159DFC10317691E3C26066CB2436B", "offer raw hash")
require(digest(result_raw) == "3A11DD4CE2DF9E139128224565B2D3FEAD5D9C807DEFF4F38FCC58381E971C63", "result raw hash")
require(digest(freeze_path) == "9F74B7530FC80AA8DA312FFC6E8E8AFFF2C87F79035CEDA3CF2117BF5E939821", "freeze hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes result")
require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(offer_path), "offer link")
require(freeze["invalid_delivery_period_objects"] == [] and freeze["source_volume_conflict_objects"] == [], "clean offer gates")
require(freeze["objects_with_prior_base_cell_match"] == 13 and freeze["frozen_destination_predictions"] == 50, "freeze census")
require({item["calendar_phase"] for item in freeze["objects"]} == {"M10-M11-M12"}, "phase parsing")
require(offer["object_count"] == 14 and offer["advertised_volume_m3"] == 111499, "offer census")
require(offer["all_location_totals_match"] is True, "all offer volumes verified")

require(result["award_row_count"] == 27 and result["local_outcome_count"] == 26, "result census")
require(result["quarantined_outcome_count"] == 0 and result["quarantined_outcomes"] == [], "no quarantined outcomes")
require(result["total_awarded_volume_m3"] == 61916, "result volume")
require(not result["extraction_failures"], "result extraction has no failures")
require(result["freeze_used_sha256"] == digest(freeze_path), "result freeze link")

frozen_keys = {(item["object_id"], prediction["destination"]) for item in freeze["objects"] for prediction in item["frozen_local_predictions"]}
outcome_keys = {(item["object_id"], item["destination"]) for item in result["local_outcomes"]}
score_keys = {(item["object_id"], item["destination"]) for item in scoring["local_scores"]}
require(score_keys == frozen_keys & outcome_keys, "scores equal exact frozen-result intersection")
require(score_keys == {(1, "Kunda"), (2, "Kunda"), (5, "Paldiski"), (6, "Paldiski"), (10, "Roomassaare")}, "five exact scored targets")
require(scoring["scored_exact_destination_predictions"] == 5 and scoring["non_observed_or_unawarded_predictions"] == 45, "score and abstention census")
require(all(item["state"] == "NOT_OBSERVED_EXACT_DESTINATION_OUTCOME" for item in scoring["non_observed"]), "destination non-observations preserved")
price_errors = [item["price"]["absolute_error_eur_m3"] for item in scoring["local_scores"]]
volume_errors = [item["volume"]["absolute_log_error"] for item in scoring["local_scores"]]
require(math.isclose(scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"], statistics.fmean(price_errors), rel_tol=0, abs_tol=1e-12), "price MAE recomputation")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_volume_MALE"], statistics.fmean(volume_errors), rel_tol=0, abs_tol=1e-12), "volume MALE recomputation")
require(scoring["diagnostic_aggregate"]["comparison_model"] is None and scoring["global_winner"] is None, "no global or pairwise winner")
require(scoring["density_scores"].startswith("NOT_ESTIMABLE"), "density scores abstain")
require(all(item["price"]["M1_state"] == "NOT_ESTIMABLE_M1_SUPPORT" for item in scoring["local_scores"]), "M1 was not available pre-result")
require(all(item["price"]["M2_state"] == "NOT_ESTIMABLE_SEASONAL_SUPPORT" for item in scoring["local_scores"]), "M2 abstentions")
require(all(item["price"]["BMA_state"] == "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT" for item in scoring["local_scores"]), "BMA abstentions")

require(adjudication["objects_full_coverage"] == [1, 3, 5, 6, 9, 10, 11, 12, 13, 14], "full objects")
require(adjudication["objects_partial_coverage"] == [2, 4, 7, 8], "partial objects")
require(adjudication["objects_over_coverage"] == [] and adjudication["unawarded_objects"] == [], "no over or unawarded objects")
require(adjudication["not_estimable_source_objects"] == [], "all sources adjudicable")
require(adjudication["updated_prior_cells"] == 5 and adjudication["new_local_cells"] == 21, "posterior update partition")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["local_cell_count"] == 233 and posterior["posterior_observation_count"] == 522, "posterior accumulation")
count_three = [cell for cell in posterior["local_cells"].values() if len(cell["price"]["observations"]) == 3]
require(len(count_three) == 2, "two cells reach M1 observation support")
require({(cell["descriptor"]["product"], cell["descriptor"]["destination"]) for cell in count_three} == {("Haavapaberipuit", "Kunda"), ("Kuusepaberipuit", "Paldiski")}, "M1-supported cell identities")
require(all(cell["observation_events"].count("2025-10-07") == 2 for cell in count_three), "simultaneous outcomes recorded without hidden ordering")
require(all(cell["price"]["m1_innovations"] == [] for cell in count_three), "no within-event M1 innovation")
require(sum(len(cell["price"]["observations"]) == 2 for cell in posterior["local_cells"].values()) == 24, "twenty-four cells have two observations")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
m1_est_price = [cell for cell in z_post["cells"].values() if cell["price"]["M1"]["state"] == "ESTIMABLE"]
require(len(m1_est_price) == 2, "Z_post exposes exactly two M1 price cells")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "posterior no reset or pooling")
require(z_post["reset_occurred"] is False and z_post["pooling_occurred"] is False, "Z_post no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no global winner or promotion")

paths = [offer_raw, result_raw, offer_path, result_path, freeze_path, scoring_path, adjudication_path, posterior_path, z_path]
manifest = {
    "schema_version": "bpm.rmk.event-manifest.v0.5",
    "event": "2025-10-07",
    "files": [{"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)} for path in paths],
}
manifest_path = closure / "MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {
    "schema_version": "bpm.rmk.event-audit.v0.5",
    "event": "2025-10-07",
    "status": "PASS",
    "checks": len(checks),
    "failures": [],
    "manifest_sha256": digest(manifest_path),
}
(closure / "AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
