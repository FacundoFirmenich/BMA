from __future__ import annotations

from enum import Enum


class QuaternaryState(str, Enum):
    """Operational interpretation of the 1/-1/+0/0 state space."""

    AUTHORIZED = "1"
    REJECTED = "-1"
    SHADOW_CANDIDATE = "+0"
    EPISTEMIC_NULL = "0"


class EvidenceStatus(str, Enum):
    ADMISSIBLE = "admissible"
    PENDING = "pending"
    INADMISSIBLE = "inadmissible"
    LOCAL_NO_EVIDENCE = "local_no_evidence"
    NOT_ESTIMABLE = "not_estimable"


class AuthorityRole(str, Enum):
    CONGRESS = "congress"
    STATISTICAL_ADJUDICATOR = "statistical_adjudicator"
    EVIDENCE_COUNCIL = "evidence_council"
    EXECUTOR = "executor"
    DATA_DEFENDER = "data_defender"
    MODEL_OPERATOR = "model_operator"
    AUDITOR = "auditor"


class PolicyActionType(str, Enum):
    TRANSFER = "transfer"
    CREDIT = "credit"
    RATE_SUBSIDY = "rate_subsidy"
    DEBT_RESTRUCTURE = "debt_restructure"
    SUPPLY_CREDIT = "supply_credit"
    LOGISTICS_SUPPORT = "logistics_support"
    FLEXIBILITY_CHANGE = "flexibility_change"
    PAUSE = "pause"


class LedgerKind(str, Enum):
    MONETARY = "monetary"
    POLICY = "policy"
    OUTCOME = "outcome"
    EVIDENCE = "evidence"
