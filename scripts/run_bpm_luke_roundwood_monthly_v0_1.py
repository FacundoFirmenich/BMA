from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from bma.experiments import bpm_luke_roundwood_monthly_v0_1 as engine


CAPTURE_RELATIVE = Path("evidence/runs/bpm-luke-roundwood-monthly-v0.1-history-capture")
RUN_RELATIVE = Path("evidence/runs/bpm-luke-roundwood-monthly-v0.1-causal")
PREREG_RELATIVE = Path("preregistrations/BPM_LUKE_ROUNDWOOD_MONTHLY_2020_2026_V0.1.json")
ADDENDUM_RELATIVE = Path("preregistrations/BPM_LUKE_ROUNDWOOD_MONTHLY_2020_2026_V0.1_SOFTWARE_ADDENDUM.json")
PREOPENED_TARGET = "2026-07"
PROSPECTIVE_TARGET = "2026-08"
EXPECTED_MONTH_CODES = [
    f"{year}M{month:02d}"
    for year in range(2020, 2027)
    for month in range(1, 13)
    if (year, month) <= (2026, 7)
]


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(payload))


def write_gzip_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(canonical_bytes(payload), compresslevel=9, mtime=0))


def resolved_repo(path: Path) -> Path:
    """Use the Windows extended-length namespace without changing relative custody paths."""
    resolved = path.resolve()
    extended_prefix = chr(92) * 2 + "?" + chr(92)
    if os.name == "nt" and not str(resolved).startswith(extended_prefix):
        return Path(extended_prefix + str(resolved))
    return resolved

def period(code: str) -> str:
    if len(code) != 7 or code[4] != "M":
        raise engine.GateFailure(f"invalid source month {code!r}")
    result = f"{code[:4]}-{code[5:]}"
    engine.month_index(result)
    return result


def serialize_state(state: engine.TargetState) -> dict[str, Any]:
    return {
        "target_id": state.target_id,
        "last_period": state.last_period,
        "updates": state.updates,
        "weights": dict(state.weights.log_evidence),
        "models": {
            model_id: {
                "precision": model.precision.tolist(),
                "information": model.information.tolist(),
                "a": model.a,
                "b": model.b,
                "updates": model.updates,
            }
            for model_id, model in state.models.items()
        },
    }


def freeze_payload(freeze: engine.FrozenPrediction) -> dict[str, Any]:
    components: dict[str, Any] = {}
    for model_id, predictive in freeze.components.items():
        lower, upper = predictive.interval(0.90)
        components[model_id] = {
            "transformed_location": predictive.location,
            "transformed_scale": predictive.scale,
            "degrees_of_freedom": predictive.degrees_of_freedom,
            "transformed_interval_90": [lower, upper],
            "raw_location": engine.inverse_transform(freeze.target_id, predictive.location),
            "raw_interval_90": [
                engine.inverse_transform(freeze.target_id, lower),
                engine.inverse_transform(freeze.target_id, upper),
            ],
        }
    return {
        "schema": "bpm-luke-roundwood-freeze/v0.1",
        "training_period": freeze.training_period,
        "target_period": freeze.target_period,
        "target_id": freeze.target_id,
        "previous_transformed_level": freeze.previous_level,
        "previous_transformed_delta": freeze.previous_delta,
        "bootstrap_seasonality": freeze.bootstrap_seasonality,
        "weights": freeze.weights,
        "components": components,
        "mixture_transformed_location": freeze.mixture_location,
        "mixture_raw_location": engine.inverse_transform(freeze.target_id, freeze.mixture_location),
        "mixture_interval": "NOT_ESTIMATED_MIXTURE_OF_STUDENT_T_COMPONENTS",
    }


