from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2026-02-23"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-12-22/closure/prior_after_2025-12-22.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


paths = {
    "pre_offer": EVENT / "gates/pre_offer_2026-02-23.json",
    "offer_raw": EVENT / "raw/Muugiobjektid_EP_23.02.2026.xlsx",
    "offer": EVENT / "structured/offer_structured.json",
    "source_gate": EVENT / "gates/source_volume_conflict_object_1.json",
    "policy": EVENT / "gates/unweighted_multiclass_price_policy.json",
    "freeze": EVENT / "freeze/freeze.json",
    "pre_result": EVENT / "gates/pre_result_gate.json",
    "result_raw": EVENT / "raw/Edukad_EP__23.02.2026-.xlsx",
    "probe": EVENT / "structured/result_v0_5_probe.json",
    "repair_script": ROOT / "scripts/quarantine_rmk_unweighted_multiclass_v0_1.py",
    "repair_gate": EVENT / "gates/post_result_pre_scoring_unweighted_multiclass_repair.json",
    "result": EVENT / "structured/result.json",
    "scoring": EVENT / "closure/local_scoring.json",
    "adjudication": EVENT / "closure/adjudication.json",
    "posterior": EVENT / "closure/prior_after_2026-02-23.json",
    "z": EVENT / "closure/z_post_2026-02-23.json",
}

expected_hashes = {
    "pre_offer": "CC22153A084CFBE007F4AEB8A4D8ED7A8C608A491A8120FFD9877D0242E4E913",
    "offer_raw": "CFC761EC69AB86C53396BEDB9B866522292AAA8A4195F8E1C02F4AE9F1903EC8",
    "offer": "E549640EEEAC0DA97DEEC77FED435E07A8B11FCF786E62CF680D877340C3C5B6",
    "source_gate": "3A4A0BD7E8D10C9719AE2900C8DACC66A8BF2E54ED3B30EF825A4AB230EF2DAA",
    "policy": "D9E16C42EAB8F34BA12E0EFAB8C073AAE5BF5E480F41352F8F9C96B5A5CB20B2",
    "freeze": "495DF9F4CA50BB5E32D7E9763CA21E04E84CAF5378F4908AFFB7680691FF8CCD",
    "pre_result": "19AE4EE7A192ED9E25B16C0A01777151044F560C0756E7021997B36FA5638124",
    "result_raw": "4A60D7FE3F652CABA516BC4A9ADCD0A4719FEF48F8C9BFC6962334EF7852D264",
    "probe": "E5F07CA6C8E80C0753E955A2996F9880BA617F378F694A4298E324EDA6EFCF56",
    "repair_script": "801168C638CDBB65C346442995FC40841A101F65DED4EAAC86540799E6D68A8E",
    "repair_gate": "163D5E9AA13E88ED034D7ABCF2F632F0F5949AC79F1C2AD9C78CA9AF3D9812EC",
    "result": "02DC2F5C90EAEE4F7B8D4B31F223E18C8A4BAB456C123ACC2C9C99A0F53F18F6",
    "scoring": "6477DC10733B848A2F5B012DB0D8DE812D6D424D74DD2E3732B915B67708B83A",
    "adjudication": "58A4E0C89E2EDF877200A35F2C3586DD7E9C2FA367BB393B57231F5035E4A2B1",
    "posterior": "5E9EDFEE38C009CE37D6943DD462ECA29BE5FB4E7A8FA39BFC5C6C1161EB89B9",
    "z": "E882E158CE809AF9DBD8B8C137CAE90D183D4BBBD518F249B39CBC2D868C7489",
}
for name, expected in expected_hashes.items():
    require(digest(paths[name]) == expected, f"{name} hash")

offer, freeze = load(paths["offer"]), load(paths["freeze"])
probe, result = load(paths["probe"]), load(paths["result"])
scoring, adjudication = load(paths["scoring"]), load(paths["adjudication"])
previous, posterior, z_post = load(PREVIOUS), load(paths["posterior"]), load(paths["z"])

require(paths["freeze"].stat().st_ctime_ns < paths["result_raw"].stat().st_ctime_ns, "freeze precedes result")
require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "freeze prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(paths["offer"]), "freeze offer link")
require(result["freeze_used_sha256"] == digest(paths["freeze"]), "result freeze link")
require(result["structured_offer_used_sha256"] == digest(paths["offer"]), "result offer link")
require(result["parent_probe_sha256"] == digest(paths["probe"]), "repair probe link")
require(result["pre_result_policy_sha256"] == digest(paths["policy"]), "repair policy link")

