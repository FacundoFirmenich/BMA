"""Frozen local phase selector derived from the 2022--2024 discovery campaign.

The selector is deterministic and cannot be confirmatorily scored on its
discovery years.  It dispatches a model for one variable and one next-month
target while preserving December's primary abstention.
"""
from __future__ import annotations

from dataclasses import dataclass

from bma.experiments import aeat_monthly_seasonal_v0_6_5 as seasonal


SCHEMA = "bma.aeat.chapter72.monthly-seasonal.phase-selector.v0.6.6"
DISCOVERY_YEARS = frozenset({2022, 2023, 2024})
VARIABLES = frozenset({"participation", "quantity", "unit_value"})


@dataclass(frozen=True)
class PhaseSelection:
    variable: str
    target_period: str
    calendar_month: int
    model_id: str
    primary_status: str
    evidence_window: str


def _year(period: str) -> int:
    try:
        year, _ = period.split("-")
        return int(year)
    except (AttributeError, ValueError) as exc:
        raise seasonal.GateFailure(f"invalid monthly period {period!r}") from exc


def require_unused_validation_target(target_period: str) -> None:
    seasonal.calendar_phase(target_period)
    if _year(target_period) in DISCOVERY_YEARS:
        raise seasonal.GateFailure("v0.6.6 confirmatory validation cannot reuse a 2022--2024 discovery target")


def select(variable: str, target_period: str) -> PhaseSelection:
    if variable not in VARIABLES:
        raise seasonal.GateFailure(f"unknown selector variable {variable!r}")
    month = seasonal.calendar_phase(target_period)
    model_id = "M0"
    evidence_window = "ordinary baseline outside frozen local seasonal windows"

    if variable == "participation" and month in {6, 7, 8, 9}:
        model_id = "M1"
        evidence_window = "reproduced annual harmonic participation window June--September"
    elif variable == "participation" and month in {10, 11}:
        model_id = "M2"
        evidence_window = "reproduced hierarchical participation window October--November"
    elif variable == "quantity" and month == 9:
        model_id = "M2"
        evidence_window = "reproduced hierarchical quantity window September"
    elif variable == "unit_value" and month == 3:
        model_id = "M1"
        evidence_window = "reproduced annual harmonic statistical-unit-value window March"

    primary_status = "PRIMARY_ELIGIBLE"
    if month == 12:
        model_id = "M0"
        primary_status = "ABSTAIN_YEAR_END_UNCALIBRATED"
        evidence_window = "December posterior update required; primary adjudication prohibited"

    return PhaseSelection(
        variable=variable,
        target_period=target_period,
        calendar_month=month,
        model_id=model_id,
        primary_status=primary_status,
        evidence_window=evidence_window,
    )
