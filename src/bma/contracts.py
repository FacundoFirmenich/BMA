from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any


class ContractError(ValueError):
    pass


class PublicationState(StrEnum):
    POSITIVE_ROWS = "POSITIVE_ROWS"
    PENDING_EMPTY_NOT_ZERO = "PENDING_EMPTY_NOT_ZERO"
    CLOSED_CONFIRMED_ZERO = "CLOSED_CONFIRMED_ZERO"
    UNAVAILABLE = "UNAVAILABLE"


class EvidenceState(StrEnum):
    DEMONSTRATED = "DEMONSTRATED"
    LIMITED_TRANSFER = "LIMITED_TRANSFER"
    DEVELOPMENT_EVIDENCE = "DEVELOPMENT_EVIDENCE"
    THIN_BASELINE_DIAGNOSTIC = "THIN_BASELINE_DIAGNOSTIC"
    PROPOSED_NOT_EXECUTED = "PROPOSED_NOT_EXECUTED"
    PENDING = "PENDING"
    NOT_ESTIMABLE = "NOT_ESTIMABLE"
    REJECTED = "REJECTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class PipelineStage(StrEnum):
    RAW_CUSTODY = "RAW_CUSTODY"
    STRUCTURED_OBSERVATION = "STRUCTURED_OBSERVATION"
    COMPLETENESS_ADJUDICATED = "COMPLETENESS_ADJUDICATED"
    FREEZE = "FREEZE"
    OUTCOME_ADJUDICATED = "OUTCOME_ADJUDICATED"
    ECONOMIC_POSTERIOR = "ECONOMIC_POSTERIOR"
    FUTURE_PRIOR = "FUTURE_PRIOR"


@dataclass(frozen=True)
class MarketRow:
    cell_id: str
    product: str
    node_id: str
    node_label: str
    quantity: float
    price: float | None
    unit: str

    def __post_init__(self) -> None:
        if not self.cell_id or not self.product or not self.node_id:
            raise ContractError("cell_id, product and node_id are required")
        if self.quantity <= 0:
            raise ContractError("positive rows require quantity > 0")
        if self.price is not None and self.price < 0:
            raise ContractError("price cannot be negative")
        if not self.unit:
            raise ContractError("unit is required")


@dataclass(frozen=True)
class MarketDay:
    market_id: str
    target_date: date
    publication_state: PublicationState
    rows: tuple[MarketRow, ...]
    source_receipts: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        if self.publication_state == PublicationState.POSITIVE_ROWS and not self.rows:
            raise ContractError("POSITIVE_ROWS requires at least one row")
        if self.publication_state != PublicationState.POSITIVE_ROWS and self.rows:
            raise ContractError("non-positive publication states cannot carry positive rows")
        ids = [row.cell_id for row in self.rows]
        if len(ids) != len(set(ids)):
            raise ContractError("duplicate cell_id in market day")
        if self.publication_state == PublicationState.CLOSED_CONFIRMED_ZERO and not self.source_receipts:
            raise ContractError("economic zero requires a completeness witness")


@dataclass(frozen=True)
class PipelineReceipt:
    stage: PipelineStage
    target_date: date
    knowledge_cut: date
    emitted_at: datetime
    artifact_sha256: str
    parent_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.knowledge_cut >= self.target_date:
            raise ContractError("knowledge_cut must precede target_date")
        if self.emitted_at.tzinfo is None:
            raise ContractError("emitted_at must be timezone-aware")
        if len(self.artifact_sha256) != 64:
            raise ContractError("artifact_sha256 must be a SHA-256 hex digest")

    @classmethod
    def now(
        cls,
        stage: PipelineStage,
        target_date: date,
        knowledge_cut: date,
        artifact_sha256: str,
        parent_sha256: str | None = None,
    ) -> "PipelineReceipt":
        return cls(stage, target_date, knowledge_cut, datetime.now(timezone.utc), artifact_sha256, parent_sha256)
