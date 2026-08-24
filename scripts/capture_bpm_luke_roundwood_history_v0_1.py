from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
import uuid
from pathlib import Path
from typing import Any


ENDPOINT = "https://statdb.luke.fi/PxWeb/api/v1/en/LUKE/met/teokau/kk/0100_teokau.px"
RUN_RELATIVE = Path("evidence/runs/bpm-luke-roundwood-monthly-v0.1-history-capture")
PREREG_RELATIVE = Path("preregistrations/BPM_LUKE_ROUNDWOOD_MONTHLY_2020_2026_V0.1.json")
ADDENDUM_RELATIVE = Path("preregistrations/BPM_LUKE_ROUNDWOOD_MONTHLY_2020_2026_V0.1_SOFTWARE_ADDENDUM.json")
MONTHS = [f"{year}M{month:02d}" for year in range(2020, 2027) for month in range(1, 13) if (year, month) <= (2026, 7)]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolved_repo(path: Path) -> Path:
    """Use the Windows extended-length namespace without changing relative custody paths."""
    resolved = path.resolve()
    extended_prefix = chr(92) * 2 + "?" + chr(92)
    if os.name == "nt" and not str(resolved).startswith(extended_prefix):
        return Path(extended_prefix + str(resolved))
    return resolved

def request_once(request: urllib.request.Request) -> tuple[int, dict[str, str], bytes]:
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.status, dict(response.headers.items()), response.read()


repo = resolved_repo(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd())
prereg = repo / PREREG_RELATIVE
addendum = repo / ADDENDUM_RELATIVE
if not prereg.is_file() or not addendum.is_file():
    raise RuntimeError("Campaign preregistration and software addendum must exist before acquisition")
if json.loads(prereg.read_text(encoding="utf-8"))["status"] != "FROZEN_BEFORE_HISTORICAL_VALUE_ACQUISITION":
    raise RuntimeError("Campaign preregistration is not frozen")
if json.loads(addendum.read_text(encoding="utf-8"))["status"] != "FROZEN_BEFORE_HISTORICAL_VALUE_ACQUISITION":
    raise RuntimeError("Software addendum is not frozen")

final_dir = repo / RUN_RELATIVE
if final_dir.exists():
    raise RuntimeError(f"Immutable capture already exists: {final_dir}")
staging_dir = final_dir.parent / f".{final_dir.name}.staging-{uuid.uuid4().hex}"
staging_dir.mkdir(parents=True, exist_ok=False)

query = {
    "query": [
        {"code": "INFO", "selection": {"filter": "item", "values": ["M3T", "E_M3"]}},
        {"code": "M", "selection": {"filter": "item", "values": MONTHS}},
        {"code": "MPKH", "selection": {"filter": "item", "values": ["SSS"]}},
        {"code": "KAUP", "selection": {"filter": "item", "values": ["PKAUP"]}},
        {"code": "PTL", "selection": {"filter": "item", "values": ["TUK_KU"]}},
    ],
    "response": {"format": "json-stat2"},
}
query_path = staging_dir / "query.json"
write_json(query_path, query)
query_bytes = json.dumps(query, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
request = urllib.request.Request(
    ENDPOINT,
    data=query_bytes,
    method="POST",
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "BPM-Luke-causal-history-capture/0.1",
    },
)
status, headers, response_bytes = request_once(request)
response_path = staging_dir / "luke_roundwood_2020M01_2026M07.json"
response_path.write_bytes(response_bytes)
write_json(staging_dir / "response.headers.json", headers)
if status != 200:
    raise RuntimeError(f"Luke history request returned HTTP {status}; preserved only in staging")
response = json.loads(response_bytes.decode("utf-8"))
expected_id = ["INFO", "M", "MPKH", "KAUP", "PTL"]
expected_size = [2, len(MONTHS), 1, 1, 1]
if response.get("id") != expected_id or response.get("size") != expected_size:
    raise RuntimeError(f"Unexpected response cube: id={response.get('id')} size={response.get('size')}")
values = response.get("value")
if not isinstance(values, list) or len(values) != 2 * len(MONTHS):
    raise RuntimeError(f"Expected {2 * len(MONTHS)} dense cells; observed {type(values).__name__}/{len(values or [])}")
if response["dimension"]["M"]["category"]["index"] != {month: index for index, month in enumerate(MONTHS)}:
    raise RuntimeError("Returned month order differs from the frozen query")

manifest = {
    "schema": "bpm-luke-roundwood-history-capture-manifest/v0.1",
    "classification": "BOUNDED_CURRENT_SERIES_NOT_HISTORICAL_FIRST_RELEASE_VINTAGES",
    "preregistration": {"path": PREREG_RELATIVE.as_posix(), "sha256": sha256_file(prereg)},
    "software_addendum": {"path": ADDENDUM_RELATIVE.as_posix(), "sha256": sha256_file(addendum)},
    "source": {
        "endpoint": ENDPOINT,
        "remote_metadata_gets": 0,
        "remote_data_posts": 1,
        "http_status": status,
        "updated": response.get("updated"),
    },
    "selection": {
        "information": ["M3T", "E_M3"],
        "months": MONTHS,
        "price_region": "SSS",
        "type_of_sale": "PKAUP",
        "roundwood_assortment": "TUK_KU",
        "query_sha256": sha256_file(query_path),
    },
    "response": {
        "path": response_path.name,
        "bytes": len(response_bytes),
        "sha256": sha256_bytes(response_bytes),
        "cell_count": len(values),
        "status_flags_present": "status" in response,
    },
    "invariants": {
        "bulk_download": False,
        "fit_performed": False,
        "forecast_performed": False,
        "score_performed": False,
        "posterior_updated": False,
        "Z_post_updated": False,
        "historical_freeze_reconstructed": False,
        "cross_source_pooling": False,
        "global_winner": None,
        "automatic_promotion": False,
    },
}
write_json(staging_dir / "capture_manifest.json", manifest)
os.replace(staging_dir, final_dir)
print(json.dumps({"run": RUN_RELATIVE.as_posix(), "cells": len(values), "response_sha256": manifest["response"]["sha256"]}, indent=2))
