from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-04-24"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-03-20/closure/prior_after_2025-03-20.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_KLH_24.04.2025.xlsx"
result_raw = EVENT / "raw/Edukad_KLH_24.04.2025.xlsx"
offer_path = EVENT / "structured/offer.json"
result_path = EVENT / "structured/result.json"
freeze_path = EVENT / "freeze/freeze.json"
closure = EVENT / "closure"
adjudication_path = closure / "adjudication.json"
posterior_path = closure / "prior_after_2025-04-24.json"
z_path = closure / "z_post_2025-04-24.json"
offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
adjudication, posterior, z_post = load(adjudication_path), load(posterior_path), load(z_path)

require(digest(offer_raw) == "86994714CFEF962F72712B2F823529B658280838CD520C10CEF30A6EC9DA1165", "offer hash")
require(digest(result_raw) == "AB6C08A3F3F38952858F9A3D67CD75E1F72DE742712839E34B67FDF29A41F7D4", "result hash")
require(digest(freeze_path) == "9DA3BE1893344CE3DDDB9E9CF85269AACA88B219842A7DEE71A6CFA057C43416", "freeze hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes result")
require(freeze["inputs_sha256"]["prior_after_2025_03_20"] == digest(PREVIOUS), "prior link")
require(freeze["objects_with_prior_base_cell_match"] == 0 and freeze["frozen_destination_predictions"] == 0, "zero comparable cells frozen")
require(offer["object_count"] == 20 and offer["advertised_volume_m3"] == 80146, "offer census")
require(offer["all_location_totals_match"] is True, "offer location totals")
require(result["award_row_count"] == 56 and result["local_outcome_count"] == 44, "result census")
require(result["total_awarded_volume_m3"] == 73702, "result volume")
require(not result["price_mapping_failures"], "class vectors mapped")
require(adjudication["freeze_sha256"] == digest(freeze_path), "adjudication freeze link")
require(adjudication["scored_predictions"] == 0, "no retrospective score")
require(len(adjudication["objects_full_coverage"]) == 15, "full coverage objects")
require(len(adjudication["objects_partial_coverage"]) == 4, "partial coverage objects")
require(adjudication["unawarded_objects"] == [10], "unawarded tilo object")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["local_cell_count"] == 160 and posterior["posterior_observation_count"] == 320, "posterior accumulation")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no global winner or promotion")

paths = [offer_raw, result_raw, offer_path, result_path, freeze_path, adjudication_path, posterior_path, z_path]
manifest = {"schema_version": "bpm.rmk.event-manifest.v0.1", "event": "2025-04-24", "files": [
    {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)} for path in paths
]}
manifest_path = closure / "MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {"schema_version": "bpm.rmk.event-audit.v0.1", "event": "2025-04-24", "status": "PASS", "checks": len(checks), "failures": [], "manifest_sha256": digest(manifest_path)}
(closure / "AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
