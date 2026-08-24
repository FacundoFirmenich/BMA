"""Bounded-state models and BIFF8 extraction for the new INDEC UCII chain."""

from __future__ import annotations

import importlib
import re
from math import cos, exp, isfinite, log, pi, sin, sqrt
from pathlib import Path
from typing import Iterable

import numpy as np

from bma.experiments.hbp_eurostat_sts_v0_1 import GateFailure, StudentTPredictive
from bma.experiments.hbp_indec_ipi_v0_1 import MONTHS, require_exact_contiguity


def logit_percent(values: Iterable[float]) -> list[float]:
    checked = [float(value) for value in values]
    if not checked or any(not isfinite(value) or not 0.0 < value < 100.0 for value in checked):
        raise GateFailure("UCII observations must be finite and strictly between 0 and 100")
    return [log(value / (100.0 - value)) for value in checked]


def inverse_logit_percent(value: float) -> float:
    if not isfinite(value):
        raise GateFailure("bounded-state location must be finite")
    if value >= 0.0:
        tail = exp(-value)
        return 100.0 / (1.0 + tail)
    head = exp(value)
    return 100.0 * head / (1.0 + head)


def bounded_forecast(last_percent: float, innovation: StudentTPredictive) -> dict[str, float]:
    last_state = logit_percent([last_percent])[0]
    lower, upper = innovation.interval(0.90)
    return {
        "point_median_percent": inverse_logit_percent(last_state + innovation.location),
        "lower_90_percent": inverse_logit_percent(last_state + lower),
        "upper_90_percent": inverse_logit_percent(last_state + upper),
        "logit_location": last_state + innovation.location,
        "logit_scale": innovation.scale,
        "degrees_of_freedom": innovation.degrees_of_freedom,
    }


def harmonic_features(month: int) -> list[float]:
    if month not in range(1, 13):
        raise GateFailure("calendar month must be between 1 and 12")
    angle = 2.0 * pi * month / 12.0
    return [1.0, sin(angle), cos(angle), sin(2.0 * angle), cos(2.0 * angle)]


def bayesian_linear_posterior(
    response: Iterable[float],
    design: Iterable[Iterable[float]],
    *,
    prior_mean: Iterable[float],
    prior_precision_diagonal: Iterable[float],
    alpha0: float,
    beta0_scale: float,
    future_features: Iterable[float],
) -> dict:
    y = np.asarray(list(response), dtype=float)
    x = np.asarray([list(row) for row in design], dtype=float)
    mean0 = np.asarray(list(prior_mean), dtype=float)
    precision_diagonal = np.asarray(list(prior_precision_diagonal), dtype=float)
    future = np.asarray(list(future_features), dtype=float)
    if y.ndim != 1 or x.ndim != 2 or x.shape[0] != y.shape[0] or x.shape[1] != mean0.shape[0]:
        raise GateFailure("harmonic regression dimensions are inconsistent")
    if future.shape != mean0.shape or precision_diagonal.shape != mean0.shape:
        raise GateFailure("harmonic prior or future-feature dimensions are inconsistent")
    if y.size == 0 or not np.all(np.isfinite(y)) or not np.all(np.isfinite(x)):
        raise GateFailure("harmonic regression inputs must be non-empty and finite")
    if alpha0 <= 0.0 or beta0_scale <= 0.0 or np.any(precision_diagonal <= 0.0):
        raise GateFailure("harmonic conjugate hyperparameters must be positive")

    precision0 = np.diag(precision_diagonal)
    precision_n = precision0 + x.T @ x
    covariance_n = np.linalg.inv(precision_n)
    mean_n = covariance_n @ (precision0 @ mean0 + x.T @ y)
    alpha_n = alpha0 + y.size / 2.0
    beta_n = beta0_scale + 0.5 * float(y @ y + mean0 @ precision0 @ mean0 - mean_n @ precision_n @ mean_n)
    predictive = StudentTPredictive(
        degrees_of_freedom=2.0 * alpha_n,
        location=float(future @ mean_n),
        scale=sqrt(float(beta_n / alpha_n * (1.0 + future @ covariance_n @ future))),
    )
    return {
        "n": int(y.size),
        "coefficient_count": int(mean_n.size),
        "mean": mean_n.tolist(),
        "precision": precision_n.tolist(),
        "covariance": covariance_n.tolist(),
        "alpha": float(alpha_n),
        "beta": float(beta_n),
        "posterior_predictive": predictive,
    }


def extract_ucii_records(path: Path) -> tuple[list[dict], list[str], str]:
    try:
        xlrd = importlib.import_module("xlrd")
    except ModuleNotFoundError as exc:
        raise GateFailure("xlrd==2.0.2 is required for the frozen BIFF8 evidence reader") from exc
    if getattr(xlrd, "__version__", None) != "2.0.2":
        raise GateFailure(f"unexpected xlrd version: {getattr(xlrd, '__version__', None)!r}")
    book = xlrd.open_workbook(path, on_demand=True, encoding_override="cp1252")
    try:
        sheet = book.sheet_by_name("UCI - NG y bloques")
        headers = [str(sheet.cell_value(2, column)).strip() for column in range(sheet.ncols)]
        records = []
        current_year = None
        for row_index in range(sheet.nrows):
            period = sheet.cell_value(row_index, 0)
            if isinstance(period, str):
                match = re.fullmatch(r"Año\s+(\d{4})", period.strip())
                if match:
                    current_year = int(match.group(1))
                    continue
                month_label = period.strip().rstrip("*").strip()
            else:
                continue
            if current_year is None or month_label not in MONTHS:
                continue
            values = [sheet.cell_value(row_index, column) for column in range(1, sheet.ncols)]
            if any(not isinstance(value, float) for value in values):
                continue
            records.append(
                {
                    "time": f"{current_year:04d}-{MONTHS[month_label]:02d}",
                    "general_percent": float(values[0]),
                    "sector_percent": {headers[index + 2]: float(value) for index, value in enumerate(values[1:])},
                    "provisional": period.strip().endswith("*"),
                    "source_row_1_based": row_index + 1,
                }
            )
    finally:
        book.release_resources()
    records = [record for record in records if "2016-01" <= record["time"] <= "2026-06"]
    require_exact_contiguity(records, start="2016-01", end="2026-06", count=126)
    if any(record["time"] == "2026-07" for record in records):
        raise GateFailure("INDEC UCII target 2026-07 appeared in the training workbook")
    for record in records:
        logit_percent([record["general_percent"], *record["sector_percent"].values()])
    if round(records[-1]["general_percent"], 1) != 59.1:
        raise GateFailure("INDEC UCII last general value does not reconcile to the official PDF")
    return records, headers, xlrd.__version__
