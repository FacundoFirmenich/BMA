from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any


EXPECTED_PREREG_SHA256 = "4259A1A5E7846AAD508F1D889B85625677B4883C8EF4E476D208071F30F214E7"
EXPECTED_AMENDMENT_SHA256 = "05F0B5D5C1638A84642943C50223BE9E0B62A258B5402486A8D042E8424C76AD"
ENDPOINT = "https://statdb.luke.fi/PxWeb/api/v1/en/LUKE/met/teokau/kk/0100_teokau.px"
RUN_RELATIVE = Path("evidence/runs/bpm-luke-roundwood-public-probe-v0.1")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def normalized(value: str) -> str:
    return " ".join(value.casefold().replace("\u00b3", "3").lstrip(". ").split())


def request_once(request: urllib.request.Request) -> tuple[int, dict[str, str], bytes]:
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.status, dict(response.headers.items()), response.read()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_variable(variables: list[dict[str, Any]], exact_text: str) -> dict[str, Any]:
    wanted = normalized(exact_text)
    matches = [variable for variable in variables if normalized(variable.get("text", "")) == wanted]
    if len(matches) != 1:
        raise ValueError(f"Expected one variable {exact_text!r}; observed {[v.get('text') for v in variables]}")
    return matches[0]


def find_value(variable: dict[str, Any], predicate, label: str) -> str:
    pairs = list(zip(variable.get("values", []), variable.get("valueTexts", []), strict=True))
    matches = [(code, text) for code, text in pairs if predicate(normalized(text))]
    if len(matches) != 1:
        raise ValueError(f"Expected one {label}; observed matches={matches}")
    return matches[0][0]


repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
prereg = repo / "preregistrations" / "BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_V0.1.json"
amendment = repo / "preregistrations" / "BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_AMENDMENT_A1.json"
run_dir = repo / RUN_RELATIVE
run_dir.mkdir(parents=True, exist_ok=True)
prereg_hash = sha256(prereg.read_bytes())
if prereg_hash != EXPECTED_PREREG_SHA256:
    raise RuntimeError(f"Preregistration hash mismatch: {prereg_hash}")
amendment_hash = sha256(amendment.read_bytes())
if amendment_hash != EXPECTED_AMENDMENT_SHA256:
    raise RuntimeError(f"Amendment hash mismatch: {amendment_hash}")

metadata_path = run_dir / "luke_roundwood_metadata.json"
metadata_headers_path = run_dir / "luke_roundwood_metadata.headers.json"
if metadata_path.exists():
    metadata_bytes = metadata_path.read_bytes()
    if sha256(metadata_bytes) != "EEEC4DD5228206B0054CB53615AD65E23986A9C1D2E4877376173137C6B7C05E":
        raise RuntimeError("Previously captured metadata hash mismatch")
    metadata_headers = json.loads(metadata_headers_path.read_text(encoding="utf-8"))
    metadata_status = 200
    metadata_get_performed_now = False
else:
    metadata_request = urllib.request.Request(
        ENDPOINT,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": "BMA-public-schema-probe/0.1"},
    )
    metadata_status, metadata_headers, metadata_bytes = request_once(metadata_request)
    metadata_path.write_bytes(metadata_bytes)
    write_json(metadata_headers_path, metadata_headers)
    metadata_get_performed_now = True
metadata = json.loads(metadata_bytes.decode("utf-8"))
if metadata_status != 200:
    raise RuntimeError(f"Metadata HTTP status {metadata_status}")

variables = metadata.get("variables", [])
information = find_variable(variables, "Information")
month = find_variable(variables, "Month")
region = find_variable(variables, "Price region (8 price regions)")
sale_type = find_variable(variables, "Type of sale")
assortment = find_variable(variables, "Roundwood assortment")

