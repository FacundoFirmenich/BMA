from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-02-26"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(condition: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(condition)})
    if not condition:
        raise AssertionError(name)


offer_raw = EVENT / "raw/Myygiobjektid_EP_26.02.2025.xlsx"
result_raw = EVENT / "raw/EdukadEP_26.02.2025.xlsx"
offer_path = EVENT / "structured/offer.json"
result_path = EVENT / "structured/result.json"
freeze_path = EVENT / "freeze/freeze.json"
old_closure = EVENT / "closure"
closure = EVENT / "closure_v2"
adjudication_path = closure / "adjudication.json"
posterior_path = closure / "prior_after_2025-02-26.json"
z_path = closure / "z_post_2025-02-26.json"

offer = load(offer_path)
result = load(result_path)
freeze = load(freeze_path)
adjudication = load(adjudication_path)
posterior = load(posterior_path)
z_post = load(z_path)

require(digest(offer_raw) == "A4A58FCF42DAF4026805923195F13F88351414FF2228F9AC5978783561BB10FB", "raw offer hash")
require(digest(result_raw) == "72106FE84B1186C24CD124B85115D2D5536EA5976758312AB3F2BB31EC61D9C2", "raw result hash")
require(digest(freeze_path) == "C509BF1EF4274D7840B3184900CD48B1F596BC2D48B8409F9C3EDB7742F7CB92", "freeze hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze created before result download")
require(freeze["result"]["body_opened"] is False, "freeze records closed result")
require(freeze["object_count"] == 22 and freeze["price_target_count"] == 35, "frozen offer census")
require(freeze["historical_2023_2024_model_observations"] == 0, "history excluded from fit")
require(len(freeze["source_inconsistencies"]) == 1 and freeze["source_inconsistencies"][0]["object_id"] == 16, "object 16 discrepancy preserved")
require(offer["object_count"] == 22 and offer["advertised_volume_m3"] == 255243, "structured offer totals")
require(result["award_row_count"] == 131 and result["local_outcome_count"] == 114, "result row and local census")
require(result["total_awarded_volume_m3"] == 255124, "result physical total")
require(not result["price_mapping_failures"], "all price vectors mapped from offer-only weights")
require(adjudication["freeze_sha256"] == digest(freeze_path), "adjudication freeze link")
require(adjudication["raw_result_sha256"] == digest(result_raw), "adjudication raw result link")
require(adjudication["scored_predictions"] == 0, "empty-prior event not scored")
require(len(adjudication["objects_full_coverage"]) == 20, "twenty full coverage objects")
require(adjudication["objects_partial_coverage"] == [21], "object 21 partial coverage")
require(adjudication["objects_source_volume_conflict"] == [16], "object 16 source conflict")
require(posterior["adjudication_sha256"] == digest(adjudication_path), "posterior adjudication link")
require(posterior["local_cell_count"] == 114, "posterior local cell count")
require(posterior["posterior_observation_count"] == 228, "posterior outcome count")
require(all("calendar_phase" not in cell["descriptor"] for cell in posterior["local_cells"].values()), "phase excluded from base cell identity")
require(all(len(cell["price"]["phases"]) == 1 and len(cell["volume"]["phases"]) == 1 for cell in posterior["local_cells"].values()), "phase retained in observation state")
require(all(cell["weights"]["activated"] is False for cell in posterior["local_cells"].values()), "weights inactive without common support")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post future prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(z_post["Z_post_is_residual_z"] is False and z_post["Z_post_is_Z_XPL"] is False, "Z_post semantics")
require(z_post["Z_XPL_bilateral_thresholds"] == [0.25, 5.25], "Z-XPL thresholds")
require((old_closure / "INVALID_DO_NOT_USE_PHASE_IN_CELL_KEY.md").exists(), "invalid V1 posterior marked")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no global winner or promotion")

manifest_files = [
    offer_raw,
    result_raw,
    offer_path,
    result_path,
    freeze_path,
    adjudication_path,
    posterior_path,
    z_path,
    ROOT / "preregistrations/BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1_CELL_IDENTITY_AMENDMENT_20260821.json",
]
manifest = {
    "schema_version": "bpm.rmk.event-manifest.v0.1",
    "event": "2025-02-26",
    "files": [
        {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
        for path in manifest_files
    ],
}
manifest_path = closure / "MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

audit = {
    "schema_version": "bpm.rmk.event-audit.v0.1",
    "event": "2025-02-26",
    "status": "PASS",
    "checks": len(checks),
    "failures": [item for item in checks if not item["pass"]],
    "manifest_sha256": digest(manifest_path),
}
audit_path = closure / "AUDIT.json"
audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
