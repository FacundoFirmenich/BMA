from __future__ import annotations

import hashlib
import io
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from ..prospective import PriceQuantityEventV1

CKAN_PACKAGE = "https://datos.gob.ar/data/api/3/action/package_show"
PACKAGE_ID = "energia-precios-volumenes-eess---resolucion-110404"
RESOURCE_ID = "d6ecf302-049b-459d-bca2-b638ea70518b"
CKAN_ENDPOINTS = (
    "https://datos.gob.ar/data/api/3/action",
    "https://www.datos.gob.ar/data/api/3/action",
    "https://datos.gob.ar/api/3/action",
)


def _request_with_retries(
    session: requests.Session,
    urls: list[tuple[str, dict[str, str] | None]],
    *,
    timeout: int,
    attempts: int = 5,
    stream: bool = False,
) -> requests.Response:
    errors: list[str] = []
    retryable = {408, 425, 429, 500, 502, 503, 504}
    for attempt in range(attempts):
        for url, params in urls:
            try:
                response = session.get(url, params=params, timeout=timeout, stream=stream)
                if response.status_code < 400:
                    return response
                errors.append(f"{response.status_code} {response.url}")
                if response.status_code not in retryable:
                    response.raise_for_status()
            except requests.RequestException as exc:
                errors.append(f"{url}: {exc!r}")
        if attempt < attempts - 1:
            time.sleep(min(2 ** attempt, 8))
    raise RuntimeError("official source unavailable after retries: " + " | ".join(errors[-12:]))


def _resolve_resource(session: requests.Session) -> tuple[dict, dict, str]:
    resource_calls = [
        (f"{base}/resource_show", {"id": RESOURCE_ID}) for base in CKAN_ENDPOINTS
    ]
    try:
        response = _request_with_retries(session, resource_calls, timeout=90)
        payload = response.json()
        if payload.get("success") and payload.get("result", {}).get("url"):
            return payload, payload["result"], "pinned_resource_show_with_retry"
    except Exception:
        pass

    package_calls = [
        (f"{base}/package_show", {"id": PACKAGE_ID}) for base in CKAN_ENDPOINTS
    ]
    response = _request_with_retries(session, package_calls, timeout=90)
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError("official CKAN package lookup failed")
    resource, reason = select_resource(payload["result"].get("resources", []))
    return payload, resource, "package_fallback; " + reason


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _find(columns: Iterable[str], aliases: Iterable[str]) -> str | None:
    normed = {_norm(c): c for c in columns}
    for alias in aliases:
        alias_n = _norm(alias)
        for key, original in normed.items():
            if alias_n == key or alias_n in key:
                return original
    return None


@dataclass(frozen=True)
class FuelCalibrationResult:
    source_url: str
    source_hash: str
    raw_rows: int
    transformed_events: int
    contexts: int
    products: int
    coverage_start: str | None
    coverage_end: str | None
    selection_reason: str


def select_resource(resources: list[dict]) -> tuple[dict, str]:
    candidates = []
    current_year = datetime.now(timezone.utc).year
    for resource in resources:
        if str(resource.get("format", "")).lower() != "csv":
            continue
        text = _norm(" ".join(str(resource.get(k, "")) for k in ("name", "description", "url")))
        years = [int(x) for x in re.findall(r"20\d{2}", text) if int(x) <= current_year]
        year = max(years) if years else 0
        current_bonus = 5 if year >= current_year - 1 else 0
        full_bonus = 2 if "partir_de_2018" in text else 0
        candidates.append((year + current_bonus + full_bonus, resource, text))
    if not candidates:
        raise RuntimeError("official fuel package has no CSV resource")
    candidates.sort(key=lambda x: x[0], reverse=True)
    score, resource, text = candidates[0]
    return resource, f"highest_dynamic_csv_score={score}; descriptor={text[:240]}"


