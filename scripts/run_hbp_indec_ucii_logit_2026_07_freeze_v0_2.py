"""Freeze UCII V0.2 after the sole sector-support-gate repair."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from bma.experiments.hbp_eurostat_sts_v0_1 import m0_posterior, m1_posterior
from bma.experiments.hbp_indec_ucii_v0_1 import (
    bayesian_linear_posterior,
    bounded_forecast,
    harmonic_features,
    logit_percent,
)
from bma.experiments.hbp_indec_ucii_v0_2 import extract_ucii_records_v0_2


ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "preregistrations" / "HBP_INDEC_UCII_LOGIT_2026_07_FREEZE_V0.2.json"
OUTPUT = ROOT / "evidence" / "runs" / "hbp-indec-ucii-logit-v0.2-2026-07-freeze"


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


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


def validate_chain(amendment: dict) -> tuple[dict, Path]:
    parent_ref = amendment["parent_preregistration"]
    parent_path = ROOT / parent_ref["path"]
    if digest_file(parent_path) != parent_ref["sha256"]:
        raise RuntimeError("UCII V0.1 parent preregistration hash mismatch")
    failure_ref = amendment["observed_gate_failure"]
    failure_path = ROOT / failure_ref["path"]
    if digest_file(failure_path) != failure_ref["sha256"]:
        raise RuntimeError("UCII V0.1 gate-failure hash mismatch")
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    if failure["fit_performed"] or failure["target_outcome_opened"]:
        raise RuntimeError("UCII V0.2 cannot repair a post-fit or post-outcome failure")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    source_ref = parent["parent_schema_capture"]
    for key in ("manifest", "schema", "workbook"):
        path = ROOT / source_ref[key]
        if digest_file(path) != source_ref[f"{key}_sha256"]:
            raise RuntimeError(f"UCII source {key} hash mismatch")
    manifest = json.loads((ROOT / source_ref["manifest"]).read_text(encoding="utf-8"))
    for record in manifest["files"]:
        path = ROOT / record["path"]
        if (
            digest_file(path) != record["sha256"]
            or path.stat().st_size != record["bytes"]
        ):
            raise RuntimeError(f"UCII source manifest mismatch: {record['path']}")
    return parent, ROOT / source_ref["workbook"]


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"immutable output already exists: {OUTPUT}")
    amendment_bytes = AMENDMENT.read_bytes()
    amendment = json.loads(amendment_bytes.decode("utf-8-sig"))
    parent, source = validate_chain(amendment)
    records, headers, reader_version, boundary_events = extract_ucii_records_v0_2(
        source
    )
    if (
        len(boundary_events)
        != amendment["execution_contract"]["expected_boundary_events"]
    ):
        raise RuntimeError("unexpected UCII sector boundary-event count")
    values = [record["general_percent"] for record in records]
    states = logit_percent(values)
    innovations = [current - previous for previous, current in zip(states, states[1:])]
    model = parent["models"]
    m0 = m0_posterior(
        innovations,
        alpha0=model["M0"]["alpha0"],
        beta0=model["M0"]["beta0"],
    )
    m1 = m1_posterior(
        innovations,
        mu0=model["M1"]["mu0"],
        kappa0=model["M1"]["kappa0"],
        alpha0=model["M1"]["alpha0"],
        beta0=model["M1"]["beta0"],
    )
    destination_months = [int(record["time"].split("-")[1]) for record in records[1:]]
    m2 = bayesian_linear_posterior(
        innovations,
        [harmonic_features(month) for month in destination_months],
        prior_mean=model["M2"]["prior_mean"],
        prior_precision_diagonal=model["M2"]["prior_precision_diagonal"],
        alpha0=model["M2"]["alpha0"],
        beta0_scale=model["M2"]["beta0"],
        future_features=harmonic_features(7),
    )
    july_replicates = sum(month == 7 for month in destination_months)
    if july_replicates != amendment["execution_contract"]["expected_July_replicates"]:
        raise RuntimeError("unexpected UCII prior July replicate count")
    forecasts = {
        "M0": {"state": "ESTIMABLE", **bounded_forecast(values[-1], m0["predictive"])},
        "M1": {"state": "ESTIMABLE", **bounded_forecast(values[-1], m1["predictive"])},
        "M2": {
            "state": "ESTIMABLE",
            **bounded_forecast(values[-1], m2["posterior_predictive"]),
        },
    }

    OUTPUT.mkdir(parents=True, exist_ok=False)
    normalized = {
        "schema": "hbp.indec.ucii.training-series.v0.2",
        "source_workbook_sha256": digest_file(source),
        "headers": headers,
        "records": records,
        "record_count": len(records),
        "transition_count": len(innovations),
        "sector_boundary_events": boundary_events,
        "general_target_likelihood_uses_sector_blocks": False,
    }
    (OUTPUT / "normalized_training_series.json").write_bytes(json_bytes(normalized))
    receipt = {
        "schema": "hbp.indec.ucii.extraction-receipt.v0.2",
        "reader": f"xlrd=={reader_version}",
        "read_only": True,
        "source_workbook_sha256": digest_file(source),
        "training_start": records[0]["time"],
        "training_end": records[-1]["time"],
        "target_present": False,
        "last_general_percent": values[-1],
        "general_minimum_percent": min(values),
        "general_maximum_percent": max(values),
        "sector_boundary_event_count": len(boundary_events),
        "July_phase_replicates": july_replicates,
        "V0_1_failure_preserved": True,
    }
    (OUTPUT / "extraction_receipt.json").write_bytes(json_bytes(receipt))
    m2_payload = dict(m2)
    m2_payload["posterior_predictive"] = predictive_payload(m2["posterior_predictive"])
    z_post = {
        "schema": "hbp.indec.ucii.z-post.v0.2",
        "state": "INITIALIZED_PRE_OUTCOME_AFTER_SECTOR_GATE_REPAIR",
        "training_start": records[0]["time"],
        "training_end": records[-1]["time"],
        "target_month": "2026-07",
        "observation_count": len(records),
        "transition_count": len(innovations),
        "M0": posterior_payload(m0),
        "M1": posterior_payload(m1),
        "M2": m2_payload,
        "weights": parent["weights"],
        "initialization_event": True,
        "batch_is_exactly_equivalent_to_sequential_conjugate_updates": True,
        "reset_occurred": False,
        "pooling_occurred": False,
        "sector_blocks_used_in_general_likelihood": False,
        "sector_boundary_events_preserved": len(boundary_events),
        "legacy_freeze_used": False,
        "Z_post_is_residual_z": False,
        "Z_post_is_Z_XPL": False,
    }
    z_path = OUTPUT / "posterior_z_post.json"
    z_path.write_bytes(json_bytes(z_post))
    freeze = {
        "schema": "hbp.indec.ucii.forecast-freeze.v0.2",
        "status": "FROZEN_PRE_OUTCOME",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_month": "2026-07",
        "last_observed_month": records[-1]["time"],
        "last_observed_percent": values[-1],
        "models": forecasts,
        "weights": parent["weights"],
        "outcome_opened": False,
        "global_winner": None,
        "automatic_promotion": False,
        "legacy_freeze_used": False,
        "sector_blocks_used_in_general_likelihood": False,
        "sector_boundary_events_preserved": len(boundary_events),
        "V0_1_gate_failure_sha256": amendment["observed_gate_failure"]["sha256"],
        "source_workbook_sha256": digest_file(source),
        "parent_preregistration_sha256": amendment["parent_preregistration"]["sha256"],
        "amendment_preregistration_sha256": digest_bytes(amendment_bytes),
        "posterior_z_post_sha256": digest_file(z_path),
        "script_sha256": digest_file(Path(__file__)),
    }
    (OUTPUT / "forecast_freeze.json").write_bytes(json_bytes(freeze))
    paths = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    manifest = {
        "schema": "hbp.indec.ucii.freeze-manifest.v0.2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": [
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": digest_file(path),
            }
            for path in paths
        ],
        "target_outcome_opened": False,
        "V0_1_gate_failure_preserved": True,
        "global_winner": None,
    }
    (OUTPUT / "manifest.json").write_bytes(json_bytes(manifest))
    print(
        json.dumps(
            {
                "status": freeze["status"],
                "last": values[-1],
                "M0": forecasts["M0"]["point_median_percent"],
                "M1": forecasts["M1"]["point_median_percent"],
                "M2": forecasts["M2"]["point_median_percent"],
                "sector_boundary_events": len(boundary_events),
                "output": str(OUTPUT),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
