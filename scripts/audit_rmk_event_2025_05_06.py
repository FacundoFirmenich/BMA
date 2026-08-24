from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-05-06"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-04-24/closure/prior_after_2025-04-24.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_EP_06.05.2025.xlsx"
result_raw = EVENT / "raw/Edukad_EP06.05.2025.xlsx"
unpaired_raw = EVENT / "raw/Edukad_KLH06.05.2025.xlsx"
offer_frozen_path = EVENT / "structured/offer_structured.json"
offer_repaired_path = EVENT / "structured/offer_structured_v2_location_repair.json"
repair_receipt_path = EVENT / "structured/OFFER_LOCATION_TOTAL_REPAIR_RECEIPT.json"
result_path = EVENT / "structured/result.json"
freeze_path = EVENT / "freeze/freeze.json"
closure = EVENT / "closure"
adjudication_path = closure / "adjudication.json"
posterior_path = closure / "prior_after_2025-05-06.json"
z_path = closure / "z_post_2025-05-06.json"

offer_frozen, offer_repaired = load(offer_frozen_path), load(offer_repaired_path)
repair_receipt, result, freeze = load(repair_receipt_path), load(result_path), load(freeze_path)
adjudication, posterior, z_post = load(adjudication_path), load(posterior_path), load(z_path)

require(digest(offer_raw) == "C47FE032AA3B9C9B61497040D7B132F5F02C70C4D4FC3B04D5498AC5FE628842", "offer raw hash")
require(digest(result_raw) == "FA52581886D28FF22C764FBB22E71669CAA0F2D6C1BE852E9B3DE1D155F85171", "paired result raw hash")
require(digest(freeze_path) == "4D82B699FD3CB9E1D2796F944350E212F32BB23EA8E3684850C3199EAABC1D68", "freeze hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes paired result")
require(not unpaired_raw.exists(), "unpaired KLH result remains unopened")
require(freeze["quarantined_unpaired_result"]["body_opened"] is False, "unpaired result quarantine state")
require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(offer_frozen_path), "frozen offer link")
require(freeze["objects_with_prior_base_cell_match"] == 0 and freeze["frozen_destination_predictions"] == 0, "zero comparable cells frozen")
require(offer_frozen["object_count"] == 6 and offer_frozen["advertised_volume_m3"] == 35613, "frozen offer census")
require(repair_receipt["frozen_offer_preserved_sha256"] == digest(offer_frozen_path), "repair preserves frozen offer")
require(repair_receipt["repaired_offer_sha256"] == digest(offer_repaired_path), "repair offer link")
require(repair_receipt["predictive_semantic_object_differences"] == [], "repair leaves predictive semantics invariant")
require(offer_repaired["all_location_totals_match"] is True, "repaired offer location totals")
require(all(item["location_sheet_total_m3"] == item["advertised_volume_m3"] for item in offer_repaired["objects"]), "all six location totals exact")
require(result["award_row_count"] == 16 and result["local_outcome_count"] == 15, "result census")
require(result["total_awarded_volume_m3"] == 35613, "result volume")
require(not result["extraction_failures"], "result extraction has no failures")
require(result["structured_offer_used_sha256"] == digest(offer_repaired_path), "result uses repaired offer")
require(adjudication["freeze_sha256"] == digest(freeze_path), "adjudication freeze link")
require(adjudication["scored_predictions"] == 0, "no retrospective score")
require(adjudication["objects_full_coverage"] == [1, 2, 3, 4, 5, 6], "all objects full coverage")
require(adjudication["objects_partial_coverage"] == [], "no partial objects")
require(adjudication["objects_over_coverage"] == [], "no over-coverage objects")
require(adjudication["unawarded_objects"] == [], "no unawarded objects")
require(adjudication["not_estimable_source_objects"] == [], "all source volumes adjudicable")
require(adjudication["quarantined_unpaired_result"]["body_opened"] is False, "quarantine propagated")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["local_cell_count"] == 175 and posterior["posterior_observation_count"] == 350, "posterior accumulation")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "posterior no reset or pooling")
require(z_post["reset_occurred"] is False and z_post["pooling_occurred"] is False, "Z_post no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no global winner or promotion")

paths = [offer_raw, result_raw, offer_frozen_path, offer_repaired_path, repair_receipt_path, result_path, freeze_path, adjudication_path, posterior_path, z_path]
manifest = {
    "schema_version": "bpm.rmk.event-manifest.v0.2",
    "event": "2025-05-06",
    "files": [
        {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
        for path in paths
    ],
}
manifest_path = closure / "MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {
    "schema_version": "bpm.rmk.event-audit.v0.2",
    "event": "2025-05-06",
    "status": "PASS",
    "checks": len(checks),
    "failures": [],
    "manifest_sha256": digest(manifest_path),
}
(closure / "AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
