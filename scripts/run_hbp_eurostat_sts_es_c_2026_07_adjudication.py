"""Capture and, only if published, adjudicate Eurostat STS Spain July 2026."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bma.experiments.hbp_eurostat_sts_v0_1 import (
    GateFailure,
    index_forecast,
    log_innovations,
    m0_posterior,
    m1_posterior,
    score_index_observation,
    update_weights_from_log_scores,
)


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "preregistrations" / "HBP_EUROSTAT_STS_ES_C_2026_07_ADJUDICATION_V0.1.json"
PARENT = ROOT / "evidence" / "runs" / "hbp-eurostat-sts-es-c-v0.1-2026-07-freeze"
OUTPUT = ROOT / "evidence" / "runs" / "hbp-eurostat-sts-es-c-v0.1-2026-07-adjudication-20260822"


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sparse(payload: object | None) -> dict[int, object]:
    if payload is None:
        return {}
    if isinstance(payload, list):
        return {index: value for index, value in enumerate(payload) if value is not None}
    if isinstance(payload, dict):
        return {int(index): value for index, value in payload.items()}
    raise GateFailure("unsupported Eurostat sparse representation")


def positions(document: dict, dimension: str) -> dict[int, str]:
    index = document["dimension"][dimension]["category"]["index"]
    if isinstance(index, list):
        return {position: code for position, code in enumerate(index)}
    return {int(position): code for code, position in index.items()}


def validate_parent(prereg: dict) -> tuple[dict, dict, dict]:
    if digest_file(PARENT / "forecast_freeze.json") != prereg["parent_freeze_sha256"]:
        raise GateFailure("parent Eurostat forecast freeze hash mismatch")
    manifest = json.loads((PARENT / "manifest.json").read_text(encoding="utf-8"))
    for record in manifest["files"]:
        path = ROOT / record["path"]
        if digest_file(path) != record["sha256"] or path.stat().st_size != record["bytes"]:
            raise GateFailure(f"parent manifest mismatch: {record['path']}")
    freeze = json.loads((PARENT / "forecast_freeze.json").read_text(encoding="utf-8"))
    series = json.loads((PARENT / "normalized_training_series.json").read_text(encoding="utf-8"))
    parent_prereg = json.loads(
        (ROOT / "preregistrations" / "HBP_EUROSTAT_STS_ES_C_2026_07_FREEZE_V0.1.json").read_text(
            encoding="utf-8"
        )
    )
    if freeze["target_month"] != "2026-07" or freeze["outcome_opened"] is not False:
        raise GateFailure("parent is not the unopened July 2026 freeze")
    return freeze, series, parent_prereg


def extract_target(document: dict) -> tuple[str, float | None, str | None]:
    if document.get("id") != ["freq", "indic_bt", "nace_r2", "s_adj", "unit", "geo", "time"]:
        raise GateFailure(f"unexpected Eurostat dimension order: {document.get('id')!r}")
    expected = {
        "freq": "M",
        "indic_bt": "PRD",
        "nace_r2": "C",
        "s_adj": "SCA",
        "unit": "I21",
        "geo": "ES",
    }
    for dimension, code in expected.items():
        if positions(document, dimension) != {0: code}:
            raise GateFailure(f"unexpected target dimension {dimension}")
    time_positions = positions(document, "time")
    if time_positions not in ({}, {0: "2026-07"}):
        raise GateFailure(f"unexpected target time positions: {time_positions!r}")
    values = sparse(document.get("value"))
    flags = sparse(document.get("status"))
    if not values:
        return "OUTCOME_PENDING", None, None
    if set(values) != {0} or time_positions != {0: "2026-07"}:
        raise GateFailure("Eurostat target response is not exactly one July cell")
    value = float(values[0])
    if value <= 0.0:
        return "NOT_ESTIMABLE_NONPOSITIVE", None, str(flags.get(0)) if 0 in flags else None
    return "OUTCOME_AVAILABLE", value, str(flags.get(0)) if 0 in flags else None


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
        raise GateFailure(f"immutable output already exists: {OUTPUT}")
    prereg_bytes = PREREG.read_bytes()
    prereg = json.loads(prereg_bytes.decode("utf-8-sig"))
    freeze, series, parent_prereg = validate_parent(prereg)
    request = Request(prereg["target_query"], headers={"User-Agent": "BMA-HBP-evidence-custody/0.1"})
    captured_at = datetime.now(timezone.utc).isoformat()
    with urlopen(request, timeout=60) as response:
        raw = response.read(prereg["capture_contract"]["max_response_bytes"] + 1)
        headers = {key: value for key, value in response.headers.items()}
        status_code = response.status
        final_url = response.geturl()
    if len(raw) > prereg["capture_contract"]["max_response_bytes"]:
        raise GateFailure("Eurostat target response exceeded bounded size")
    if status_code != 200:
        raise GateFailure(f"unexpected Eurostat HTTP status: {status_code}")
    document = json.loads(raw.decode("utf-8-sig"))
    outcome_state, actual, flag = extract_target(document)

    OUTPUT.mkdir(parents=True, exist_ok=False)
    raw_path = OUTPUT / "eurostat_sts_es_c_2026_07.json"
    raw_path.write_bytes(raw)
    capture = {
        "captured_at_utc": captured_at,
        "request_url": prereg["target_query"],
        "final_url": final_url,
        "http_status": status_code,
        "headers": headers,
        "raw_bytes": len(raw),
        "raw_sha256": digest_bytes(raw),
        "source_updated": document.get("updated"),
    }
    (OUTPUT / "response_headers.json").write_bytes(json_bytes(capture))
    adjudication = {
        "schema": "hbp.eurostat.sts.es-c.adjudication.v0.1",
        "target_month": "2026-07",
        "outcome_state": outcome_state,
        "actual_index": actual,
        "status_flag": flag,
        "parent_freeze_sha256": digest_file(PARENT / "forecast_freeze.json"),
        "target_raw_sha256": digest_bytes(raw),
        "posterior_updated": False,
        "next_target_frozen": False,
        "global_winner": None,
        "automatic_promotion": False,
    }

    if outcome_state == "OUTCOME_AVAILABLE" and actual is not None:
        scores = {
            model: score_index_observation(actual, freeze["models"][model]) for model in ("M0", "M1")
        }
        prior_weights = {model: float(freeze["weights"][model]) for model in ("M0", "M1")}
        future_weights = update_weights_from_log_scores(
            prior_weights,
            {model: float(scores[model]["log_score_index_density"]) for model in scores},
        )
        all_values = [float(record["value"]) for record in series["records"]] + [actual]
        innovations = log_innovations(all_values)
        priors = parent_prereg["priors"]
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
        z_post = {
            "schema": "hbp.eurostat.sts.es-c.z-post.v0.2",
            "state": "CLOSED_2026_07_OPEN_2026_08",
            "previous_z_post_sha256": digest_file(PARENT / "posterior_z_post.json"),
            "new_information_count": 1,
            "closed_outcome": {"time": "2026-07", "value": actual, "status": flag},
            "M0": posterior_payload(m0),
            "M1": posterior_payload(m1),
            "weights": future_weights,
            "reset_occurred": False,
            "pooling_occurred": False,
            "Z_post_is_residual_z": False,
            "Z_post_is_Z_XPL": False,
        }
        z_path = OUTPUT / "closed_posterior_z_post.json"
        z_path.write_bytes(json_bytes(z_post))
        next_freeze = {
            "schema": "hbp.eurostat.sts.es-c.forecast-freeze.v0.2",
            "status": "FROZEN_PRE_OUTCOME",
            "issued_at_utc": datetime.now(timezone.utc).isoformat(),
            "target_month": "2026-08",
            "last_observed_month": "2026-07",
            "last_observed_index": actual,
            "models": {
                "M0": {"state": "ESTIMABLE", **index_forecast(actual, m0["predictive"])},
                "M1": {"state": "ESTIMABLE", **index_forecast(actual, m1["predictive"])},
                "M2_port": {"state": prereg["continuation"]["M2_port"]},
                "M2_ted": {"state": prereg["continuation"]["M2_ted"]},
                "M3_coral": {"state": prereg["continuation"]["M3_coral"]},
            },
            "weights": future_weights,
            "outcome_opened": False,
            "global_winner": None,
            "automatic_promotion": False,
            "closed_posterior_z_post_sha256": digest_file(z_path),
        }
        (OUTPUT / "next_forecast_freeze_2026_08.json").write_bytes(json_bytes(next_freeze))
        adjudication.update(
            {
                "scores": scores,
                "future_weights": future_weights,
                "posterior_updated": True,
                "next_target_frozen": True,
            }
        )
    (OUTPUT / "adjudication.json").write_bytes(json_bytes(adjudication))

    paths = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    manifest = {
        "schema": "hbp.eurostat.sts.es-c.adjudication-manifest.v0.1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration_sha256": digest_bytes(prereg_bytes),
        "files": [
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": digest_file(path),
            }
            for path in paths
        ],
        "outcome_state": outcome_state,
        "posterior_updated": adjudication["posterior_updated"],
        "next_target_frozen": adjudication["next_target_frozen"],
        "global_winner": None,
    }
    (OUTPUT / "manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"outcome_state": outcome_state, "actual": actual, "posterior_updated": adjudication["posterior_updated"], "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
