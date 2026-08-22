"""V0.2 UCII extraction: preserve sector boundaries outside the general likelihood."""

from __future__ import annotations

import importlib
import re
from math import isfinite
from pathlib import Path

from bma.experiments.hbp_eurostat_sts_v0_1 import GateFailure
from bma.experiments.hbp_indec_ipi_v0_1 import MONTHS, require_exact_contiguity
from bma.experiments.hbp_indec_ucii_v0_1 import logit_percent


def extract_ucii_records_v0_2(
    path: Path,
) -> tuple[list[dict], list[str], str, list[dict]]:
    try:
        xlrd = importlib.import_module("xlrd")
    except ModuleNotFoundError as exc:
        raise GateFailure(
            "xlrd==2.0.2 is required for the frozen BIFF8 evidence reader"
        ) from exc
    if getattr(xlrd, "__version__", None) != "2.0.2":
        raise GateFailure(
            f"unexpected xlrd version: {getattr(xlrd, '__version__', None)!r}"
        )
    book = xlrd.open_workbook(path, on_demand=True, encoding_override="cp1252")
    try:
        sheet = book.sheet_by_name("UCI - NG y bloques")
        headers = [
            str(sheet.cell_value(2, column)).strip() for column in range(sheet.ncols)
        ]
        records = []
        current_year = None
        for row_index in range(sheet.nrows):
            period = sheet.cell_value(row_index, 0)
            if not isinstance(period, str):
                continue
            match = re.fullmatch(r"Año\s+(\d{4})", period.strip())
            if match:
                current_year = int(match.group(1))
                continue
            month_label = period.strip().rstrip("*").strip()
            if current_year is None or month_label not in MONTHS:
                continue
            values = [
                sheet.cell_value(row_index, column) for column in range(1, sheet.ncols)
            ]
            if any(not isinstance(value, float) for value in values):
                continue
            records.append(
                {
                    "time": f"{current_year:04d}-{MONTHS[month_label]:02d}",
                    "general_percent": float(values[0]),
                    "sector_percent": {
                        headers[index + 2]: float(value)
                        for index, value in enumerate(values[1:])
                    },
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
    logit_percent(record["general_percent"] for record in records)
    boundary_events = []
    for record in records:
        for label, value in record["sector_percent"].items():
            if not isfinite(value) or not 0.0 <= value <= 100.0:
                raise GateFailure(
                    "UCII sector observers must be finite and within closed support 0 to 100"
                )
            if value in (0.0, 100.0):
                boundary_events.append(
                    {
                        "time": record["time"],
                        "source_row_1_based": record["source_row_1_based"],
                        "label": label,
                        "value": value,
                    }
                )
    if round(records[-1]["general_percent"], 1) != 59.1:
        raise GateFailure(
            "INDEC UCII last general value does not reconcile to the official PDF"
        )
    return records, headers, xlrd.__version__, boundary_events
