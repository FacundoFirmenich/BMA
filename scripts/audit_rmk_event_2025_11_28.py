from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-11-28"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-10-29/closure/prior_after_2025-10-29.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/EP_objektid_pakkumuse-vorm_hakkpuit_28.11.2025.xlsx"
result_raw = EVENT / "raw/Edukad_EP_28.11.2025.xlsx"
offer_path = EVENT / "structured/offer.json"
result_path = EVENT / "structured/result.json"
freeze_path = EVENT / "freeze/freeze.json"
gate_path = EVENT / "gates/pre_result_gate.json"
scoring_path = EVENT / "closure/local_scoring.json"
adjudication_path = EVENT / "closure/adjudication.json"
posterior_path = EVENT / "closure/prior_after_2025-11-28.json"
z_path = EVENT / "closure/z_post_2025-11-28.json"
offer_extractor = ROOT / ".artifact_probe/extract_rmk_hakkpuit_offer_v0_2.mjs"
result_extractor = ROOT / ".artifact_probe/extract_rmk_hakkpuit_result_v0_2.mjs"
freezer_script = ROOT / "scripts/freeze_rmk_hakkpuit_offer_v0_2.py"
closer_script = ROOT / "scripts/close_rmk_hakkpuit_event_v0_2.py"

offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
scoring, adjudication = load(scoring_path), load(adjudication_path)
previous, posterior, z_post = load(PREVIOUS), load(posterior_path), load(z_path)

require(digest(offer_raw) == "006D357F617CC7C2F2E8B86D51D63CDEF55104B9967CC83238E52DD1F7ABDCF2", "offer raw hash")
require(digest(result_raw) == "FA1D8CFCCE8231E5EC3769D6D3875E5FEECE75A0D30A90D3B90C1A472DF3BD9C", "result raw hash")
require(digest(offer_path) == "6C7CD6F9A8B230C2FCF9B691D900446CBA3B78D7F1BF4252A5B819C2A8ECA311", "structured offer hash")
require(digest(result_path) == "2799BDA8BEFDC15371179E5E5903E2C785DE6DE4D47AD59F7B45A7BC896DA70C", "structured result hash")
require(digest(freeze_path) == "ED1DFE3C5C23EED21D5991FCDF268DA0EBC8B52514A7BBAA420814DADC31CA8E", "freeze hash")
require(digest(gate_path) == "3E8B474A502F46CB1F06911D678C9FB5C9B8A6AFA59B073951E87F1A78782CFB", "pre-result gate hash")
require(digest(offer_extractor) == "F94FBC845E176F9F0CA5C6A6A55388E30D85F0CFC2ED042FB4D133E8CA9750FB", "offer extractor hash")
require(digest(result_extractor) == "26E59D4F8A6859C90ED4620158D273F712F0C12451CE44C196FD698B5CBED1CC", "result extractor hash")
require(digest(freezer_script) == "6CAE6389A61363768E2CA5C15450A1C5D0470A42F46694A16ACF314404C5EBDE", "freezer hash")
require(digest(closer_script) == "F9B17DB9BD01A46ABD18F553EF1AC05C7F577D065CE27100B68775E3E3E37EAA", "closer hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes result")
require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(offer_path), "offer link")
require(result["freeze_used_sha256"] == digest(freeze_path), "result freeze link")
require(result["structured_offer_used_sha256"] == digest(offer_path), "result offer link")

require(offer["advertised_volume_m3"] == offer["location_sheet_volume_m3"] == offer["location_sheet_stated_total_m3"] == 10630, "offer volume reconciliation")
require(offer["location_total_matches"] is True and len(offer["location_components"]) == 4, "location census")
require(offer["measurement_fingerprint_sha256"] == "09A4899A7928837011B1FF0207C239AA52D14CA08EEA818C10957BC9083D14DF", "historical quality fingerprint continuity")
require(offer["exact_calendar_phase"] == "M12-M01-M02", "calendar phase")
require(offer["frozen_conversions"] == {"m3_to_pm3": 2.78, "m3_to_MWh_primary": 2.22}, "offer conversions")
require(len(offer["starting_price_regions"]) == 2, "regional starting prices preserved")

