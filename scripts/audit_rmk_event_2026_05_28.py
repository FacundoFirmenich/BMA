from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2026-05-28"
PREVIOUS = ROOT / "evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events/2026-02-23/closure/prior_after_2026-02-23.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def require(value: bool, name: str) -> None:
    checks.append({"check": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


files = {
    "pre_offer": EVENT / "gates/pre_offer_2026-05-28.json",
    "raw_offer": EVENT / "raw/Myygiobjektid_28_05_2026.xlsx",
    "original_offer": EVENT / "structured/offer_structured_v0_2_pre_stocklot_semantics.json",
    "amendment": ROOT / "preregistrations/BPM_RMK_STOCKLOT_LOCATION_SEMANTICS_AMENDMENT_20260821.json",
    "repair_script": ROOT / "scripts/repair_rmk_stocklot_location_v0_1.py",
    "offer": EVENT / "structured/offer_structured.json",
    "weights": EVENT / "gates/offer_anchored_class_weights.json",
    "hake_gate": EVENT / "gates/unpaired_hake_result_quarantine.json",
    "freeze": EVENT / "freeze/freeze.json",
    "pre_result": EVENT / "gates/pre_result_gate.json",
    "raw_result": EVENT / "raw/Edukad_EP_28.05.2026.xlsx",
    "result": EVENT / "structured/result.json",
    "scoring": EVENT / "closure/local_scoring.json",
    "adjudication": EVENT / "closure/adjudication.json",
    "posterior": EVENT / "closure/prior_after_2026-05-28.json",
    "z": EVENT / "closure/z_post_2026-05-28.json",
}
expected = {
    "pre_offer": "2613E4B0C0ECA5A42F9A061DA36843403B75F9A182385EC84A0A1F1F68C19179",
    "raw_offer": "BECAF1D777E3F9725C43E08B483B04AE3EF325C86A4F94C8D9F59B23AFC1DB85",
    "original_offer": "9B8BA69024DE3A0F454FEF7EBCA4737EC5C7630E84F574D685005CC27FDABD12",
    "amendment": "3B3B402C57983F1AD81CC1EE4B273199E4D725C9ECCC9A79FE3DA7FBDCAA5D85",
    "repair_script": "CD52A859A47717F9D3F3FE27A0603498ACB953FBF427B0734A2D4C3BCD1AB7DF",
    "offer": "CB433CB7E9531A93F5850D11E708E1DDEB94B53431AA3A3AA52BF1AF9E5A1681",
    "weights": "A84AAEFF1D9D1CAACB57D6FC8D63C4B9E0C02BD41BCD6031AB455FF999350926",
    "hake_gate": "B32A9C91C9AA9CA83B2C3130D08E4F1D038D5E05C8FA4EF7185CB383B5C6AA08",
    "freeze": "747E6DE78861CE9654E1D0A1E78C5B13576A16B70DDF89C99E648C6F95A6AD2E",
    "pre_result": "0099DEC3FF713B19AA42B65BB5ABB4BB453BA589DCCD99CF9EBAA51CA3270A77",
    "raw_result": "56A0089906F405C88C7ED8A24EC46B6260CBB48AB403615DE17F7FFED261FF58",
    "result": "CEA2E204AA81F3920D23D8F17DA978D6B1750A33A3370630933A13EBE641F48E",
    "scoring": "13B2BAE7DF4DBCF082F00E3DF7E30BA561821DCF95E83483DE73726E9874203C",
    "adjudication": "29E7B105223939A5E4F4EBD2631887B7FCBFC049247CE5A4D64C114EB94AE904",
    "posterior": "30B881129B797CB0C2F7A35805F4BF089285D5ACD97FF4D65F2F8E36FDE2DE7C",
    "z": "F9BBD60D750EB1C8BBA49569E2BE20C8B89403AF061F3E8513BF5A9D45312CB7",
}
for name, sha in expected.items():
    require(digest(files[name]) == sha, f"{name} hash")

offer, freeze, result = load(files["offer"]), load(files["freeze"]), load(files["result"])
scoring, adjudication = load(files["scoring"]), load(files["adjudication"])
previous, posterior, z_post = load(PREVIOUS), load(files["posterior"]), load(files["z"])
weights, hake_gate = load(files["weights"]), load(files["hake_gate"])

require(files["freeze"].stat().st_ctime_ns < files["raw_result"].stat().st_ctime_ns, "freeze precedes general result")
require(not (EVENT / "raw/Edukad_hake_EP_28.05.2026.xlsx").exists(), "hake body remains closed")
require(hake_gate["result_body_opened"] is False and hake_gate["posterior_update_authorized"] is False, "hake quarantine")
require(offer["object_count"] == 5 and offer["advertised_volume_m3"] == 10166, "offer census")
require(offer["all_location_totals_match"] is True, "offer locations verified")
require(offer["stocklot_location_semantics_repair"] == {"changed_object_ids": [4, 5], "advertised_volumes_changed": False, "component_values_imputed": False}, "stocklot repair scope")
require(weights["weights_by_object"] == {"1": [0.23, 0.77]} and weights["invented_weights"] is False, "offer weights")
require(freeze["inputs_sha256"]["prior"] == digest(PREVIOUS), "freeze prior link")
require(freeze["inputs_sha256"]["structured_offer"] == digest(files["offer"]), "freeze offer link")
require(freeze["frozen_destination_predictions"] == 0 and freeze["objects_with_prior_base_cell_match"] == 0, "zero-match freeze")
require(freeze["source_volume_conflict_objects"] == [] and freeze["invalid_delivery_period_objects"] == [], "no source quarantine")

require(result["award_row_count"] == 7 and result["local_outcome_count"] == 7, "result census")
require(result["total_awarded_volume_m3"] == 10166 and result["extraction_failures"] == [], "result complete")
require(sum(row["price_state"] == "ESTIMABLE_OFFER_WEIGHTED_CLASS_PRICE" for row in result["rows"]) == 1, "one weighted row")
require(result["quarantined_unpaired_result"]["body_opened"] is False, "unpaired result preserved")
require(scoring["scored_exact_destination_predictions"] == 0 and scoring["local_scores"] == [], "no invented scores")
require(all(value is None for key, value in scoring["diagnostic_aggregate"].items() if key.startswith("M0_") or key.startswith("M1_") and not key.endswith("counts")), "diagnostics remain null")
require(scoring["global_winner"] is None and scoring["automatic_promotion"] is False, "no global winner")

require(adjudication["updated_prior_cells"] == 0 and adjudication["new_local_cells"] == 7, "posterior partition")
require(adjudication["objects_full_coverage"] == [1, 2, 3, 4, 5], "full object coverage")
require(previous["local_cell_count"] == 381 and previous["posterior_observation_count"] == 994, "parent census")
require(posterior["parent_prior_sha256"] == digest(PREVIOUS), "posterior parent")
require(posterior["local_cell_count"] == 388 and posterior["posterior_observation_count"] == 1008, "posterior accumulation")
require(sum(cell.get("observation_events", []).count("2026-05-28") for cell in posterior["local_cells"].values()) == 7, "seven outcomes batch-recorded")
require(z_post["future_prior_sha256"] == digest(files["posterior"]), "Z_post prior link")
require(sum(cell["price"]["M1"]["state"] == "ESTIMABLE" for cell in z_post["cells"].values()) == 30, "Z_post M1 census")
require(sum(cell["price"]["M2"]["state"] == "ESTIMABLE_FOR_LISTED_PHASES" for cell in z_post["cells"].values()) == 0, "no premature M2")
require(posterior["reset_occurred"] is False and posterior["pooling_occurred"] is False, "no reset or pooling")

manifest = {"schema_version": "bpm.rmk.event-manifest.v0.12", "event": "2026-05-28", "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)} for p in list(files.values()) + [PREVIOUS]]}
manifest_path = EVENT / "closure/MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
audit = {"schema_version": "bpm.rmk.event-audit.v0.12", "event": "2026-05-28", "status": "PASS", "checks": len(checks), "failures": [], "manifest_sha256": digest(manifest_path)}
(EVENT / "closure/AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
