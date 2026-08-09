from __future__ import annotations

import math

from bma.connectors.aeat_trade import aggregate_records, archive_url, parse_record
from bma.experiments.aeat_steel_v0_6_1 import (
    _continuous_context,
    _continuous_predictions,
    _metadata,
    _participation_context,
    _participation_predictions,
)


def record(
    *,
    flow: str = "I",
    position: str = "7208390090",
    country: str = "FR ",
    weight_grams: int = 12_500,
    units_milli: int = 0,
    statistical_cents: int = 9_875,
    invoice_cents: int = 10_000,
) -> bytes:
    raw = bytearray(b" " * 226)
    raw[0:1] = flow.encode()
    raw[1:5] = b"2401"
    raw[5:7] = b"08"
    raw[19:25] = b"240105"
    raw[25:37] = position.ljust(12).encode()
    raw[37:38] = b"I"
    raw[38:46] = b" " * 8
    raw[66:69] = country.encode()
    raw[69:72] = b"FR "
    raw[75:77] = b"08"
    raw[82:84] = b"40"
    raw[84:86] = b"00"
    raw[89:104] = f"{weight_grams:015d}".encode()
    raw[104:119] = f"{units_milli:015d}".encode()
    raw[119:131] = f"{statistical_cents:012d}".encode()
    raw[131:143] = f"{invoice_cents:012d}".encode()
    raw[158:159] = b"0"
    raw[159:164] = b"00000"
    raw[164:165] = b"3"
    raw[165:166] = b"3"
    raw[170:171] = b"C"
    raw[172:174] = b"11"
    raw[174:177] = b"FCA"
    raw[224:226] = b"08"
    return bytes(raw)


def test_archive_url_is_official_month_pattern() -> None:
    assert archive_url(2024, 1).endswith("/2024/enero/cg24en74.zip")
    assert archive_url(2024, 12).endswith("/2024/diciembre/cg24dc74.zip")


def test_fixed_width_record_scaling() -> None:
    row = parse_record(record(), expected_year=2024, expected_month=1)
    assert row["cn8"] == "72083900"
    assert row["weight_kg"] == 12.5
    assert row["statistical_value_eur"] == 98.75
    assert row["invoice_value_eur"] == 100.0


def test_aggregate_filters_to_chapter72_and_preserves_dimensions() -> None:
    cells, counts = aggregate_records(
        [record(), record(weight_grams=7_500, statistical_cents=4_000), record(position="7304410090")],
        year=2024,
        month=1,
    )
    assert counts == {"total_lines": 3, "chapter72_lines": 2, "cells": 1}
    assert cells[0]["weight_kg"] == 20.0
    assert cells[0]["statistical_value_eur"] == 138.75
    assert cells[0]["dimension_cardinality"]["customs_province"] == 1


def test_hierarchical_contexts_are_finite_and_target_blind() -> None:
    maps = [
        {
            "I|72083900|FR": {
                "cell_id": "I|72083900|FR",
                "flow": "I",
                "cn8": "72083900",
                "cn4": "7208",
                "partner_country": "FR",
                "weight_kg": value,
                "statistical_unit_value_eur_per_kg": unit_value,
            }
        }
        for value, unit_value in ((10.0, 0.8), (12.0, 0.9), (11.0, 0.85))
    ]
    metadata = _metadata(maps)
    participation = _participation_predictions(_participation_context(maps, metadata), metadata, "I|72083900|FR")
    continuous = _continuous_predictions(_continuous_context(maps, metadata, "weight_kg"), metadata, "I|72083900|FR")
    assert all(0 < value < 1 for value in participation.values())
    assert continuous is not None
    assert all(math.isfinite(value) for value in continuous.values())
