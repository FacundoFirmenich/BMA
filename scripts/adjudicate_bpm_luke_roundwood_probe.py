from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


RUN_RELATIVE = Path("evidence/runs/bpm-luke-roundwood-public-probe-v0.1")
EXPECTED = {
    "luke_roundwood_metadata.json": "EEEC4DD5228206B0054CB53615AD65E23986A9C1D2E4877376173137C6B7C05E",
    "luke_roundwood_2026_07_finland_standing_spruce_logs.json": "16CFF01C7D93877584F585AB5DEF82360FC0BA65EF2B6F4554CAE4E13EC4529E",
    "luke_roundwood_query.json": "817B95891F49276F9CF6434BF4A3B14B9AEBD8A48F75334ACBE725C98DF6AE09",
    "capture_manifest.json": "85973EDD0451FB10D82C6CFBA8CA3FB63DBBEE73C14246A610130A3B22FBA8A4",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
run_dir = repo / RUN_RELATIVE
for name, expected in EXPECTED.items():
    observed = sha256(run_dir / name)
    if observed != expected:
        raise RuntimeError(f"Hash mismatch for {name}: {observed}")

metadata = json.loads((run_dir / "luke_roundwood_metadata.json").read_text(encoding="utf-8"))
data = json.loads(
    (run_dir / "luke_roundwood_2026_07_finland_standing_spruce_logs.json").read_text(encoding="utf-8")
)
manifest = json.loads((run_dir / "capture_manifest.json").read_text(encoding="utf-8"))
if data["id"] != ["INFO", "M", "MPKH", "KAUP", "PTL"] or data["size"] != [2, 1, 1, 1, 1]:
    raise RuntimeError("Unexpected Luke response cube")
info_index = data["dimension"]["INFO"]["category"]["index"]
volume_thousand_m3 = data["value"][info_index["M3T"]]
price_eur_m3 = data["value"][info_index["E_M3"]]
months = next(variable for variable in metadata["variables"] if variable["code"] == "M")

adjudication = {
    "schema": "bpm-luke-roundwood-public-probe-adjudication/v0.1",
    "adjudicated_on": "2026-08-22",
    "status": "PASS_SINGLE_PRODUCT_PRICE_VOLUME_SUPPORT",
    "jurisdiction": {
        "publisher": "Natural Resources Institute Finland (Luke)",
        "country": "Finland",
        "reference_month": "2026-07",
        "updated": data["updated"],
        "price_region": "WHOLE COUNTRY",
        "sale_type": "Standing sales",
        "product": "Spruce logs",
        "price_measure": "published current unit price",
        "volume_measure": "published transaction volume",
    },
    "observation": {
        "volume_source_value_thousand_m3": volume_thousand_m3,
        "volume_m3": volume_thousand_m3 * 1000,
        "price_eur_per_m3": price_eur_m3,
        "response_cells": len(data["value"]),
        "status_flags_present": "status" in data,
    },
    "support": {
        "metadata_month_count": len(months["values"]),
        "metadata_first_month": months["values"][0],
        "metadata_last_month": months["values"][-1],
        "at_least_36_months": len(months["values"]) >= 36,
        "price_and_volume_same_product_month_market": True,
        "public_without_account": True,
    },
    "quality_boundaries": {
        "post_release_observation": True,
        "first_release_vintages_preserved": False,
        "revision_notes_present": bool(data.get("note")),
        "response_extension_official_statistics_flag": data["extension"]["px"].get("official-statistics"),
        "publisher_page_and_response_flag_require_reconciliation": True,
        "price_is_not_claimed_as_auction_clearing_price": True,
        "national_cell_does_not_generalize_to_other_jurisdictions": True,
    },
    "authority": {
        "probe": "PASS_SCHEMA_AND_SINGLE_CELL_SUPPORT",
        "candidate": "PROMOTE_TO_SEPARATELY_PREREGISTERED_BPM_FINLAND_ROUNDWOOD_CAUSAL_CAMPAIGN",
        "model_fit": False,
        "forecast": False,
        "score": False,
        "posterior_update": False,
        "Z_post_update": False,
        "historical_freeze_reconstruction": False,
        "cross_source_pooling": False,
        "global_winner": None,
        "automatic_promotion": False,
    },
    "next_gate": {
        "freeze_required_before_next_values": True,
        "campaign_unit": "one reference month predicts only the next homologous month",
        "minimum_training_history": 36,
        "vintage_rule": "new prospective releases stored as distinct immutable bytes; revisions never overwrite first observed bytes",
        "seasonality_rule": "activate only after a separately frozen training design with same product, sale type, geography and calendar",
    },
    "custody": {
        "preregistration_sha256": manifest["preregistration"]["sha256"],
        "amendment_sha256": manifest["amendment"]["sha256"],
        "metadata_sha256": manifest["metadata"]["sha256"],
        "query_sha256": manifest["selection"]["query_sha256"],
        "data_sha256": manifest["data"]["sha256"],
    },
}
(run_dir / "probe_adjudication.json").write_text(
    json.dumps(adjudication, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(json.dumps({"status": adjudication["status"], "observation": adjudication["observation"], "candidate": adjudication["authority"]["candidate"]}, indent=2))