require(freeze["frozen_destination_predictions"] == 2, "freeze census")
require(freeze["object"]["prior_matching_destinations"] == ["Heltermaa", "Kuressaare/Ninase"], "frozen destination identities")
require(freeze["M1_price_estimable_predictions"] == freeze["M1_volume_estimable_predictions"] == 0, "M1 abstains")
require(freeze["M2_price_estimable_predictions"] == freeze["M2_volume_estimable_predictions"] == 0, "M2 abstains")

require(result["award_row_count"] == 4 and len(result["local_outcomes"]) == 4, "result census")
require(result["total_awarded_volume_pm3"] == 29552, "pm3 total")
require(math.isclose(result["total_awarded_volume_m3"], 29552 / 2.78, rel_tol=0, abs_tol=1e-12), "m3 conversion")
require(math.isclose(result["approximate_coverage_ratio"], (29552 / 2.78) / 10630, rel_tol=0, abs_tol=1e-12), "coverage conversion")
require(result["coverage_state"] == "DIAGNOSTIC_ONLY_APPROXIMATE_OFFER_AND_UNIT_ROUNDING", "coverage caveat")
require(result["extraction_failures"] == [], "no extraction failures")
require({item["destination"] for item in result["local_outcomes"]} == {"Heltermaa", "Ninase", "Roomassaare", "Pärsama"}, "result destinations")

require(scoring["scored_exact_destination_predictions"] == 1 and scoring["non_observed_or_unawarded_predictions"] == 1, "score census")
require([item["destination"] for item in scoring["local_scores"]] == ["Heltermaa"], "exact intersection only")
require(scoring["non_observed"] == [{"object_id": 1, "product": "Hakkpuit", "destination": "Kuressaare/Ninase", "state": "NOT_OBSERVED_EXACT_DESTINATION_OUTCOME"}], "composite destination not split")
score = scoring["local_scores"][0]
require(math.isclose(score["price"]["actual_eur_m3"], 15.52 * 2.78, rel_tol=0, abs_tol=1e-12), "price conversion")
require(math.isclose(score["price"]["M0"]["absolute_error_eur_m3"], abs(48.6778 - 15.52 * 2.78), rel_tol=0, abs_tol=1e-12), "price error recomputation")
require(math.isclose(score["volume"]["actual_m3"], 6422 / 2.78, rel_tol=0, abs_tol=1e-12), "volume conversion")
require(scoring["global_winner"] is None and scoring["automatic_promotion"] is False, "no global winner or promotion")

require(adjudication["updated_prior_cells"] == 1 and adjudication["new_local_cells"] == 3, "posterior partition")
require(previous["local_cell_count"] == 274 and previous["posterior_observation_count"] == 660, "parent census")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["adjudication_sha256"] == digest(adjudication_path), "posterior adjudication link")
require(posterior["local_cell_count"] == 277 and posterior["posterior_observation_count"] == 668, "posterior accumulation")
require(sum(cell.get("observation_events", []).count("2025-11-28") for cell in posterior["local_cells"].values()) == 4, "four outcomes batch-recorded")
require(all("2025-11-28" not in cell["price"].get("m1_innovation_events", []) for cell in posterior["local_cells"].values()), "no unscored M1 innovation")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(sum(cell["price"]["M1"]["state"] == "ESTIMABLE" for cell in z_post["cells"].values()) == 14, "M1 support census unchanged")
require(sum(cell["price"]["M2"]["state"] == "ESTIMABLE_FOR_LISTED_PHASES" for cell in z_post["cells"].values()) == 0, "no premature M2")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "posterior no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "posterior no promotion")

paths = [offer_raw, result_raw, offer_path, result_path, freeze_path, gate_path, offer_extractor, result_extractor, freezer_script, closer_script, scoring_path, adjudication_path, posterior_path, z_path]
manifest = {"schema_version": "bpm.rmk.event-manifest.v0.8", "event": "2025-11-28", "files": [{"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)} for path in paths]}
manifest_path = EVENT / "closure/MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {"schema_version": "bpm.rmk.event-audit.v0.8", "event": "2025-11-28", "status": "PASS", "checks": len(checks), "failures": [], "manifest_sha256": digest(manifest_path)}
(EVENT / "closure/AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