def summarize(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["score_authority"]:
            grouped[row[key]].append(row)
    result: dict[str, Any] = {}
    for group, items in sorted(grouped.items()):
        result[group] = {
            "target_count": len(items),
            "targets": [item["target_period"] for item in items],
            "mean_log_score": {
                model_id: sum(item["component_log_scores"][model_id] for item in items) / len(items)
                for model_id in engine.MODEL_IDS
            },
            "mean_absolute_log_error": {
                model_id: sum(item["absolute_log_error"][model_id] for item in items) / len(items)
                for model_id in engine.MODEL_IDS
            },
            "mixture_mean_log_score": sum(item["mixture_log_score"] for item in items) / len(items),
            "mixture_mean_absolute_log_error": sum(item["mixture_absolute_log_error"] for item in items) / len(items),
            "persistence_mean_absolute_log_error": sum(item["persistence_absolute_log_error"] for item in items)
            / len(items),
            "winner": None,
            "authority": "DIAGNOSTIC_GROUP_SUMMARY_ONLY_TARGET_LOCAL_ROWS_REMAIN_PRIMARY",
        }
    return result


repo = resolved_repo(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd())
prereg_path = repo / PREREG_RELATIVE
addendum_path = repo / ADDENDUM_RELATIVE
capture_dir = repo / CAPTURE_RELATIVE
capture_manifest = json.loads((capture_dir / "capture_manifest.json").read_text(encoding="utf-8"))
raw_path = capture_dir / capture_manifest["response"]["path"]
if sha256_file(raw_path) != capture_manifest["response"]["sha256"]:
    raise RuntimeError("History response hash differs from capture manifest")
if sha256_file(prereg_path) != capture_manifest["preregistration"]["sha256"]:
    raise RuntimeError("Preregistration hash differs from capture manifest")
if sha256_file(addendum_path) != capture_manifest["software_addendum"]["sha256"]:
    raise RuntimeError("Software addendum hash differs from capture manifest")

final_dir = repo / RUN_RELATIVE
if final_dir.exists():
    raise RuntimeError(f"Immutable causal run already exists: {final_dir}")
staging = final_dir.parent / f".{final_dir.name}.staging-{uuid.uuid4().hex}"
staging.mkdir(parents=True, exist_ok=False)

raw = json.loads(raw_path.read_text(encoding="utf-8"))
if raw.get("id") != ["INFO", "M", "MPKH", "KAUP", "PTL"] or raw.get("size") != [2, 79, 1, 1, 1]:
    raise engine.GateFailure("captured cube differs from the frozen dimension contract")
months_index = raw["dimension"]["M"]["category"]["index"]
info_index = raw["dimension"]["INFO"]["category"]["index"]
ordered_month_codes = [code for code, _ in sorted(months_index.items(), key=lambda pair: pair[1])]
month_count = len(ordered_month_codes)
values = raw["value"]
if ordered_month_codes != EXPECTED_MONTH_CODES:
    raise engine.GateFailure("captured month support or order differs from the frozen contract")
if info_index != {"M3T": 0, "E_M3": 1}:
    raise engine.GateFailure("captured information order differs from the frozen contract")
if not isinstance(values, list) or len(values) != 2 * len(EXPECTED_MONTH_CODES):
    raise engine.GateFailure("captured value vector is not the frozen dense 158-cell panel")
status_values = raw.get("status")


def raw_cell(info_code: str, month_code: str) -> float | None:
    flat_index = info_index[info_code] * month_count + months_index[month_code]
    value = values[flat_index]
    return None if value is None else float(value)


def raw_status(info_code: str, month_code: str) -> str | None:
    if status_values is None:
        return None
    flat_index = info_index[info_code] * month_count + months_index[month_code]
    if isinstance(status_values, list):
        if len(status_values) != len(values):
            raise engine.GateFailure("source status vector does not match the value vector")
        value = status_values[flat_index]
    elif isinstance(status_values, dict):
        value = status_values.get(str(flat_index), status_values.get(flat_index))
    else:
        raise engine.GateFailure("unsupported source status representation")
    return None if value in {None, ""} else str(value)


structured: list[dict[str, Any]] = []
missing: list[dict[str, str]] = []
flagged: list[dict[str, str]] = []
for month_code in ordered_month_codes:
    volume_thousand = raw_cell("M3T", month_code)
    price = raw_cell("E_M3", month_code)
    volume_status = raw_status("M3T", month_code)
    price_status = raw_status("E_M3", month_code)
    if volume_thousand is None:
        missing.append({"period": period(month_code), "target": "volume"})
    if price is None:
        missing.append({"period": period(month_code), "target": "price"})
    if volume_status is not None:
        flagged.append({"period": period(month_code), "target": "volume", "status": volume_status})
    if price_status is not None:
        flagged.append({"period": period(month_code), "target": "price", "status": price_status})
    structured.append(
        {
            "period": period(month_code),
            "volume_thousand_m3": volume_thousand,
            "volume_m3": None if volume_thousand is None else volume_thousand * 1000.0,
            "price_eur_per_m3": price,
            "source_status": {"volume": volume_status, "price": price_status},
            "vintage": "CURRENT_SERIES_CAPTURE_NOT_HISTORICAL_FIRST_RELEASE",
        }
    )

if missing or flagged:
    for item in structured:
        write_json(staging / "structured_months" / f"month_{item['period']}.json", item)
    result = {
        "schema": "bpm-luke-roundwood-result/v0.1",
        "status": (
            "NOT_ESTIMABLE_INCOMPLETE_PANEL"
            if missing and not flagged
            else "NOT_ESTIMABLE_UNINTERPRETED_SOURCE_STATUS"
            if flagged and not missing
            else "NOT_ESTIMABLE_INCOMPLETE_AND_FLAGGED_PANEL"
        ),
        "missing": missing,
        "flagged": flagged,
        "fit_performed": False,
        "forecast_performed": False,
        "posterior_updated": False,
        "Z_post_updated": False,
        "global_winner": None,
        "automatic_promotion": False,
    }
    write_json(staging / "RESULT.json", result)
    os.replace(staging, final_dir)
    print(json.dumps(result, indent=2))
    raise SystemExit(0)

for item in structured:
    if item["volume_m3"] < 0.0 or item["price_eur_per_m3"] <= 0.0:
        raise engine.GateFailure(f"invalid physical observation at {item['period']}")
    write_json(staging / "structured_months" / f"month_{item['period']}.json", item)

states = {target_id: engine.TargetState.frozen_prior(target_id) for target_id in engine.TARGET_IDS}
for state in states.values():
    state.last_period = structured[0]["period"]
previous_levels = {
    "volume": engine.transform_observation("volume", structured[0]["volume_m3"]),
    "price": engine.transform_observation("price", structured[0]["price_eur_per_m3"]),
}
previous_deltas = {target_id: 0.0 for target_id in engine.TARGET_IDS}
sequence: list[dict[str, Any]] = []
score_rows: dict[str, list[dict[str, Any]]] = {target_id: [] for target_id in engine.TARGET_IDS}
year_last_prior: dict[str, dict[str, str]] = {}

for index in range(1, len(structured)):
    training_period = structured[index - 1]["period"]
    target_period = structured[index]["period"]
    engine.require_next_month(training_period, target_period)
    bootstrap = target_period.startswith("2020-")
    score_authority = target_period != PREOPENED_TARGET
    target_sequence: dict[str, Any] = {}
    for target_id in engine.TARGET_IDS:
        raw_key = "volume_m3" if target_id == "volume" else "price_eur_per_m3"
        realized_level = engine.transform_observation(target_id, structured[index][raw_key])
        freeze = states[target_id].freeze_prediction(
            training_period,
            target_period,
            previous_levels[target_id],
            previous_deltas[target_id],
            bootstrap_seasonality=bootstrap,
        )
        frozen = freeze_payload(freeze)
        freeze_path = staging / "freezes" / f"freeze_{target_period}_{target_id}.json"
        write_json(freeze_path, frozen)
        component_scores = freeze.component_log_scores(realized_level)
        mixture_score = freeze.mixture_log_score(realized_level)
        point_locations = {model_id: predictive.location for model_id, predictive in freeze.components.items()}
        adjudication = {
            "schema": "bpm-luke-roundwood-adjudication/v0.1",
            "training_period": training_period,
            "target_period": target_period,
            "target_id": target_id,
            "classification": (
                "OPENED_PRE_CAMPAIGN_PROBE_EXCLUDED_FROM_WEIGHT_AND_SCORE_AGGREGATES"
                if not score_authority
                else "RETROSPECTIVE_SEQUENTIAL_DEVELOPMENT"
            ),
            "score_authority": score_authority,
            "realized_transformed_level": realized_level,
            "realized_raw_value": structured[index][raw_key],
            "component_log_scores": component_scores,
            "mixture_log_score": mixture_score,
            "absolute_log_error": {
                model_id: abs(realized_level - location) for model_id, location in point_locations.items()
            },
            "mixture_absolute_log_error": abs(realized_level - freeze.mixture_location),
            "persistence_absolute_log_error": abs(realized_level - previous_levels[target_id]),
            "winner": None,
            "global_winner": None,
            "automatic_promotion": False,
        }
        adjudication_path = staging / "adjudications" / f"adjudication_{target_period}_{target_id}.json"
        write_json(adjudication_path, adjudication)
        states[target_id].update_after_adjudication(
            freeze,
            realized_level,
            update_weight_evidence=score_authority,
        )
        posterior = serialize_state(states[target_id])
        prior_path = staging / "priors" / f"prior_after_{target_period}_{target_id}.json.gz"
        write_gzip_json(prior_path, posterior)
        prior_hash = sha256_file(prior_path)
        z_post = {
            "schema": "bpm-luke-roundwood-Z_post/v0.1",
            "target_period": target_period,
            "target_id": target_id,
            "posterior_path": prior_path.relative_to(staging).as_posix(),
            "posterior_sha256": prior_hash,
            "posterior_updates": states[target_id].updates,
            "weight_evidence_updated": score_authority,
            "next_period_only": True,
            "raw_to_prior": False,
            "reset": False,
        }
        z_path = staging / "z_post" / f"z_post_{target_period}_{target_id}.json"
        write_json(z_path, z_post)
        target_sequence[target_id] = {
            "freeze": freeze_path.relative_to(staging).as_posix(),
            "freeze_sha256": sha256_file(freeze_path),
            "adjudication": adjudication_path.relative_to(staging).as_posix(),
            "adjudication_sha256": sha256_file(adjudication_path),
            "prior": prior_path.relative_to(staging).as_posix(),
            "prior_sha256": prior_hash,
            "z_post": z_path.relative_to(staging).as_posix(),
            "z_post_sha256": sha256_file(z_path),
        }
        score_rows[target_id].append(
            {
                **adjudication,
                "year": target_period[:4],
                "phase": target_period[-2:],
            }
        )
        previous_deltas[target_id] = realized_level - previous_levels[target_id]
        previous_levels[target_id] = realized_level
    sequence.append({"training_period": training_period, "target_period": target_period, "targets": target_sequence})
    year_last_prior[target_period[:4]] = {
        target_id: target_sequence[target_id]["prior_sha256"] for target_id in engine.TARGET_IDS
    }

for year, hashes in sorted(year_last_prior.items()):
    write_json(
        staging / "checkpoints" / f"year_{year}.json",
        {
            "schema": "bpm-luke-roundwood-year-checkpoint/v0.1",
            "year": year,
            "last_prior_sha256_by_target": hashes,
            "no_reset": True,
            "global_winner": None,
        },
    )

future_freezes: dict[str, Any] = {}
for target_id in engine.TARGET_IDS:
    freeze = states[target_id].freeze_prediction(
        "2026-07",
        PROSPECTIVE_TARGET,
        previous_levels[target_id],
        previous_deltas[target_id],
        bootstrap_seasonality=False,
    )
    future_freezes[target_id] = freeze_payload(freeze)

forecast = {
    "schema": "bpm-luke-roundwood-prospective-forecast/v0.1",
    "jurisdiction": "Finland|WHOLE_COUNTRY|Standing_sales|Spruce_logs",
    "training_terminal_period": "2026-07",
    "target_period": PROSPECTIVE_TARGET,
    "target_opened": False,
    "target_available_in_raw_capture": False,
    "targets": future_freezes,
    "classification": "PROSPECTIVE_FIRST_RELEASE_TARGET_PENDING",
    "global_winner": None,
    "automatic_promotion": False,
}
write_json(staging / "FORECAST_2026-08.json", forecast)
write_json(staging / "SEQUENCE.json", {"schema": "bpm-luke-roundwood-sequence/v0.1", "targets": sequence})
result = {
    "schema": "bpm-luke-roundwood-result/v0.1",
    "status": "RETROSPECTIVE_REPLAY_COMPLETE_PROSPECTIVE_2026_08_FROZEN",
    "jurisdiction": forecast["jurisdiction"],
    "history": {"first_month": structured[0]["period"], "last_month": structured[-1]["period"], "month_count": len(structured)},
    "target_count": len(sequence),
    "scored_target_count": len(sequence) - 1,
    "preopened_targets_excluded_from_weights_and_aggregates": [PREOPENED_TARGET],
    "target_local_rows": score_rows,
    "year_diagnostics": {target_id: summarize(rows, "year") for target_id, rows in score_rows.items()},
    "calendar_phase_diagnostics": {target_id: summarize(rows, "phase") for target_id, rows in score_rows.items()},
    "prospective_forecast": "FORECAST_2026-08.json",
    "global_winner": None,
    "automatic_promotion": False,
}
write_json(staging / "RESULT.json", result)

manifest_entries: list[dict[str, Any]] = []
for path in sorted(staging.rglob("*")):
    if path.is_file() and path.name != "MANIFEST.json":
        manifest_entries.append(
            {"path": path.relative_to(staging).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        )
manifest = {
    "schema": "bpm-luke-roundwood-causal-manifest/v0.1",
    "preregistration_sha256": sha256_file(prereg_path),
    "software_addendum_sha256": sha256_file(addendum_path),
    "capture_manifest_sha256": sha256_file(capture_dir / "capture_manifest.json"),
    "artifact_count_excluding_manifest": len(manifest_entries),
    "artifacts": manifest_entries,
}
write_json(staging / "MANIFEST.json", manifest)
os.replace(staging, final_dir)
print(
    json.dumps(
        {
            "run": RUN_RELATIVE.as_posix(),
            "status": result["status"],
            "target_count": result["target_count"],
            "scored_target_count": result["scored_target_count"],
            "forecast": forecast["target_period"],
        },
        indent=2,
    )
)
