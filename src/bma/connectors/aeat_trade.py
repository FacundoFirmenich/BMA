"""Bounded, in-memory reader for AEAT maximum-disaggregation trade archives.

The connector never persists the source ZIP. It validates the fixed-width
226-byte record contract, filters chapter 72 (iron and steel), and emits
monthly aggregates at flow x CN8 x partner-country resolution.
"""

from __future__ import annotations

from collections.abc import Iterable
import hashlib
import io
import urllib.request
import zipfile
from dataclasses import dataclass, field
from typing import Any, BinaryIO

RECORD_LENGTH = 226
MAX_COMPRESSED_BYTES = 30_000_000
MAX_UNCOMPRESSED_BYTES = 250_000_000
MONTH_CODES = {
    1: ("enero", "en"),
    2: ("febrero", "fb"),
    3: ("marzo", "mz"),
    4: ("abril", "ab"),
    5: ("mayo", "my"),
    6: ("junio", "jn"),
    7: ("julio", "jl"),
    8: ("agosto", "ag"),
    9: ("septiembre", "sp"),
    10: ("octubre", "oc"),
    11: ("noviembre", "nv"),
    12: ("diciembre", "dc"),
}
BASE_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Tema/Aduanas/"
    "Comercio_exterior/maxima_desag_mens"
)


class AeatContractError(RuntimeError):
    """Raised when transport or record evidence violates the frozen contract."""


def archive_url(year: int, month: int) -> str:
    month_name, month_code = MONTH_CODES[month]
    return f"{BASE_URL}/{year}/{month_name}/cg{year % 100:02d}{month_code}74.zip"


def _integer(raw: bytes, label: str) -> int:
    if not raw or any(byte < 48 or byte > 57 for byte in raw):
        raise AeatContractError(f"non-numeric {label}: {raw!r}")
    return int(raw)


def parse_record(raw: bytes, *, expected_year: int, expected_month: int) -> dict[str, Any]:
    if len(raw) != RECORD_LENGTH:
        raise AeatContractError(f"record length {len(raw)} != {RECORD_LENGTH}")
    flow = raw[0:1].decode("ascii")
    if flow not in {"I", "E"}:
        raise AeatContractError(f"unknown flow {flow!r}")
    observed_year = 2000 + _integer(raw[1:3], "year")
    observed_month = _integer(raw[3:5], "month")
    if (observed_year, observed_month) != (expected_year, expected_month):
        raise AeatContractError(
            f"period mismatch {(observed_year, observed_month)} != {(expected_year, expected_month)}"
        )
    position12 = raw[25:37].decode("ascii").strip()
    if len(position12) < 8 or not position12[:8].isdigit():
        raise AeatContractError(f"invalid statistical position {position12!r}")
    return {
        "flow": flow,
        "cn8": position12[:8],
        "position12": position12,
        "customs_province": raw[5:7].decode("ascii"),
        "admission_date": raw[19:25].decode("ascii"),
        "declaration_type": raw[37:38].decode("ascii"),
        "additional_codes": raw[38:46].decode("ascii").strip(),
        "partner_country": raw[66:69].decode("ascii").strip(),
        "dispatch_country": raw[69:72].decode("ascii").strip(),
        "origin_destination_province": raw[75:77].decode("ascii"),
        "requested_customs_regime": raw[82:84].decode("ascii"),
        "preceding_customs_regime": raw[84:86].decode("ascii"),
        "weight_kg": _integer(raw[89:104], "weight") / 1000.0,
        "supplementary_units": _integer(raw[104:119], "units") / 1000.0,
        "statistical_value_eur": _integer(raw[119:131], "statistical value") / 100.0,
        "invoice_value_eur": _integer(raw[131:143], "invoice value") / 100.0,
        "container": raw[158:159].decode("ascii"),
        "transport_regime": raw[159:164].decode("ascii"),
        "border_transport_mode": raw[164:165].decode("ascii"),
        "internal_transport_mode": raw[165:166].decode("ascii"),
        "exchange_zone": raw[170:171].decode("ascii"),
        "transaction_nature": raw[172:174].decode("ascii"),
        "delivery_conditions": raw[174:177].decode("ascii"),
        "fiscal_province": raw[224:226].decode("ascii"),
    }


