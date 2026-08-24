"""Read-only extraction gates for the official INDEC IPI BIFF8 workbook."""

from __future__ import annotations

import importlib
from pathlib import Path

from bma.experiments.hbp_eurostat_sts_v0_1 import GateFailure


MONTHS = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12,
}


def next_month(month: str) -> str:
    year, number = (int(part) for part in month.split("-"))
    return f"{year + (number == 12):04d}-{1 if number == 12 else number + 1:02d}"


def require_exact_contiguity(records: list[dict], *, start: str, end: str, count: int) -> None:
    if len(records) != count:
        raise GateFailure(f"unexpected INDEC IPI observation count: {len(records)}")
    if records[0]["time"] != start or records[-1]["time"] != end:
        raise GateFailure("unexpected INDEC IPI temporal endpoints")
    for previous, current in zip(records, records[1:]):
        if next_month(previous["time"]) != current["time"]:
            raise GateFailure(f"non-contiguous INDEC IPI months: {previous['time']} to {current['time']}")


def extract_ipi_records(path: Path) -> tuple[list[dict], str]:
    try:
        xlrd = importlib.import_module("xlrd")
    except ModuleNotFoundError as exc:
        raise GateFailure("xlrd==2.0.2 is required for the frozen BIFF8 evidence reader") from exc
    if getattr(xlrd, "__version__", None) != "2.0.2":
        raise GateFailure(f"unexpected xlrd version: {getattr(xlrd, '__version__', None)!r}")

    book = xlrd.open_workbook(path, on_demand=True, encoding_override="cp1252")
    try:
        sheet = book.sheet_by_name("Cuadro 1")
        records = []
        current_year = None
        provisional = False
        for row_index in range(sheet.nrows):
            year_value = sheet.cell_value(row_index, 1)
            if isinstance(year_value, float) and year_value.is_integer():
                current_year = int(year_value)
                provisional = False
            elif isinstance(year_value, str) and year_value.rstrip("*").isdigit():
                current_year = int(year_value.rstrip("*"))
                provisional = year_value.endswith("*")
            month_label = sheet.cell_value(row_index, 2)
            if current_year is None or month_label not in MONTHS:
                continue
            original = sheet.cell_value(row_index, 3)
            seasonally_adjusted = sheet.cell_value(row_index, 7)
            if not isinstance(original, float) or not isinstance(seasonally_adjusted, float):
                continue
            month = f"{current_year:04d}-{MONTHS[month_label]:02d}"
            records.append(
                {
                    "time": month,
                    "original_index": float(original),
                    "seasonally_adjusted_index": float(seasonally_adjusted),
                    "provisional": provisional,
                    "source_row_1_based": row_index + 1,
                }
            )
    finally:
        book.release_resources()

    records = [record for record in records if "2016-01" <= record["time"] <= "2026-06"]
    require_exact_contiguity(records, start="2016-01", end="2026-06", count=126)
    if any(record["time"] == "2026-07" for record in records):
        raise GateFailure("INDEC IPI target 2026-07 appeared in the training workbook")
    if round(records[-1]["original_index"], 1) != 119.9:
        raise GateFailure("INDEC IPI last original index does not reconcile to the official PDF")
    if round(records[-1]["seasonally_adjusted_index"], 1) != 119.1:
        raise GateFailure("INDEC IPI last seasonally adjusted index does not reconcile to the official PDF")
    return records, xlrd.__version__
