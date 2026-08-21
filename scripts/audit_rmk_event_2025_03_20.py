from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-03-20"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2025-02-26/closure_v2/prior_after_2025-02-26.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


offer_raw = EVENT / "raw/EP_objektid_pakkumuse-vorm_hakkpuit_25.03.20.xlsx"
result_raw = EVENT / "raw/Edukad_EP_20.03.2025.xlsx"
offer_path = EVENT / "structured/offer.json"
result_path = EVENT / "structured/result.json"
freeze_path = EVENT / "freeze/freeze.json"
closure = EVENT / "closure"
adjudication_path = closure / "adjudication.json"
posterior_path = closure / "prior_after_2025-03-20.json"
z_path = closure / "z_post_2025-03-20.json"
offer, result, freeze = load(offer_path), load(result_path), load(freeze_path)
adjudication, posterior, z_post = load(adjudication_path), load(posterior_path), load(z_path)

require(digest(offer_raw) == "4D0462BC42932A60C25A1B4F3A0FB94AE727D0BCC6A4BA7D1D53323942E11456", "offer hash")
require(digest(result_raw) == "6002F2E0D77797BA2FD6CC480CE321F20FF1FC5951C8CF146DA5E34FD714C8CC", "result hash")
require(digest(freeze_path) == "CA505F41F4D787AD9B64F4A33432311E7DB522A5C0C4435AE28136F45F5277DA", "freeze hash")
require(freeze_path.stat().st_ctime_ns < result_raw.stat().st_ctime_ns, "freeze precedes result download")
require(freeze["result"]["body_opened"] is False, "result closed in freeze")
require(freeze["inputs_sha256"]["prior_after_2025-02-26"] == digest(PREVIOUS), "previous prior link")
require(offer["location_total_matches"] is True and offer["advertised_volume_m3"] == 6759, "offer volume custody")
require(offer["exact_calendar_phase"] == "M04-M05-M06", "exact phase")
require(offer["frozen_conversions"] == {"m3_to_pm3": 2.78, "m3_to_MWh_primary": 2.22}, "conversion freeze")
require(result["award_row_count"] == 2 and result["total_awarded_volume_pm3"] == 18794, "result physical rows")
require(abs(result["total_awarded_volume_m3"] - 6760.431654676259) < 1e-12, "deterministic unit conversion")
require(result["coverage_state"] == "DIAGNOSTIC_ONLY_APPROXIMATE_OFFER_AND_UNIT_ROUNDING", "coverage boundary")
require(adjudication["freeze_sha256"] == digest(freeze_path), "adjudication freeze link")
require(adjudication["scored_predictions"] == 0, "first wood-chip cells unscored")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent link")
require(posterior["local_cell_count"] == 116 and posterior["posterior_observation_count"] == 232, "posterior accumulation")
require(sum(cell["descriptor"]["product"] == "Hakkpuit" for cell in posterior["local_cells"].values()) == 2, "two wood-chip local cells")
require(all("calendar_phase" not in cell["descriptor"] for cell in posterior["local_cells"].values()), "phase not in base identity")
require(z_post["future_prior_sha256"] == digest(posterior_path), "Z_post future prior link")
require(z_post["adjudication_sha256"] == digest(adjudication_path), "Z_post adjudication link")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "no reset or pooling")
require(posterior["global_winner"] is None and posterior["automatic_promotion"] is False, "no global winner or promotion")

paths = [offer_raw, result_raw, offer_path, result_path, freeze_path, adjudication_path, posterior_path, z_path]
manifest = {"schema_version": "bpm.rmk.event-manifest.v0.1", "event": "2025-03-20", "files": [
    {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)} for path in paths
]}
manifest_path = closure / "MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {"schema_version": "bpm.rmk.event-audit.v0.1", "event": "2025-03-20", "status": "PASS", "checks": len(checks), "failures": [], "manifest_sha256": digest(manifest_path)}
(closure / "AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