month_code = find_value(
    month,
    lambda text: bool(re.search(r"2026\D*07$", text)),
    "2026-07 month",
)
region_code = find_value(
    region,
    lambda text: text in {"whole country", "whole of finland", "finland"},
    "national price region",
)
sale_code = find_value(
    sale_type,
    lambda text: text in {"standing sales", "standing sale"},
    "standing sales",
)
assortment_code = find_value(
    assortment,
    lambda text: text in {"spruce logs", "spruce log"},
    "spruce logs",
)
volume_code = find_value(
    information,
    lambda text: "volume" in text and ("m3" in text or "cubic metre" in text or "cubic meter" in text),
    "physical transaction volume",
)
price_code = find_value(
    information,
    lambda text: text == "price (eur/m3)",
    "nominal EUR unit price",
)

query = {
    "query": [
        {"code": information["code"], "selection": {"filter": "item", "values": [volume_code, price_code]}},
        {"code": month["code"], "selection": {"filter": "item", "values": [month_code]}},
        {"code": region["code"], "selection": {"filter": "item", "values": [region_code]}},
        {"code": sale_type["code"], "selection": {"filter": "item", "values": [sale_code]}},
        {"code": assortment["code"], "selection": {"filter": "item", "values": [assortment_code]}},
    ],
    "response": {"format": "json-stat2"},
}
query_bytes = json.dumps(query, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
write_json(run_dir / "luke_roundwood_query.json", query)
data_request = urllib.request.Request(
    ENDPOINT,
    data=query_bytes,
    method="POST",
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "BMA-public-schema-probe/0.1",
    },
)
data_status, data_headers, data_bytes = request_once(data_request)
(run_dir / "luke_roundwood_2026_07_finland_standing_spruce_logs.json").write_bytes(data_bytes)
write_json(run_dir / "luke_roundwood_2026_07_finland_standing_spruce_logs.headers.json", data_headers)
if data_status != 200:
    raise RuntimeError(f"Data HTTP status {data_status}")
data = json.loads(data_bytes.decode("utf-8"))
values = data.get("value", [])
if isinstance(values, dict):
    observed_value_count = len(values)
else:
    observed_value_count = len(values)
if observed_value_count > 4:
    raise RuntimeError(f"Bounded cell limit exceeded: {observed_value_count}")

manifest = {
    "schema": "bpm-luke-roundwood-public-probe-manifest/v0.1",
    "classification": "BOUNDED_SCHEMA_AND_SINGLE_PRODUCT_CELL_PROBE",
    "preregistration": {
        "path": "preregistrations/BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_V0.1.json",
        "sha256": prereg_hash,
    },
    "amendment": {
        "path": "preregistrations/BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_AMENDMENT_A1.json",
        "sha256": amendment_hash,
    },
    "metadata": {
        "url": ENDPOINT,
        "http_status": metadata_status,
        "bytes": len(metadata_bytes),
        "sha256": sha256(metadata_bytes),
        "variable_count": len(variables),
        "variables": [
            {
                "code": variable.get("code"),
                "text": variable.get("text"),
                "value_count": len(variable.get("values", [])),
                "time": variable.get("time", False),
            }
            for variable in variables
        ],
    },
    "selection": {
        "month": month_code,
        "price_region": region_code,
        "type_of_sale": sale_code,
        "roundwood_assortment": assortment_code,
        "information": [volume_code, price_code],
        "query_sha256": sha256((run_dir / "luke_roundwood_query.json").read_bytes()),
    },
    "data": {
        "http_status": data_status,
        "bytes": len(data_bytes),
        "sha256": sha256(data_bytes),
        "observed_value_count": observed_value_count,
        "id": data.get("id"),
        "size": data.get("size"),
    },
    "invariants": {
        "remote_metadata_gets": 1,
        "metadata_get_performed_in_this_recovery_invocation": metadata_get_performed_now,
        "remote_data_posts": 1,
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
write_json(run_dir / "capture_manifest.json", manifest)
print(json.dumps({"run": str(RUN_RELATIVE), "selection": manifest["selection"], "data": manifest["data"]}, indent=2))
