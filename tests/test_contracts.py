from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from bma.contracts import ContractError, MarketDay, MarketRow, PipelineReceipt, PipelineStage, PublicationState


def test_empty_publication_is_not_economic_zero() -> None:
    day = MarketDay("fixture", date(2026, 7, 26), PublicationState.PENDING_EMPTY_NOT_ZERO, (), ())
    assert day.publication_state is PublicationState.PENDING_EMPTY_NOT_ZERO


def test_confirmed_zero_requires_completeness_witness() -> None:
    with pytest.raises(ContractError):
        MarketDay("fixture", date(2026, 7, 26), PublicationState.CLOSED_CONFIRMED_ZERO, (), ())


def test_positive_row_contract() -> None:
    row = MarketRow("node|product", "product", "node", "Node", 4.0, 1.2, "units")
    day = MarketDay("fixture", date(2026, 7, 21), PublicationState.POSITIVE_ROWS, (row,), ({"sha256": "a" * 64},))
    assert day.rows[0].quantity == 4.0


def test_pipeline_receipt_rejects_target_knowledge() -> None:
    with pytest.raises(ContractError):
        PipelineReceipt(
            PipelineStage.FREEZE,
            date(2026, 7, 21),
            date(2026, 7, 21),
            datetime.now(timezone.utc),
            "a" * 64,
        )
