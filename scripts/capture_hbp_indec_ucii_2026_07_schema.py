"""One-shot capture of the official INDEC UCII BIFF8 workbook, without fitting."""

from __future__ import annotations

import hashlib
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "preregistrations" / "HBP_INDEC_UCII_2026_07_CAPTURE_V0.1.json"
OUTPUT = ROOT / "evidence" / "runs" / "hbp-indec-ucii-v0.1-2026-07-schema-capture"
MAX_BYTES = 10_000_000


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def redacted_row(sheet: object, row_index: int) -> list[dict]:
    cells = []
    for column_index in range(sheet.ncols):
        value = sheet.cell_value(row_index, column_index)
        if isinstance(value, float):
            rendered: object = "NUMERIC_PRESENT"
        elif isinstance(value, str):
            rendered = value
        else:
            rendered = str(value)
        cells.append({"column_zero_based": column_index, "value_or_type": rendered})
    return cells


def inspect_schema(raw: bytes) -> tuple[dict, str]:
    xlrd = importlib.import_module("xlrd")
    if getattr(xlrd, "__version__", None) != "2.0.2":
        raise RuntimeError(f"unexpected xlrd version: {getattr(xlrd, '__version__', None)!r}")
    book = xlrd.open_workbook(file_contents=raw, on_demand=True, encoding_override="cp1252")
    sheets = []
    try:
        for name in book.sheet_names():
            sheet = book.sheet_by_name(name)
            selected_rows = sorted(set(range(min(15, sheet.nrows))) | set(range(max(0, sheet.nrows - 20), sheet.nrows)))
            sheets.append(
                {
                    "name": name,
                    "nrows": sheet.nrows,
                    "ncols": sheet.ncols,
                    "schema_rows_numeric_redacted": [
                        {"row_zero_based": row, "cells": redacted_row(sheet, row)} for row in selected_rows
                    ],
                }
            )
    finally:
        book.release_resources()
    return {"biff_version": book.biff_version, "datemode": book.datemode, "sheets": sheets}, xlrd.__version__


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"immutable output already exists: {OUTPUT}")
    prereg_bytes = PREREG.read_bytes()
    prereg = json.loads(prereg_bytes.decode("utf-8-sig"))
    request = Request(prereg["exact_workbook_url"], headers={"User-Agent": "BMA-HBP-evidence-custody/0.1"})
    captured_at = datetime.now(timezone.utc).isoformat()
    with urlopen(request, timeout=60) as response:
        raw = response.read(MAX_BYTES + 1)
        headers = {key: value for key, value in response.headers.items()}
        status_code = response.status
        final_url = response.geturl()
    if len(raw) > MAX_BYTES:
        raise RuntimeError("INDEC UCII workbook exceeded bounded size")
    if status_code != 200:
        raise RuntimeError(f"unexpected INDEC UCII HTTP status: {status_code}")
    if not raw.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        raise RuntimeError("INDEC UCII payload is not an OLE/BIFF workbook")
    schema, reader_version = inspect_schema(raw)

    OUTPUT.mkdir(parents=True, exist_ok=False)
    raw_path = OUTPUT / "indec_ucii_series_through_2026_06.xls"
    raw_path.write_bytes(raw)
    capture = {
        "captured_at_utc": captured_at,
        "request_url": prereg["exact_workbook_url"],
        "final_url": final_url,
        "http_status": status_code,
        "headers": headers,
        "raw_bytes": len(raw),
        "raw_sha256": digest_bytes(raw),
        "reader": f"xlrd=={reader_version}",
        "fit_performed": False,
        "forecast_performed": False,
        "score_performed": False,
    }
    (OUTPUT / "response_headers.json").write_bytes(json_bytes(capture))
    schema.update(
        {
            "schema": "hbp.indec.ucii.biff8-schema.v0.1",
            "raw_sha256": digest_bytes(raw),
            "numeric_values_redacted_before_freeze_preregistration": True,
            "fit_performed": False,
            "forecast_performed": False,
            "score_performed": False,
        }
    )
    (OUTPUT / "workbook_schema.json").write_bytes(json_bytes(schema))
    paths = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    manifest = {
        "schema": "hbp.indec.ucii.schema-capture-manifest.v0.1",
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
        "fit_performed": False,
        "forecast_performed": False,
        "score_performed": False,
    }
    (OUTPUT / "manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"status": "SCHEMA_CAPTURED_NO_FIT", "bytes": len(raw), "sha256": digest_bytes(raw), "sheets": [{"name": item["name"], "nrows": item["nrows"], "ncols": item["ncols"]} for item in schema["sheets"]], "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
