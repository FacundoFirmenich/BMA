"""Event-day projection of AEAT maximum-detail trade records.

This module does not make AEAT a live daily feed. It preserves the economic
event date contained in a monthly source archive and keeps that event clock
separate from source availability. Raw archives are not persisted here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable

from bma.connectors.aeat_trade import AeatContractError, RECORD_LENGTH, parse_record


def parse_event_date(value: str, *, expected_year: int, expected_month: int) -> date:
    """Parse AEAT YYMMDD admission date and enforce its archive period."""
    if len(value) != 6 or not value.isdigit():
        raise AeatContractError(f"invalid admission date {value!r}")
    year = 2000 + int(value[0:2])
    month = int(value[2:4])
    day = int(value[4:6])
    try:
        observed = date(year, month, day)
    except ValueError as error:
        raise AeatContractError(f"invalid admission date {value!r}") from error
    if (year, month) != (expected_year, expected_month):
        raise AeatContractError(
            f"admission period mismatch {(year, month)} != {(expected_year, expected_month)}"
        )
    return observed


@dataclass
class _DailyAggregate:
    event_date: date
    flow: str
    cn8: str
    partner_country: str
    weight_kg: float = 0.0
    supplementary_units: float = 0.0
    statistical_value_eur: float = 0.0
    invoice_value_eur: float = 0.0
    line_count: int = 0

    def add(self, row: dict[str, Any]) -> None:
        self.weight_kg += float(row["weight_kg"])
        self.supplementary_units += float(row["supplementary_units"])
        self.statistical_value_eur += float(row["statistical_value_eur"])
        self.invoice_value_eur += float(row["invoice_value_eur"])
        self.line_count += 1

    def serializable(self) -> dict[str, Any]:
        partner = self.partner_country or "UNK"
        cell_id = f"{self.flow}|{self.cn8}|{partner}"
        return {
            "event_date": self.event_date.isoformat(),
            "cell_id": cell_id,
            "cell_day_id": f"{self.event_date.isoformat()}|{cell_id}",
            "flow": self.flow,
            "cn8": self.cn8,
            "cn4": self.cn8[:4],
            "partner_country": partner,
            "weight_kg": self.weight_kg,
            "supplementary_units": self.supplementary_units,
            "statistical_value_eur": self.statistical_value_eur,
            "invoice_value_eur": self.invoice_value_eur,
            "statistical_unit_value_eur_per_kg": (
                self.statistical_value_eur / self.weight_kg if self.weight_kg > 0 else None
            ),
            "line_count": self.line_count,
        }


def aggregate_records_by_event_day(
    lines: Iterable[bytes], *, year: int, month: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Aggregate Chapter 72 records by their admission day without imputing zeros."""
    aggregates: dict[tuple[date, str, str, str], _DailyAggregate] = {}
    total_lines = 0
    chapter72_lines = 0
    event_days: set[date] = set()
    for source in lines:
        raw = source.rstrip(b"\r\n")
        if not raw:
            continue
        if len(raw) != RECORD_LENGTH:
            raise AeatContractError(f"record length {len(raw)} != {RECORD_LENGTH}")
        total_lines += 1
        row = parse_record(raw, expected_year=year, expected_month=month)
        event_day = parse_event_date(
            str(row["admission_date"]), expected_year=year, expected_month=month
        )
        if not str(row["cn8"]).startswith("72"):
            continue
        chapter72_lines += 1
        event_days.add(event_day)
        partner = str(row["partner_country"] or "UNK")
        key = (event_day, str(row["flow"]), str(row["cn8"]), partner)
        aggregate = aggregates.setdefault(key, _DailyAggregate(*key))
        aggregate.add(row)
    cells = [aggregates[key].serializable() for key in sorted(aggregates)]
    return cells, {
        "total_lines": total_lines,
        "chapter72_lines": chapter72_lines,
        "cell_day_rows": len(cells),
        "observed_event_days": len(event_days),
        "first_event_date": min(event_days).isoformat() if event_days else None,
        "last_event_date": max(event_days).isoformat() if event_days else None,
        "missing_calendar_days_are_zero": False,
        "source_release_granularity": "monthly",
        "operational_daily_feed": False,
    }