def acquire_and_transform(
    output_dir: str | Path,
    *,
    session: requests.Session | None = None,
    max_download_bytes: int = 300_000_000,
) -> FuelCalibrationResult:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    session = session or requests.Session()
    session.headers.update({"User-Agent": "BayME-MC-Gate5/0.3"})
    metadata, resource, reason = _resolve_resource(session)
    source_url = resource["url"]
    download_urls = [(source_url, None)]
    if "://datos.gob.ar/" in source_url:
        download_urls.append((source_url.replace("://datos.gob.ar/", "://www.datos.gob.ar/"), None))
    response = _request_with_retries(
        session, download_urls, timeout=180, attempts=5, stream=True
    )
    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        total += len(chunk)
        if total > max_download_bytes:
            raise RuntimeError("official resource exceeds frozen download ceiling")
        chunks.append(chunk)
    raw = b"".join(chunks)
    source_hash = hashlib.sha256(raw).hexdigest()
    (output / "package_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "source_receipt.json").write_text(
        json.dumps(
            {
                "source_url": source_url,
                "source_hash": source_hash,
                "bytes": len(raw),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "selection_reason": reason,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    frame = pd.read_csv(io.BytesIO(raw), low_memory=False)
    date_col = _find(frame.columns, ["fecha", "indice_tiempo", "periodo", "mes"])
    price_col = _find(frame.columns, ["precio", "precio_venta"])
    quantity_col = _find(frame.columns, ["volumen", "cantidad", "volumen_m3"])
    province_col = _find(frame.columns, ["provincia"])
    locality_col = _find(frame.columns, ["localidad", "municipio", "departamento"])
    product_col = _find(frame.columns, ["producto", "tipo_combustible", "combustible"])
    merchant_col = _find(frame.columns, ["empresa", "bandera", "razon_social", "establecimiento"])
    if not date_col or not price_col or not province_col or not product_col:
        raise RuntimeError(f"unsupported official fuel columns: {list(frame.columns)}")

    slim = pd.DataFrame(
        {
            "date": pd.to_datetime(frame[date_col], errors="coerce"),
            "price": pd.to_numeric(frame[price_col], errors="coerce"),
            "quantity": pd.to_numeric(frame[quantity_col], errors="coerce") if quantity_col else None,
            "province": frame[province_col].astype(str),
            "locality": frame[locality_col].astype(str) if locality_col else "UNKNOWN",
            "product": frame[product_col].astype(str),
            "merchant": frame[merchant_col].astype(str) if merchant_col else "UNKNOWN",
        }
    ).dropna(subset=["date", "price"])
    slim = slim[slim["price"] > 0].copy()
    slim["month"] = slim["date"].dt.to_period("M").dt.to_timestamp()
    slim["context_id"] = slim.apply(
        lambda r: f"AR:{_norm(r.province)}:{_norm(r.locality)}", axis=1
    )
    slim["product_code"] = slim["product"].map(_norm)

    rows = []
    for keys, group in slim.groupby(
        ["month", "context_id", "product_code", "product"], dropna=False
    ):
        month, context_id, product_code, product_label = keys
        quantities = group["quantity"] if "quantity" in group else pd.Series(dtype=float)
        if quantities.notna().any() and float(quantities.fillna(0).sum()) > 0:
            weights = quantities.fillna(0).clip(lower=0)
            price = float((group["price"] * weights).sum() / weights.sum())
            quantity = float(weights.sum())
            unit = "reported_volume"
        else:
            price = float(group["price"].median())
            quantity = None
            unit = None
        observation_material = f"{source_hash}|{month}|{context_id}|{product_code}"
        observation_id = "pq-" + hashlib.sha256(observation_material.encode()).hexdigest()[:24]
        event = PriceQuantityEventV1(
            observation_id=observation_id,
            observed_at=month.to_pydatetime().replace(tzinfo=timezone.utc),
            context_id=context_id,
            product_code=product_code,
            product_label=str(product_label),
            observation_level="aggregate",
            price_ars=price,
            quantity=quantity,
            quantity_unit=unit,
            merchant_count=max(1, int(group["merchant"].nunique())),
            source_id="datos_argentina_fuel_prices_volumes",
            source_hash=source_hash,
            measurement_version="gate5-fuel-adapter-v2-resilient",
        )
        rows.append(event)

    with (output / "price_quantity_events.jsonl").open("w", encoding="utf-8") as handle:
        for event in rows:
            handle.write(event.model_dump_json() + "\n")
    summary = FuelCalibrationResult(
        source_url=source_url,
        source_hash=source_hash,
        raw_rows=len(frame),
        transformed_events=len(rows),
        contexts=slim["context_id"].nunique(),
        products=slim["product_code"].nunique(),
        coverage_start=slim["date"].min().date().isoformat() if not slim.empty else None,
        coverage_end=slim["date"].max().date().isoformat() if not slim.empty else None,
        selection_reason=reason,
    )
    (output / "calibration_summary.json").write_text(
        json.dumps(summary.__dict__, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
