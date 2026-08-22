from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


RUN_RELATIVE = Path("evidence/runs/bpm-luke-roundwood-monthly-v0.1-causal")
CAPTURE_RELATIVE = Path("evidence/runs/bpm-luke-roundwood-monthly-v0.1-history-capture")
OUTPUT_RELATIVE = Path("outputs/BPM_LUKE_ROUNDWOOD_MONTHLY_LOCAL_CARTOGRAPHY_20260822.json")
MODEL_IDS = ("M0", "M1", "M2")
TARGETS = {"volume": "volume_m3", "price": "price_eur_per_m3"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def harmonic(month: int) -> np.ndarray:
    phase = 2.0 * math.pi * (month - 1) / 12.0
    return np.asarray(
        [math.sin(phase), math.cos(phase), math.sin(2.0 * phase), math.cos(2.0 * phase)],
        dtype=float,
    )


def month_residual(month: int) -> np.ndarray:
    if month == 12:
        return np.full(11, -1.0, dtype=float)
    result = np.zeros(11, dtype=float)
    result[month - 1] = 1.0
    return result


repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
run = repo / RUN_RELATIVE
capture = repo / CAPTURE_RELATIVE
output = repo / OUTPUT_RELATIVE
if output.exists():
    raise RuntimeError(f"Immutable cartography already exists: {output}")

manifest_path = run / "MANIFEST.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
failures: list[str] = []
for item in manifest["artifacts"]:
    path = run / item["path"]
    if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
        failures.append(item["path"])
if failures:
    raise RuntimeError(f"Run manifest integrity failures: {failures}")

result = json.loads((run / "RESULT.json").read_text(encoding="utf-8"))
forecast = json.loads((run / "FORECAST_2026-08.json").read_text(encoding="utf-8"))
months = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((run / "structured_months").glob("*.json"))]
if result["status"] != "RETROSPECTIVE_REPLAY_COMPLETE_PROSPECTIVE_2026_08_FROZEN":
    raise RuntimeError("Luke run is not in the frozen terminal state")

cartography: dict[str, Any] = {}
for target_id, raw_key in TARGETS.items():
    all_rows = result["target_local_rows"][target_id]
    rows = [row for row in all_rows if row["score_authority"]]
    whole = {
        "classification": "DIAGNOSTIC_WHOLE_HISTORY_NO_GLOBAL_AUTHORITY",
        "scored_months": len(rows),
        "mean_log_score": {
            model_id: mean([row["component_log_scores"][model_id] for row in rows]) for model_id in MODEL_IDS
        },
        "mean_absolute_log_error": {
            model_id: mean([row["absolute_log_error"][model_id] for row in rows]) for model_id in MODEL_IDS
        },
        "mixture_mean_log_score": mean([row["mixture_log_score"] for row in rows]),
        "mixture_mean_absolute_log_error": mean([row["mixture_absolute_log_error"] for row in rows]),
        "persistence_mean_absolute_log_error": mean([row["persistence_absolute_log_error"] for row in rows]),
    }
    whole["relative_absolute_error_reduction_vs_M0"] = {
        model_id: (whole["mean_absolute_log_error"]["M0"] - whole["mean_absolute_log_error"][model_id])
        / whole["mean_absolute_log_error"]["M0"]
        for model_id in ("M1", "M2")
    }
    whole["relative_absolute_error_reduction_vs_persistence"] = {
        model_id: (whole["persistence_mean_absolute_log_error"] - whole["mean_absolute_log_error"][model_id])
        / whole["persistence_mean_absolute_log_error"]
        for model_id in MODEL_IDS
    }

    phase_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        phase_rows[row["phase"]].append(row)
    physical_changes: dict[str, list[float]] = defaultdict(list)
    for previous, current in zip(months, months[1:]):
        if target_id == "volume":
            delta = math.log1p(current[raw_key]) - math.log1p(previous[raw_key])
        else:
            delta = math.log(current[raw_key]) - math.log(previous[raw_key])
        physical_changes[current["period"][-2:]].append(delta)

    prior_path = run / "priors" / f"prior_after_2026-07_{target_id}.json.gz"
    with gzip.open(prior_path, "rt", encoding="utf-8") as handle:
        final_state = json.load(handle)
    posterior_means: dict[str, np.ndarray] = {}
    for model_id in ("M1", "M2"):
        model = final_state["models"][model_id]
        posterior_means[model_id] = np.linalg.solve(
            np.asarray(model["precision"], dtype=float),
            np.asarray(model["information"], dtype=float),
        )

    phases: dict[str, Any] = {}
    for phase in [f"{month:02d}" for month in range(1, 13)]:
        items = phase_rows[phase]
        changes = physical_changes[phase]
        phase_summary: dict[str, Any] = {
            "scored_year_replicates": len(items),
            "physical_current_series_replicates": len(changes),
            "physical_positive_change_count": sum(value > 0.0 for value in changes),
            "physical_mean_log_change": mean(changes),
            "physical_median_log_change": float(np.median(np.asarray(changes))),
            "physical_approx_mean_percent_change": 100.0 * math.expm1(mean(changes)),
            "models_vs_M0": {},
            "final_posterior_calendar_contribution": {},
        }
        for model_id in ("M1", "M2"):
            phase_summary["models_vs_M0"][model_id] = {
                "mean_log_score_delta": mean(
                    [item["component_log_scores"][model_id] - item["component_log_scores"]["M0"] for item in items]
                ),
                "mean_absolute_error_reduction": mean(
                    [item["absolute_log_error"]["M0"] - item["absolute_log_error"][model_id] for item in items]
                ),
                "log_score_better_count": sum(
                    item["component_log_scores"][model_id] > item["component_log_scores"]["M0"] for item in items
                ),
                "absolute_error_better_count": sum(
                    item["absolute_log_error"][model_id] < item["absolute_log_error"]["M0"] for item in items
                ),
                "both_better_count": sum(
                    item["component_log_scores"][model_id] > item["component_log_scores"]["M0"]
                    and item["absolute_log_error"][model_id] < item["absolute_log_error"]["M0"]
                    for item in items
                ),
            }
            month_number = int(phase)
            coefficients = posterior_means[model_id]
            contribution = float(harmonic(month_number) @ coefficients[2:6])
            if model_id == "M2":
                contribution += float(month_residual(month_number) @ coefficients[6:17])
            phase_summary["final_posterior_calendar_contribution"][model_id] = {
                "posterior_mean_log_innovation": contribution,
                "approx_percent_level_multiplier": 100.0 * math.expm1(contribution),
                "uncertainty_interval": "NOT_COMPUTED_POST_OUTCOME_DESCRIPTIVE_ONLY",
            }
        phases[phase] = phase_summary

    years: dict[str, Any] = {}
    for year, data in result["year_diagnostics"][target_id].items():
        years[year] = {
            "target_count": data["target_count"],
            "M0_mean_absolute_log_error": data["mean_absolute_log_error"]["M0"],
            "persistence_mean_absolute_log_error": data["persistence_mean_absolute_log_error"],
            "models_vs_M0": {
                model_id: {
                    "mean_log_score_delta": data["mean_log_score"][model_id] - data["mean_log_score"]["M0"],
                    "mean_absolute_error_reduction": data["mean_absolute_log_error"]["M0"]
                    - data["mean_absolute_log_error"][model_id],
                }
                for model_id in ("M1", "M2")
            },
        }

    cartography[target_id] = {
        "whole_history_diagnostic": whole,
        "year_diagnostics": years,
        "calendar_phase_cartography": phases,
        "prospective_2026_08": {
            "weights": forecast["targets"][target_id]["weights"],
            "components": forecast["targets"][target_id]["components"],
            "mixture_raw_location": forecast["targets"][target_id]["mixture_raw_location"],
            "mixture_interval": forecast["targets"][target_id]["mixture_interval"],
        },
    }

