#!/usr/bin/env python3
"""Stratified v0.5.1 audit of the frozen Mercabarna Flor v0.5.0 replay.

This module does not refit or rewrite v0.5.0. It freezes a product taxonomy
from the 2026-07-01..20 training universe, then stratifies already-frozen
participation and quantity scores for 2026-07-21..31.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from bma.custody import sha256_file, write_json_new, write_manifest
from bma.experiments import mercabarna_flor_v0_5_0 as base
from bma.taxonomy import CATEGORIES, classify_product

SCHEMA = "bma.mercabarna.flor.subfamily-audit.v0.5.1"
MIN_PARTICIPATION_N = 100
MIN_QUANTITY_N = 30
PRIMARY_REGIME = "ORDINARY"


class GateFailure(RuntimeError):
    pass


def mean(items: list[float]) -> float | None:
    return float(np.mean(items)) if items else None


def evidence_status(n: int, minimum: int, bma: float | None, comparators: list[float | None]) -> str:
    if n < minimum:
        return "NOT_ESTIMABLE_INSUFFICIENT_SUPPORT"
    if bma is None or any(value is None for value in comparators):
        return "NOT_ESTIMABLE_MISSING_COMPARATOR"
    if all(bma < float(value) for value in comparators):
        return "FAVOURABLE_DESCRIPTIVE_ONLY"
    return "MIXED_OR_ADVERSE_ABSTAIN"


def summarize_participation(records: list[dict[str, Any]]) -> dict[str, Any]:
    bma_brier = mean([float(row["bma_brier"]) for row in records])
    frozen_brier = mean([float(row["origin_frozen_brier"]) for row in records])
    bma_log = mean([float(row["bma_log_loss"]) for row in records])
    frozen_log = mean([float(row["origin_frozen_log_loss"]) for row in records])
    return {
        "n": len(records),
        "positive": sum(int(row["actual"]) for row in records),
        "bma_mean_brier": bma_brier,
        "origin_frozen_mean_brier": frozen_brier,
        "bma_mean_log_loss": bma_log,
        "origin_frozen_mean_log_loss": frozen_log,
        "relative_gain_brier_pct": (
            100.0 * (float(frozen_brier) - float(bma_brier)) / float(frozen_brier)
            if bma_brier is not None and frozen_brier not in (None, 0.0)
            else None
        ),
        "status": evidence_status(len(records), MIN_PARTICIPATION_N, bma_brier, [frozen_brier]),
    }


def summarize_quantity(records: list[dict[str, Any]]) -> dict[str, Any]:
    items = [row["quantity"] for row in records]
    bma = mean([float(item["bma_error"]) for item in items])
    persistence = mean([float(item["persistence_error"]) for item in items])
    frozen = mean([float(item["origin_frozen_error"]) for item in items])
    strong_items = [float(item["strong_error"]) for item in items if item["strong_error"] is not None]
    strong = mean(strong_items)
    return {
        "n": len(items),
        "strong_n": len(strong_items),
        "bma_mean_error": bma,
        "origin_frozen_mean_error": frozen,
        "persistence_mean_error": persistence,
        "strong_mean_error": strong,
        "wins_vs_persistence": sum(item["bma_vs_persistence"] == "LOCAL_WIN" for item in items),
        "losses_vs_persistence": sum(item["bma_vs_persistence"] == "LOCAL_LOSS" for item in items),
        "wins_vs_strong": sum(item["bma_vs_strong"] == "LOCAL_WIN" for item in items),
        "losses_vs_strong": sum(item["bma_vs_strong"] == "LOCAL_LOSS" for item in items),
        "relative_gain_vs_persistence_pct": (
            100.0 * (float(persistence) - float(bma)) / float(persistence)
            if bma is not None and persistence not in (None, 0.0)
            else None
        ),
        "relative_gain_vs_strong_pct": (
            100.0 * (float(strong) - float(bma)) / float(strong)
            if bma is not None and strong not in (None, 0.0)
            else None
        ),
        "status": evidence_status(len(items), MIN_QUANTITY_N, bma, [frozen, persistence, strong]),
    }


def run(training_root: Path, source_run: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise GateFailure(f"immutable output already exists: {output}")
    output.mkdir(parents=True)

    training = [base.load_training_day(training_root, day) for day in base.days(base.TRAIN_START, base.TRAIN_END)]
    training_rows = [row for document in training for row in document["rows"]]
    products = sorted({str(row["product"]) for row in training_rows})
    decisions = {product: classify_product(product) for product in products}
    cells: dict[str, dict[str, str]] = {}
    for row in training_rows:
        cell_id = str(row["cell_id"])
        item = {"product": str(row["product"]), "origin_code": str(row["origin_code"])}
        if cell_id in cells and cells[cell_id] != item:
            raise GateFailure(f"inconsistent training metadata for {cell_id}")
        cells[cell_id] = item

    counts = Counter(decision.subfamily for decision in decisions.values())
    if set(counts) - set(CATEGORIES):
        raise GateFailure("taxonomy emitted an undeclared category")
    taxonomy = {
        "schema_version": SCHEMA,
        "status": "FROZEN_TRAINING_ONLY_TAXONOMY",
        "training_range": [base.TRAIN_START.isoformat(), base.TRAIN_END.isoformat()],
        "training_product_count": len(products),
        "mapping_uses_target_records": False,
        "unknown_product_policy": "UNRESOLVED_NO_INFERENCE",
        "categories": list(CATEGORIES),
        "product_counts": {category: counts.get(category, 0) for category in CATEGORIES},
        "entries": [decisions[product].serializable() for product in products],
    }
    taxonomy_hash = write_json_new(output / "TAXONOMY_FREEZE.json", taxonomy)

    summary_path = source_run / "RESULT_SUMMARY.json"
    participation_path = source_run / "PARTICIPATION_SCORES.json"
    quantity_path = source_run / "QUANTITY_SCORES.json"
    source_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if source_summary.get("schema_version") != base.SCHEMA:
        raise GateFailure("source replay is not Mercabarna Flor v0.5.0")
    participation = json.loads(participation_path.read_text(encoding="utf-8"))["scores"]
    quantity = json.loads(quantity_path.read_text(encoding="utf-8"))["scores"]

    enriched_participation: list[dict[str, Any]] = []
    for row in participation:
        metadata = cells.get(str(row["cell_id"]))
        if metadata is None:
            raise GateFailure(f"participation cell outside frozen training universe: {row['cell_id']}")
        enriched_participation.append({**row, **metadata, "subfamily": decisions[metadata["product"]].subfamily})
    enriched_quantity: list[dict[str, Any]] = []
    out_of_training_quantity_cells: set[str] = set()
    out_of_training_new_products: set[str] = set()
    for row in quantity:
        metadata = cells.get(str(row["cell_id"]))
        if metadata is None:
            origin_code, separator, product = str(row["cell_id"]).partition("|")
            if not separator or not origin_code or not product:
                raise GateFailure(f"invalid quantity cell identifier: {row['cell_id']}")
            metadata = {"product": product, "origin_code": origin_code}
            out_of_training_quantity_cells.add(str(row["cell_id"]))
            if product not in decisions:
                out_of_training_new_products.add(product)
        decision = decisions.get(metadata["product"], classify_product(metadata["product"]))
        enriched_quantity.append({**row, **metadata, "subfamily": decision.subfamily})

    def stratify(records: list[dict[str, Any]], summarizer: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for category in CATEGORIES:
            category_rows = [row for row in records if row["subfamily"] == category]
            result[category] = {
                "all_target_regimes": summarizer(category_rows),
                "ordinary": summarizer([row for row in category_rows if row["regime"] == PRIMARY_REGIME]),
                "by_regime": {
                    regime: summarizer([row for row in category_rows if row["regime"] == regime])
                    for regime in sorted({str(row["regime"]) for row in category_rows})
                },
            }
        return result

    participation_by = stratify(enriched_participation, summarize_participation)
    quantity_by = stratify(enriched_quantity, summarize_quantity)
    result = {
        "schema_version": SCHEMA,
        "status": "EXECUTED_RETROSPECTIVE_STRATIFIED_AUDIT",
        "source_replay": {
            "schema_version": source_summary["schema_version"],
            "result_summary_sha256": sha256_file(summary_path),
            "participation_scores_sha256": sha256_file(participation_path),
            "quantity_scores_sha256": sha256_file(quantity_path),
        },
        "taxonomy": {
            "freeze_sha256": taxonomy_hash,
            "mapping_uses_target_records": False,
            "unresolved_products": sorted(
                decision.product for decision in decisions.values() if decision.subfamily == "UNRESOLVED"
            ),
            "out_of_training_quantity_cells": sorted(out_of_training_quantity_cells),
            "out_of_training_new_products": sorted(out_of_training_new_products),
        },
        "support_thresholds": {
            "participation_n": MIN_PARTICIPATION_N,
            "quantity_n": MIN_QUANTITY_N,
            "role": "minimum descriptive support; not a power calculation",
        },
        "participation_by_subfamily": participation_by,
        "quantity_by_subfamily": quantity_by,
        "claim_boundary": {
            "prospective_evidence": False,
            "taxonomy_is_target_blind": True,
            "refit_performed": False,
            "global_superiority": False,
            "commercial_validation": False,
            "price": "DEGENERATE_METRIC_VETO_INHERITED_FROM_V0.5.0",
            "ordinary_results": "RETROSPECTIVE_DESCRIPTIVE_DEVELOPMENT_EVIDENCE",
            "saturday_and_month_end": "ABSTAIN_INHERITED_FROM_V0.5.0",
        },
    }
    write_json_new(output / "PARTICIPATION_BY_SUBFAMILY.json", {"schema_version": SCHEMA, "results": participation_by})
    write_json_new(output / "QUANTITY_BY_SUBFAMILY.json", {"schema_version": SCHEMA, "results": quantity_by})
    write_json_new(output / "RESULT_SUMMARY.json", result)
    _, manifest_hash = write_manifest(output)
    return {**result, "manifest_sha256": manifest_hash, "output": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.training, args.source_run, args.output), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
