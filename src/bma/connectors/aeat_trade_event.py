"""Loss-minimizing event projection for AEAT maximum-detail records.

The source carries a daily admission date but is transported in monthly files.
Each declaration line remains an individual marked event. Aggregates are
downstream derived views and are not a replacement for these observations.
"""

from __future__ import annotations

import hashlib
from typing import Any

from bma.connectors.aeat_trade import parse_record
from bma.connectors.aeat_trade_daily import parse_event_date


def project_chapter72_event(
    raw: bytes, *, expected_year: int, expected_month: int, source_line_number: int
) -> dict[str, Any] | None:
    """Project one source line without averaging or imputing temporal detail."""
    row = parse_record(raw, expected_year=expected_year, expected_month=expected_month)
    event_date = parse_event_date(
        str(row["admission_date"]),
        expected_year=expected_year,
        expected_month=expected_month,
    )
    if not str(row["cn8"]).startswith("72"):
        return None
    projected = dict(row)
    projected.pop("admission_date")
    projected.update(
        {
            "schema_version": "bma.aeat.chapter72.marked-event.v0.7.0",
            "event_kind": "customs_declaration_line",
            "event_date": event_date.isoformat(),
            "event_time_resolution": "day",
            "source_release_granularity": "monthly",
            "operational_daily_feed": False,
            "source_line_number": source_line_number,
            "source_record_sha256": hashlib.sha256(raw).hexdigest(),
            "cell_id": (
                f"{row['flow']}|{row['cn8']}|{row['partner_country'] or 'UNK'}"
            ),
            "statistical_value_is_transaction_price": False,
        }
    )
    return projected
