from __future__ import annotations

import pytest

from bma.connectors.aeat_trade import AeatContractError
from bma.connectors.aeat_trade_daily import aggregate_records_by_event_day, parse_event_date


def _record(day: int, *, weight_grams: int = 1000) -> bytes:
    raw = bytearray(b" " * 226)
    raw[0:1] = b"I"
    raw[1:5] = b"2401"
    raw[5:7] = b"08"
    raw[19:25] = f"2401{day:02d}".encode()
    raw[25:37] = b"7208390090  "
    raw[37:38] = b"I"
    raw[66:69] = b"FR "
    raw[69:72] = b"FR "
    raw[75:77] = b"08"
    raw[82:84] = b"40"
    raw[84:86] = b"00"
    raw[89:104] = f"{weight_grams:015d}".encode()
    raw[104:119] = f"{0:015d}".encode()
    raw[119:131] = f"{10000:012d}".encode()
    raw[131:143] = f"{10000:012d}".encode()
    raw[158:159] = b"0"
    raw[159:164] = b"00000"
    raw[164:165] = b"3"
    raw[165:166] = b"3"
    raw[170:171] = b"C"
    raw[172:174] = b"11"
    raw[174:177] = b"FCA"
    raw[224:226] = b"08"
    return bytes(raw)


def test_event_date_is_strict_and_period_bound() -> None:
    assert parse_event_date("240105", expected_year=2024, expected_month=1).isoformat() == "2024-01-05"
    with pytest.raises(AeatContractError):
        parse_event_date("240231", expected_year=2024, expected_month=2)
    with pytest.raises(AeatContractError):
        parse_event_date("240205", expected_year=2024, expected_month=1)


def test_daily_aggregation_preserves_distinct_days() -> None:
    rows, counts = aggregate_records_by_event_day(
        [_record(5), _record(5, weight_grams=2000), _record(6)], year=2024, month=1
    )
    assert len(rows) == 2
    assert rows[0]["event_date"] == "2024-01-05"
    assert rows[0]["weight_kg"] == 3.0
    assert rows[1]["event_date"] == "2024-01-06"
    assert counts["observed_event_days"] == 2
    assert counts["missing_calendar_days_are_zero"] is False
    assert counts["operational_daily_feed"] is False
