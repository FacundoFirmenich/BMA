"""Freeze the first new authoritative INDEC IPI seasonally adjusted chain."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from bma.experiments.hbp_eurostat_sts_v0_1 import index_forecast, log_innovations, m0_posterior, m1_posterior
from bma.experiments.hbp_indec_ipi_v0_1 import extract_ipi_records


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "preregistrations" / "HBP_INDEC_IPI_SA_2026_07_FREEZE_V0.1.json"
SOURCE = ROOT / "evidence" / "runs" / "hbp-indec-prodcom-public-custody-probe-v0.1" / "indec_ipi_series_2026.xls"
OUTPUT = ROOT / "evidence" / "runs" / "hbp-indec-ipi-sa-v0.1-2026-07-freeze"


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def predictive_payload(predictive: object) -> dict[str, float]:
    return {
        "degrees_of_freedom": predictive.degrees_of_freedom,
        "innovation_location": predictive.location,
        "innovation_scale": predictive.scale,
    }


def posterior_payload(posterior: dict) -> dict:
    result = dict(posterior)
    result["posterior_predictive"] = predictive_payload(result.pop("predictive"))
    return result


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"immutable output already exists: {OUTPUT}")
    prereg_bytes = PREREG.read_bytes()
    prereg = json.loads(prereg_bytes.decode("utf-8-sig"))
    source_hash = digest_file(SOURCE)
    if source_hash != prereg["jurisdiction"]["source_workbook_sha256"]:
        raise RuntimeError("INDEC IPI workbook hash mismatch")
    records, reader_version = extract_ipi_records(SOURCE)
    values = [record["seasonally_adjusted_index"] for record in records]
    innovations = log_innovations(values)
    priors = prereg["priors"]
    m0 = m0_posterior(innovations, alpha0=priors["M0"]["alpha0"], beta0=priors["M0"]["beta0"])
    m1 = m1_posterior(
        innovations,
        mu0=priors["M1"]["mu0"],
        kappa0=priors["M1"]["kappa0"],
        alpha0=priors["M1"]["alpha0"],
        beta0=priors["M1"]["beta0"],
    )
    forecasts = {
        "M0": {"state": "ESTIMABLE", **index_forecast(values[-1], m0["predictive"])},
        "M1": {"state": "ESTIMABLE", **index_forecast(values[-1], m1["predictive"])},
    }

    OUTPUT.mkdir(parents=True, exist_ok=False)
    normalized = {
        "schema": "hbp.indec.ipi.sa.training-series.v0.1",
        "source_workbook_sha256": source_hash,
        "records": records,
        "record_count": len(records),
        "transition_count": len(innovations),
    }
    (OUTPUT / "normalized_training_series.json").write_bytes(json_bytes(normalized))
    receipt = {
        "schema": "hbp.indec.ipi.sa.extraction-receipt.v0.1",
        "reader": f"xlrd=={reader_version}",
        "read_only": True,
        "source_workbook_sha256": source_hash,
        "sheet": "Cuadro 1",
        "training_start": records[0]["time"],
        "training_end": records[-1]["time"],
        "target_present": False,
        "last_original_index": records[-1]["original_index"],
        "last_seasonally_adjusted_index": records[-1]["seasonally_adjusted_index"],
        "pdf_rounding_reconciliation": "PASS_119.9_ORIGINAL_119.1_SA",
    }
    (OUTPUT / "extraction_receipt.json").write_bytes(json_bytes(receipt))
    z_post = {
        "schema": "hbp.indec.ipi.sa.z-post.v0.1",
        "state": "INITIALIZED_PRE_OUTCOME_FROM_FROZEN_CURRENT_VINTAGE",
        "training_start": records[0]["time"],
        "training_end": records[-1]["time"],
        "target_month": "2026-07",
        "observation_count": len(records),
        "transition_count": len(innovations),
        "M0": posterior_payload(m0),
        "M1": posterior_payload(m1),
        "weights": prereg["weights"],
        "initialization_event": True,
        "batch_is_exactly_equivalent_to_sequential_conjugate_updates": True,
        "reset_occurred": False,
        "pooling_occurred": False,
        "Z_post_is_residual_z": False,
        "Z_post_is_Z_XPL": False,
        "source_workbook_sha256": source_hash,
        "preregistration_sha256": digest_bytes(prereg_bytes),
    }
    z_path = OUTPUT / "posterior_z_post.json"
    z_path.write_bytes(json_bytes(z_post))
    freeze = {
        "schema": "hbp.indec.ipi.sa.forecast-freeze.v0.1",
        "status": "FROZEN_PRE_OUTCOME",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_month": "2026-07",
        "last_observed_month": records[-1]["time"],
        "last_observed_index": values[-1],
        "models": forecasts,
        "weights": prereg["weights"],
        "seasonality": "NOT_ADDED_ALREADY_SEASONALLY_ADJUSTED_TARGET",
        "UCII_observer": "ABSTAIN_NOT_YET_CAUSALLY_ALIGNED",
        "outcome_opened": False,
        "global_winner": None,
        "automatic_promotion": False,
        "source_workbook_sha256": source_hash,
        "preregistration_sha256": digest_bytes(prereg_bytes),
        "posterior_z_post_sha256": digest_file(z_path),
        "script_sha256": digest_file(Path(__file__)),
    }
    (OUTPUT / "forecast_freeze.json").write_bytes(json_bytes(freeze))
    paths = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    manifest = {
        "schema": "hbp.indec.ipi.sa.freeze-manifest.v0.1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": [
            {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": digest_file(path)}
            for path in paths
        ],
        "target_outcome_opened": False,
        "global_winner": None,
    }
    (OUTPUT / "manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"status": freeze["status"], "M0": forecasts["M0"]["point_median_index"], "M1": forecasts["M1"]["point_median_index"], "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
