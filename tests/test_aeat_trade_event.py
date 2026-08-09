from __future__ import annotations

from bma.connectors.aeat_trade_event import project_chapter72_event


def _record(*, day: int, weight_grams: int, position: str = "7208390090") -> bytes:
    raw = bytearray(b" " * 226)
    raw[0:1] = b"I"
    raw[1:5] = b"2401"
    raw[5:7] = b"08"
    raw[19:25] = f"2401{day:02d}".encode()
    raw[25:37] = position.ljust(12).encode()
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


def test_event_projection_preserves_lines_with_same_day() -> None:
    first = project_chapter72_event(
        _record(day=5, weight_grams=1000),
        expected_year=2024,
        expected_month=1,
        source_line_number=1,
    )
    second = project_chapter72_event(
        _record(day=5, weight_grams=2000),
        expected_year=2024,
        expected_month=1,
        source_line_number=2,
    )
    assert first is not None and second is not None
    assert first["event_date"] == second["event_date"] == "2024-01-05"
    assert first["weight_kg"] == 1.0
    assert second["weight_kg"] == 2.0
    assert first["source_record_sha256"] != second["source_record_sha256"]
    assert first["operational_daily_feed"] is False


def test_non_chapter72_line_is_not_projected() -> None:
    assert (
        project_chapter72_event(
            _record(day=5, weight_grams=1000, position="7304410090"),
            expected_year=2024,
            expected_month=1,
            source_line_number=1,
        )
        is None
    )