directory_counts = Counter(item["path"].split("/")[0] for item in manifest["artifacts"])
payload = {
    "schema": "bpm-luke-roundwood-local-cartography/v0.1",
    "date": "2026-08-22",
    "classification": "POST_OUTCOME_DESCRIPTIVE_DERIVATIVE_NO_MODEL_SELECTION_OR_AUTHORITY_PROMOTION",
    "jurisdiction": result["jurisdiction"],
    "source_evidence": {
        "capture_manifest": {
            "path": (CAPTURE_RELATIVE / "capture_manifest.json").as_posix(),
            "sha256": sha256_file(capture / "capture_manifest.json"),
        },
        "run_manifest": {"path": (RUN_RELATIVE / "MANIFEST.json").as_posix(), "sha256": sha256_file(manifest_path)},
        "result": {"path": (RUN_RELATIVE / "RESULT.json").as_posix(), "sha256": sha256_file(run / "RESULT.json")},
        "forecast": {
            "path": (RUN_RELATIVE / "FORECAST_2026-08.json").as_posix(),
            "sha256": sha256_file(run / "FORECAST_2026-08.json"),
        },
    },
    "integrity": {
        "manifest_artifacts": len(manifest["artifacts"]),
        "manifest_failures": failures,
        "directory_counts": dict(directory_counts),
        "retrospective_transitions": result["target_count"],
        "scored_transitions_per_target": result["scored_target_count"],
        "preopened_exclusion": result["preopened_targets_excluded_from_weights_and_aggregates"],
    },
    "targets": cartography,
    "limits": [
        "current revised series, not historical first-release vintages",
        "2026-07 excluded from weight and score aggregates because it was opened in the prior probe",
        "calendar phase has only six or seven year replicates",
        "posterior calendar contribution intervals were not preregistered and are not computed here",
        "mixture predictive interval is not estimated",
        "whole-history, year and phase summaries are diagnostic and cannot create a global winner",
    ],
    "global_winner": None,
    "automatic_promotion": False,
}
output.parent.mkdir(parents=True, exist_ok=True)
staging = output.with_name(f".{output.name}.staging-{uuid.uuid4().hex}")
staging.write_bytes(canonical_bytes(payload))
os.replace(staging, output)
print(json.dumps({"output": OUTPUT_RELATIVE.as_posix(), "sha256": sha256_file(output)}, indent=2))
