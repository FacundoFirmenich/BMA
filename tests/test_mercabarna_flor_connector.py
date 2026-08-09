from __future__ import annotations

from datetime import date

import pytest

from bma.connectors.mercabarna_flor import ConnectorFailure, parse_csv, parse_decimal_comma, parse_grouped_integer


def test_numeric_parsing_matches_source_conventions() -> None:
    assert parse_grouped_integer("1.234") == 1234
    assert parse_decimal_comma("12,50") == 12.5


def test_structured_parser_discards_accumulated_columns() -> None:
    text = (
        "Mercabarna;;;;;\n"
        "Flor;;;;;\n"
        "Periodo:01-07-2026 / 01-07-2026\n"
        "Producto;Total unidades origen periodo;Precio Periodo;Acumulado;Acumulados;Origen\n"
        "ROSA FLORES I PLANTAS;1.234;12,50;999;999;Barcelona\n"
    )
    rows, metadata = parse_csv(text, date(2026, 7, 1), "48")
    assert rows[0]["unit_count"] == 1234
    assert rows[0]["price_eur_per_unit"] == 12.5
    assert metadata["forbidden_accumulated_columns_discarded"] == ["Acumulado", "Acumulados"]


def test_parser_rejects_wrong_period() -> None:
    text = (
        "Mercabarna;;;;;\nFlor;;;;;\nPeriodo:02-07-2026 / 02-07-2026\n"
        "Producto;Total unidades origen periodo;Precio Periodo;Acumulado;Acumulados;Origen\n"
    )
    with pytest.raises(ConnectorFailure):
        parse_csv(text, date(2026, 7, 1), "48")