require(offer["object_count"] == 39 and offer["advertised_volume_m3"] == 237039, "offer census")
bad = [item for item in offer["objects"] if not item["location_total_matches"]]
require(len(bad) == 1 and bad[0]["object_id"] == 1, "single source conflict")
require(bad[0]["location_sheet_total_m3"] == 7067 and bad[0]["location_component_sum_m3"] == 8042, "source conflict values")
require(freeze["source_volume_conflict_objects"] == [1], "source gate precedence")
require(freeze["frozen_destination_predictions"] == 238, "freeze census")
require(freeze["M1_price_estimable_predictions"] == freeze["M1_volume_estimable_predictions"] == 38, "M1 freeze census")
require(freeze["M2_price_estimable_predictions"] == freeze["M2_volume_estimable_predictions"] == 0, "M2 abstains")

require(probe["award_row_count"] == 155 and len(probe["extraction_failures"]) == 16, "probe census")
require(all(item["state"] == "NOT_ESTIMABLE_PRICE_ENCODING_OR_MISSING_OFFER_WEIGHTS" for item in probe["extraction_failures"]), "only governed probe failures")
require(result["schema_version"] == "bpm.rmk.result-structured.v0.6", "repaired result schema")
require(result["award_row_count"] == 155 and result["local_outcome_count"] == 117, "repaired result census")
require(result["quarantined_outcome_count"] == 15 and result["extraction_failures"] == [], "quarantine census")
states = [item["state"] for item in result["quarantined_outcomes"]]
require(states.count("NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT") == 6, "source conflict quarantines")
require(states.count("NOT_ESTIMABLE_UNWEIGHTED_MULTICLASS_PRICE") == 9, "multiclass quarantines")
require(result["post_result_repair"]["predictions_changed"] is False, "repair did not change predictions")

frozen_keys = {(item["object_id"], pred["destination"]) for item in freeze["objects"] for pred in item["frozen_local_predictions"]}
outcome_keys = {(item["object_id"], item["destination"]) for item in result["local_outcomes"]}
score_keys = {(item["object_id"], item["destination"]) for item in scoring["local_scores"]}
require(score_keys == frozen_keys & outcome_keys, "exact intersection scoring")
require(scoring["scored_exact_destination_predictions"] == 38 and scoring["non_observed_or_unawarded_predictions"] == 200, "score census")
require(scoring["M1_price_scored_predictions"] == scoring["M1_volume_scored_predictions"] == 13, "M1 scored census")
require(scoring["diagnostic_aggregate"]["local_price_point_counts"] == {"M0": 9, "M1": 4, "TIE": 0}, "local price comparison")
require(scoring["diagnostic_aggregate"]["local_volume_point_counts"] == {"M0": 6, "M1": 7, "TIE": 0}, "local volume comparison")
price_errors = [item["price"]["M0"]["absolute_error_eur_m3"] for item in scoring["local_scores"]]
volume_errors = [item["volume"]["M0"]["absolute_log_error"] for item in scoring["local_scores"]]
require(math.isclose(scoring["diagnostic_aggregate"]["M0_price_mean_absolute_error_eur_m3"], statistics.fmean(price_errors), abs_tol=1e-12), "price MAE")
require(math.isclose(scoring["diagnostic_aggregate"]["M0_volume_MALE"], statistics.fmean(volume_errors), abs_tol=1e-12), "volume MALE")
require(scoring["global_winner"] is None and scoring["automatic_promotion"] is False, "no global winner")

require(adjudication["updated_prior_cells"] == 38 and adjudication["new_local_cells"] == 79, "posterior partition")
require(adjudication["not_estimable_source_objects"] == [{"object_id": 1, "state": "NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT"}], "source conflict preserved")
require(len(adjudication["quarantined_outcomes"]) == 15, "adjudication quarantine preserved")
require(previous["local_cell_count"] == 302 and previous["posterior_observation_count"] == 760, "parent census")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["adjudication_sha256"] == digest(paths["adjudication"]), "posterior adjudication link")
require(posterior["local_cell_count"] == 381 and posterior["posterior_observation_count"] == 994, "posterior accumulation")
require(sum(cell.get("observation_events", []).count("2026-02-23") for cell in posterior["local_cells"].values()) == 117, "event outcomes batch-recorded")
require(z_post["future_prior_sha256"] == digest(paths["posterior"]), "Z_post prior link")
require(sum(cell["price"]["M1"]["state"] == "ESTIMABLE" for cell in z_post["cells"].values()) == 30, "Z_post M1 census")
require(sum(cell["price"]["M2"]["state"] == "ESTIMABLE_FOR_LISTED_PHASES" for cell in z_post["cells"].values()) == 0, "no premature M2")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no promotion")

manifest_paths = list(paths.values()) + [PREVIOUS]
manifest = {"schema_version": "bpm.rmk.event-manifest.v0.11", "event": "2026-02-23", "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)} for p in manifest_paths]}
manifest_path = EVENT / "closure/MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {"schema_version": "bpm.rmk.event-audit.v0.11", "event": "2026-02-23", "status": "PASS", "checks": len(checks), "failures": [], "manifest_sha256": digest(manifest_path)}
(EVENT / "closure/AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
