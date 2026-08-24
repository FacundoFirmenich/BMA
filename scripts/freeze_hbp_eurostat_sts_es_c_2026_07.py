"""Capture the post-preregistration Eurostat STS state and freeze July 2026.

The target is never requested.  The acquisition URL is frozen in the exact
preregistration and ends at 2026-06.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bma.experiments.hbp_eurostat_sts_v0_1 import (
    GateFailure,
    StudentTPredictive,
    index_forecast,
    log_innovations,
    m0_posterior,
    m1_posterior,
)


REPOSITORY = Path(__file__).resolve().parents[1]
PREREGISTRATION = REPOSITORY / "preregistrations" / "HBP_EUROSTAT_STS_ES_C_2026_07_FREEZE_V0.1.json"
OUTPUT = REPOSITORY / "evidence" / "runs" / "hbp-eurostat-sts-es-c-v0.1-2026-07-freeze"
MAX_RESPONSE_BYTES = 250_000


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def canonical_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def next_month(month: str) -> str:
    year, number = (int(part) for part in month.split("-"))
    return f"{year + (number == 12):04d}-{1 if number == 12 else number + 1:02d}"


def contiguous_months(start: str, end: str) -> list[str]:
    months = []
    cursor = start
    while True:
        months.append(cursor)
        if cursor == end:
            return months
        cursor = next_month(cursor)
        if len(months) > 2_000:
            raise GateFailure("invalid or unbounded month range")


def category_positions(document: dict, dimension: str) -> dict[int, str]:
    index = document["dimension"][dimension]["category"]["index"]
    if isinstance(index, list):
        return {position: code for position, code in enumerate(index)}
    return {int(position): code for code, position in index.items()}


def sparse_values(payload: object) -> dict[int, float]:
    if isinstance(payload, list):
        return {position: float(value) for position, value in enumerate(payload) if value is not None}
    if isinstance(payload, dict):
        return {int(position): float(value) for position, value in payload.items()}
    raise GateFailure("unsupported JSON-stat value representation")


def sparse_flags(payload: object | None) -> dict[int, str]:
    if payload is None:
        return {}
    if isinstance(payload, list):
        return {position: str(value) for position, value in enumerate(payload) if value is not None}
    if isinstance(payload, dict):
        return {int(position): str(value) for position, value in payload.items()}
    raise GateFailure("unsupported JSON-stat status representation")


def validate_and_extract(document: dict, preregistration: dict) -> list[dict]:
    expected_ids = ["freq", "indic_bt", "nace_r2", "s_adj", "unit", "geo", "time"]
    if document.get("id") != expected_ids:
        raise GateFailure(f"unexpected dimension order: {document.get('id')!r}")
    if not document.get("updated"):
        raise GateFailure("source updated timestamp is absent")

    jurisdiction = preregistration["jurisdiction"]
    expected_singletons = {
        "freq": "M",
        "indic_bt": jurisdiction["indicator"],
        "nace_r2": jurisdiction["nace_r2"],
        "s_adj": jurisdiction["seasonal_adjustment"],
        "unit": jurisdiction["unit"],
        "geo": jurisdiction["geo"],
    }
    for dimension, expected_code in expected_singletons.items():
        positions = category_positions(document, dimension)
        if positions != {0: expected_code}:
            raise GateFailure(f"unexpected {dimension} positions: {positions!r}")

    temporal = preregistration["temporal_contract"]
    expected_times = contiguous_months(temporal["training_start"], temporal["training_end"])
    time_positions = category_positions(document, "time")
    actual_times = [time_positions[position] for position in sorted(time_positions)]
    if actual_times != expected_times:
        raise GateFailure("training months are not the exact frozen contiguous range")
    if temporal["target_month"] in actual_times:
        raise GateFailure("target month appeared before freeze")
    if len(actual_times) < preregistration["support_and_recovery"]["minimum_complete_training_months"]:
        raise GateFailure("insufficient complete training months")

    values = sparse_values(document.get("value"))
    flags = sparse_flags(document.get("status"))
    if set(values) != set(range(len(actual_times))):
        missing = sorted(set(range(len(actual_times))) - set(values))
        raise GateFailure(f"missing training values at positions {missing!r}")
    records = [
        {"time": month, "value": values[position], "status": flags.get(position)}
        for position, month in enumerate(actual_times)
    ]
    if any(record["value"] <= 0.0 for record in records):
        raise GateFailure("non-positive index observation")
    return records


def predictive_payload(predictive: StudentTPredictive) -> dict[str, float]:
    return {
        "degrees_of_freedom": predictive.degrees_of_freedom,
        "innovation_location": predictive.location,
        "innovation_scale": predictive.scale,
    }


def posterior_payload(posterior: dict) -> dict:
    result = dict(posterior)
    predictive = result.pop("predictive")
    result["posterior_predictive"] = predictive_payload(predictive)
    return result


def main() -> None:
    if OUTPUT.exists():
        raise GateFailure(f"immutable output already exists: {OUTPUT}")
    preregistration_bytes = PREREGISTRATION.read_bytes()
    preregistration = json.loads(preregistration_bytes.decode("utf-8-sig"))
    query = preregistration["temporal_contract"]["query"]
    request = Request(query, headers={"User-Agent": "BMA-HBP-evidence-custody/0.1"})
    captured_at = datetime.now(timezone.utc).isoformat()
    with urlopen(request, timeout=60) as response:
        raw_response = response.read(MAX_RESPONSE_BYTES + 1)
        response_headers = {key: value for key, value in response.headers.items()}
        status_code = response.status
        final_url = response.geturl()
    if len(raw_response) > MAX_RESPONSE_BYTES:
        raise GateFailure("bounded response exceeded 250000 bytes")
    if status_code != 200:
        raise GateFailure(f"unexpected HTTP status {status_code}")

    document = json.loads(raw_response.decode("utf-8-sig"))
    records = validate_and_extract(document, preregistration)
    index_values = [float(record["value"]) for record in records]
    innovations = log_innovations(index_values)
    priors = preregistration["priors"]
    m0 = m0_posterior(
        innovations,
        alpha0=float(priors["M0"]["alpha0"]),
        beta0=float(priors["M0"]["beta0"]),
    )
    m1 = m1_posterior(
        innovations,
        mu0=float(priors["M1"]["mu0"]),
        kappa0=float(priors["M1"]["kappa0"]),
        alpha0=float(priors["M1"]["alpha0"]),
        beta0=float(priors["M1"]["beta0"]),
    )
    last_index = index_values[-1]
    m0_forecast = index_forecast(last_index, m0["predictive"])
    m1_forecast = index_forecast(last_index, m1["predictive"])

    OUTPUT.mkdir(parents=True, exist_ok=False)
    raw_path = OUTPUT / "eurostat_sts_es_c_through_2026_06.json"
    raw_path.write_bytes(raw_response)
    headers = {
        "captured_at_utc": captured_at,
        "request_url": query,
        "final_url": final_url,
        "http_status": status_code,
        "headers": response_headers,
        "raw_bytes": len(raw_response),
        "raw_sha256": digest_bytes(raw_response),
    }
    (OUTPUT / "response_headers.json").write_bytes(canonical_json_bytes(headers))
    normalized = {
        "schema": "hbp.eurostat.sts.es-c.training-series.v0.1",
        "source_updated": document["updated"],
        "jurisdiction": preregistration["jurisdiction"],
        "records": records,
        "record_count": len(records),
        "transition_count": len(innovations),
        "status_counts": {
            str(flag): sum(record["status"] == flag for record in records)
            for flag in sorted({record["status"] for record in records}, key=lambda value: str(value))
        },
    }
    (OUTPUT / "normalized_training_series.json").write_bytes(canonical_json_bytes(normalized))

    z_post = {
        "schema": "hbp.eurostat.sts.es-c.z-post.v0.1",
        "state": "INITIALIZED_PRE_OUTCOME_FROM_FROZEN_TRAINING_WINDOW",
        "jurisdiction": preregistration["jurisdiction"],
        "training_start": records[0]["time"],
        "training_end": records[-1]["time"],
        "target_month": preregistration["temporal_contract"]["target_month"],
        "observation_count": len(records),
        "transition_count": len(innovations),
        "M0": posterior_payload(m0),
        "M1": posterior_payload(m1),
        "weights": preregistration["weights"],
        "M2_port": preregistration["model_availability"]["M2_port"],
        "M2_ted": preregistration["model_availability"]["M2_ted"],
        "M3_coral": preregistration["model_availability"]["M3_coral"],
        "initialization_event": True,
        "batch_is_exactly_equivalent_to_sequential_conjugate_updates": True,
        "reset_occurred": False,
        "pooling_occurred": False,
        "Z_post_is_residual_z": False,
        "Z_post_is_Z_XPL": False,
        "source_raw_sha256": digest_bytes(raw_response),
        "preregistration_sha256": digest_bytes(preregistration_bytes),
    }
    z_post_path = OUTPUT / "posterior_z_post.json"
    z_post_path.write_bytes(canonical_json_bytes(z_post))

    freeze = {
        "schema": "hbp.eurostat.sts.es-c.forecast-freeze.v0.1",
        "status": "FROZEN_PRE_OUTCOME",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_month": preregistration["temporal_contract"]["target_month"],
        "last_observed_month": records[-1]["time"],
        "last_observed_index": last_index,
        "source_updated": document["updated"],
        "models": {
            "M0": {"state": "ESTIMABLE", **m0_forecast},
            "M1": {"state": "ESTIMABLE", **m1_forecast},
            "M2_port": {"state": preregistration["model_availability"]["M2_port"]},
            "M2_ted": {"state": preregistration["model_availability"]["M2_ted"]},
            "M3_coral": {"state": preregistration["model_availability"]["M3_coral"]},
        },
        "weights": preregistration["weights"],
        "outcome_opened": False,
        "target_requested_from_source": False,
        "global_winner": None,
        "automatic_promotion": False,
        "source_raw_sha256": digest_bytes(raw_response),
        "preregistration_sha256": digest_bytes(preregistration_bytes),
        "posterior_z_post_sha256": digest_file(z_post_path),
        "script_sha256": digest_file(Path(__file__)),
    }
    (OUTPUT / "forecast_freeze.json").write_bytes(canonical_json_bytes(freeze))

    manifest_paths = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    manifest = {
        "schema": "hbp.eurostat.sts.es-c.freeze-manifest.v0.1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": str(PREREGISTRATION.relative_to(REPOSITORY)).replace("\\", "/"),
        "files": [
            {
                "path": str(path.relative_to(REPOSITORY)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": digest_file(path),
            }
            for path in manifest_paths
        ],
        "target_outcome_opened": False,
        "global_winner": None,
    }
    (OUTPUT / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    print(canonical_json_bytes({
        "status": freeze["status"],
        "source_updated": freeze["source_updated"],
        "training_observations": len(records),
        "target_month": freeze["target_month"],
        "M0_point": m0_forecast["point_median_index"],
        "M1_point": m1_forecast["point_median_index"],
        "output": str(OUTPUT),
    }).decode("utf-8"), end="")


if __name__ == "__main__":
    main()

