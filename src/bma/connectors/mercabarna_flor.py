#!/usr/bin/env python3
"""Immutable Mercabarna Flor sector-4 historical retriever.

The connector preserves every raw CSV, emits one structured JSON object per
date and origin, rejects accumulated columns, and never infers an economic zero
from an empty response. A completeness witness can establish participation
absence, but quantity remains conditional on a positive row.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from bma.custody import write_json_new, write_manifest

URL = "https://www.mercabarna.es/serveis/es_estadistiques-productes/"
SCHEMA = "bma.mercabarna.flor.structured-observation.v1"


class ConnectorFailure(RuntimeError):
    pass


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return " ".join("".join(character for character in decomposed if not unicodedata.combining(character)).lower().split())


def decode_mixed(raw: bytes) -> tuple[str, str]:
    try:
        text = raw.decode("utf-8", errors="strict")
        return text, "utf-8"
    except UnicodeDecodeError:
        output: list[str] = []
        index = 0
        while index < len(raw):
            if raw[index] < 0x80:
                output.append(chr(raw[index]))
                index += 1
                continue
            decoded = None
            for width in (4, 3, 2):
                candidate = raw[index : index + width]
                if len(candidate) != width:
                    continue
                try:
                    value = candidate.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    continue
                if len(value) == 1 and not unicodedata.category(value).startswith("C"):
                    decoded = value
                    index += width
                    break
            if decoded is not None:
                output.append(decoded)
                continue
            try:
                output.append(bytes([raw[index]]).decode("cp1252", errors="strict"))
            except UnicodeDecodeError as exc:
                raise ConnectorFailure(f"undecodable byte at offset {index}") from exc
            index += 1
        text = "".join(output)
        if "\x00" in text:
            raise ConnectorFailure("NUL byte in decoded CSV")
        return text, "mixed-utf8-windows-1252"


def parse_grouped_integer(value: str) -> int:
    normalized = value.strip().replace(".", "").replace(" ", "")
    if not normalized or not normalized.isdigit():
        raise ConnectorFailure(f"invalid grouped integer: {value!r}")
    return int(normalized)


def parse_decimal_comma(value: str) -> float:
    normalized = value.strip().replace(".", "").replace(",", ".")
    try:
        result = float(normalized)
    except ValueError as exc:
        raise ConnectorFailure(f"invalid decimal: {value!r}") from exc
    if not math.isfinite(result):
        raise ConnectorFailure(f"non-finite decimal: {value!r}")
    return result


def request_payload(day: date, origin_code: str) -> bytes:
    return urllib.parse.urlencode(
        {
            "grup": "",
            "producte": "",
            "arees": "0",
            "origen": origin_code,
            "periode": "1",
            "data-inici": day.strftime("%d-%m-%Y"),
            "data-final": "",
            "sector": "4",
            "generar": "Generar estadisticas",
            "exportField": "export",
        }
    ).encode("utf-8")


def fetch(day: date, origin_code: str, timeout: int) -> tuple[bytes, dict[str, str], int]:
    request = urllib.request.Request(
        URL,
        data=request_payload(day, origin_code),
        method="POST",
        headers={
            "User-Agent": "BMA-Mercabarna-Flor/0.1",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/csv,*/*;q=0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        status = int(response.status)
        headers = {key.lower(): value for key, value in response.headers.items()}
    if status != 200 or not raw or "csv" not in headers.get("content-type", "").lower():
        raise ConnectorFailure(f"transport failure origin={origin_code} date={day.isoformat()} status={status}")
    return raw, headers, status


def parse_csv(text: str, expected_day: date, expected_origin: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = list(csv.reader(io.StringIO(text), delimiter=";", quotechar='"'))
    if len(rows) < 4:
        raise ConnectorFailure("CSV shorter than four rows")
    period = rows[2][0].split(":", 1)[-1].strip() if len(rows[2]) == 1 else ""
    expected_period = f"{expected_day:%d-%m-%Y} / {expected_day:%d-%m-%Y}"
    if period != expected_period:
        raise ConnectorFailure(f"period mismatch {period!r} != {expected_period!r}")
    header = rows[3]
    normalized = [normalize_text(cell) for cell in header]
    if (
        len(header) != 6
        or normalized[0] != "producto"
        or "total unidades origen periodo" not in normalized[1]
        or "precio periodo" not in normalized[2]
        or "acumulado" not in normalized[3]
        or "acumulados" not in normalized[4]
    ):
        raise ConnectorFailure(f"unexpected header: {header!r}")
    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source_row in rows[4:]:
        if not any(cell.strip() for cell in source_row):
            continue
        if len(source_row) != 6:
            raise ConnectorFailure(f"invalid row width: {source_row!r}")
        product = source_row[0].strip()
        cell_id = f"{expected_origin}|{product}"
        if not product or cell_id in seen:
            raise ConnectorFailure(f"blank or duplicate cell: {cell_id!r}")
        seen.add(cell_id)
        quantity = parse_grouped_integer(source_row[1])
        price = parse_decimal_comma(source_row[2])
        if quantity <= 0 or price < 0:
            raise ConnectorFailure(f"invalid positive row: {cell_id}")
        parsed.append(
            {
                "cell_id": cell_id,
                "product": product,
                "origin_code": expected_origin,
                "origin_label": source_row[5].strip(),
                "unit_count": quantity,
                "price_eur_per_unit": price,
            }
        )
    return parsed, {
        "period": period,
        "row_count": len(parsed),
        "forbidden_accumulated_columns_discarded": [header[3], header[4]],
    }


@dataclass(frozen=True)
class RetrievedObject:
    day: date
    origin_code: str
    raw: bytes
    headers: dict[str, str]
    status: int
    encoding: str
    rows: list[dict[str, Any]]
    metadata: dict[str, Any]


def retrieve_one(day: date, origin_code: str, timeout: int) -> RetrievedObject:
    raw, headers, status = fetch(day, origin_code, timeout)
    text, encoding = decode_mixed(raw)
    rows, metadata = parse_csv(text, day, origin_code)
    return RetrievedObject(day, origin_code, raw, headers, status, encoding, rows, metadata)


def persist_one(root: Path, result: RetrievedObject, completeness_witness: str) -> dict[str, Any]:
    raw_hash = hashlib.sha256(result.raw).hexdigest()
    raw_path = root / "raw" / result.day.isoformat() / f"origin_{result.origin_code}_{raw_hash[:12]}.csv"
    if raw_path.exists():
        raise ConnectorFailure(f"immutable raw already exists: {raw_path}")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(result.raw)
    publication_state = "POSITIVE_ROWS" if result.rows else "COMPLETE_ZERO_ROWS_FOR_PARTICIPATION_ONLY"
    document = {
        "schema_version": SCHEMA,
        "date": result.day.isoformat(),
        "origin_code": result.origin_code,
        "publication_state": publication_state,
        "completeness_witness": completeness_witness,
        "source": {
            "url": URL,
            "http_status": result.status,
            "content_type": result.headers.get("content-type"),
            "encoding_observed": result.encoding,
            "raw_file": raw_path.relative_to(root).as_posix(),
            "raw_sha256": raw_hash,
            "raw_bytes": len(result.raw),
        },
        "rows": result.rows,
        "metadata": result.metadata,
        "claim_boundary": {
            "annual_accumulated_used": False,
            "empty_establishes_participation_absence": True,
            "empty_establishes_quantity_zero": False,
            "price_is_conditional_on_positive_row": True,
        },
    }
    observation_path = root / "observations" / result.day.isoformat() / f"origin_{result.origin_code}.json"
    observation_hash = write_json_new(observation_path, document)
    return {
        "date": result.day.isoformat(),
        "origin_code": result.origin_code,
        "raw_sha256": raw_hash,
        "observation_sha256": observation_hash,
        "row_count": len(result.rows),
        "publication_state": publication_state,
    }


def date_range(start: date, end: date) -> list[date]:
    if end < start:
        raise ConnectorFailure("end precedes start")
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def run(
    origins_file: Path,
    output: Path,
    start: date,
    end: date,
    completeness_witness: str,
    timeout: int = 30,
    workers: int = 4,
) -> dict[str, Any]:
    if output.exists():
        raise ConnectorFailure(f"immutable output already exists: {output}")
    discovery = json.loads(origins_file.read_text(encoding="utf-8"))
    origins = sorted(str(item["origin_code"]) for item in discovery["active_origins"])
    if not origins or "32" in origins:
        raise ConnectorFailure("authorized origins are empty or include excluded Argentina")
    output.mkdir(parents=True)
    tasks = [(day, origin) for day in date_range(start, end) for origin in origins]
    retrieved: dict[tuple[str, str], RetrievedObject] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(retrieve_one, day, origin, timeout): (day, origin) for day, origin in tasks}
        for future in as_completed(futures):
            day, origin = futures[future]
            retrieved[(day.isoformat(), origin)] = future.result()
    receipts = [
        persist_one(output, retrieved[(day.isoformat(), origin)], completeness_witness)
        for day, origin in tasks
    ]
    source_contract = {
        "schema_version": "bma.source-contract.v1",
        "market": "Mercabarna sector 4 flowers, plants and complements",
        "range": [start.isoformat(), end.isoformat()],
        "origins": origins,
        "expected_objects": len(tasks),
        "retrieved_objects": len(receipts),
        "completeness_witness": completeness_witness,
        "empty_semantics": {
            "participation": "ABSENT_WITHIN_COMPLETE_DAILY_ORIGIN_PUBLICATION",
            "quantity": "NOT_APPLICABLE_CONDITIONAL_ON_POSITIVE_ROW",
            "price": "NOT_APPLICABLE_CONDITIONAL_ON_POSITIVE_ROW",
        },
        "status": "PASS" if len(receipts) == len(tasks) else "FAIL",
    }
    write_json_new(output / "SOURCE_CONTRACT.json", source_contract)
    write_json_new(output / "RETRIEVAL_RECEIPTS.json", {"schema_version": SCHEMA, "receipts": receipts})
    _, manifest_hash = write_manifest(output)
    return {
        "status": source_contract["status"],
        "objects": len(receipts),
        "positive_objects": sum(receipt["row_count"] > 0 for receipt in receipts),
        "empty_complete_objects": sum(receipt["row_count"] == 0 for receipt in receipts),
        "rows": sum(receipt["row_count"] for receipt in receipts),
        "manifest_sha256": manifest_hash,
        "output": str(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origins", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--completeness-witness", required=True)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    result = run(
        args.origins,
        args.output,
        args.start,
        args.end,
        args.completeness_witness,
        args.timeout,
        args.workers,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