@dataclass
class _Aggregate:
    flow: str
    cn8: str
    partner_country: str
    weight_kg: float = 0.0
    supplementary_units: float = 0.0
    statistical_value_eur: float = 0.0
    invoice_value_eur: float = 0.0
    line_count: int = 0
    position12: set[str] = field(default_factory=set)
    customs_provinces: set[str] = field(default_factory=set)
    origin_destination_provinces: set[str] = field(default_factory=set)
    declaration_types: set[str] = field(default_factory=set)
    requested_customs_regimes: set[str] = field(default_factory=set)
    border_transport_modes: set[str] = field(default_factory=set)
    transaction_natures: set[str] = field(default_factory=set)
    delivery_conditions: set[str] = field(default_factory=set)
    dispatch_countries: set[str] = field(default_factory=set)

    def add(self, row: dict[str, Any]) -> None:
        self.weight_kg += row["weight_kg"]
        self.supplementary_units += row["supplementary_units"]
        self.statistical_value_eur += row["statistical_value_eur"]
        self.invoice_value_eur += row["invoice_value_eur"]
        self.line_count += 1
        for field_name, target in (
            ("position12", self.position12),
            ("customs_province", self.customs_provinces),
            ("origin_destination_province", self.origin_destination_provinces),
            ("declaration_type", self.declaration_types),
            ("requested_customs_regime", self.requested_customs_regimes),
            ("border_transport_mode", self.border_transport_modes),
            ("transaction_nature", self.transaction_natures),
            ("delivery_conditions", self.delivery_conditions),
            ("dispatch_country", self.dispatch_countries),
        ):
            value = row[field_name]
            if value:
                target.add(value)

    def serializable(self) -> dict[str, Any]:
        cell_id = f"{self.flow}|{self.cn8}|{self.partner_country or 'UNK'}"
        return {
            "cell_id": cell_id,
            "flow": self.flow,
            "cn8": self.cn8,
            "cn4": self.cn8[:4],
            "partner_country": self.partner_country or "UNK",
            "weight_kg": self.weight_kg,
            "supplementary_units": self.supplementary_units,
            "statistical_value_eur": self.statistical_value_eur,
            "invoice_value_eur": self.invoice_value_eur,
            "statistical_unit_value_eur_per_kg": (
                self.statistical_value_eur / self.weight_kg if self.weight_kg > 0 else None
            ),
            "invoice_unit_value_eur_per_kg": (
                self.invoice_value_eur / self.weight_kg if self.weight_kg > 0 else None
            ),
            "line_count": self.line_count,
            "dimension_cardinality": {
                "position12": len(self.position12),
                "customs_province": len(self.customs_provinces),
                "origin_destination_province": len(self.origin_destination_provinces),
                "declaration_type": len(self.declaration_types),
                "requested_customs_regime": len(self.requested_customs_regimes),
                "border_transport_mode": len(self.border_transport_modes),
                "transaction_nature": len(self.transaction_natures),
                "delivery_conditions": len(self.delivery_conditions),
                "dispatch_country": len(self.dispatch_countries),
            },
        }


def aggregate_records(lines: Iterable[bytes], *, year: int, month: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    aggregates: dict[tuple[str, str, str], _Aggregate] = {}
    total_lines = 0
    chapter72_lines = 0
    for source in lines:
        raw = source.rstrip(b"\r\n")
        if not raw:
            continue
        total_lines += 1
        row = parse_record(raw, expected_year=year, expected_month=month)
        if not row["cn8"].startswith("72"):
            continue
        chapter72_lines += 1
        key = (row["flow"], row["cn8"], row["partner_country"] or "UNK")
        aggregate = aggregates.setdefault(key, _Aggregate(*key))
        aggregate.add(row)
    cells = [aggregates[key].serializable() for key in sorted(aggregates)]
    return cells, {"total_lines": total_lines, "chapter72_lines": chapter72_lines, "cells": len(cells)}


def _read_bounded(handle: BinaryIO, cap: int) -> bytes:
    chunks: list[bytes] = []
    observed = 0
    while True:
        chunk = handle.read(min(1024 * 1024, cap + 1 - observed))
        if not chunk:
            break
        chunks.append(chunk)
        observed += len(chunk)
        if observed > cap:
            raise AeatContractError(f"compressed archive exceeds {cap} bytes")
    return b"".join(chunks)


def fetch_month(year: int, month: int, *, timeout: int = 90) -> dict[str, Any]:
    """Fetch one archive into RAM, aggregate it, then release the raw bytes."""
    url = archive_url(year, month)
    request = urllib.request.Request(url, headers={"User-Agent": "BMA-AEAT/0.6.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        declared = int(response.headers.get("Content-Length", "0") or 0)
        if declared and declared > MAX_COMPRESSED_BYTES:
            raise AeatContractError(f"declared archive size {declared} exceeds cap")
        payload = _read_bounded(response, MAX_COMPRESSED_BYTES)
    archive_sha256 = hashlib.sha256(payload).hexdigest()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        if len(members) != 1:
            raise AeatContractError(f"expected one member, observed {len(members)}")
        member = members[0]
        if member.file_size > MAX_UNCOMPRESSED_BYTES:
            raise AeatContractError(f"uncompressed member {member.file_size} exceeds cap")
        with archive.open(member) as handle:
            cells, counts = aggregate_records(handle, year=year, month=month)
    return {
        "schema_version": "bma.aeat.maximum-detail.month.v0.6.0",
        "period": f"{year:04d}-{month:02d}",
        "scope": "chapter_72_iron_and_steel",
        "aggregation_key": ["flow", "cn8", "partner_country"],
        "source": {
            "url": url,
            "archive_sha256": archive_sha256,
            "compressed_bytes": len(payload),
            "member_name": member.filename,
            "member_uncompressed_bytes": member.file_size,
            **counts,
            "raw_archive_persisted": False,
        },
        "cells": cells,
    }
