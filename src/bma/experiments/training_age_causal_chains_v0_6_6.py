"""Invariant engine for calendar-aligned causal training-age chains."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


SCHEMA = "bma.training-age.causal-chains.v0.6.6"
DISCOVERY_YEARS = frozenset({2022, 2023, 2024})


class GateFailure(RuntimeError):
    pass


def period_index(period: str) -> int:
    try:
        year_text, month_text = period.split("-")
        year, month = int(year_text), int(month_text)
    except (AttributeError, ValueError) as exc:
        raise GateFailure(f"invalid monthly period {period!r}") from exc
    if year < 1 or not 1 <= month <= 12:
        raise GateFailure(f"invalid monthly period {period!r}")
    return year * 12 + month - 1


def period_from_index(index: int) -> str:
    if index < 12:
        raise GateFailure("period index predates year 1")
    year, zero_month = divmod(index, 12)
    return f"{year:04d}-{zero_month + 1:02d}"


def calendar_month(period: str) -> int:
    return period_index(period) % 12 + 1


@dataclass(frozen=True)
class ChainStep:
    training_period: str
    target_period: str
    events: tuple[str, ...] = (
        "FREEZE_BEFORE_TARGET_OPEN",
        "OPEN_SEALED_TARGET",
        "ADJUDICATE",
        "WRITE_PRIOR_AND_Z_POST",
    )


@dataclass(frozen=True)
class AgeArm:
    target_period: str
    nominal_age_months: int
    seed_period: str
    steps: tuple[ChainStep, ...]

    @property
    def final_training_period(self) -> str:
        return self.steps[-1].training_period


def build_age_arm(target_period: str, nominal_age_months: int) -> AgeArm:
    target = period_index(target_period)
    if nominal_age_months <= 0 or nominal_age_months % 12 != 0:
        raise GateFailure("training ages must be positive multiples of 12 months")
    seed = target - nominal_age_months
    seed_period = period_from_index(seed)
    if calendar_month(seed_period) != calendar_month(target_period):
        raise GateFailure("age arm does not preserve calendar phase")
    steps = tuple(
        ChainStep(period_from_index(index - 1), period_from_index(index))
        for index in range(seed + 1, target + 1)
    )
    if len(steps) != nominal_age_months:
        raise GateFailure("age arm condensed or skipped a monthly transition")
    return AgeArm(target_period, nominal_age_months, seed_period, steps)


def build_aligned_panel(
    target_period: str,
    nominal_ages_months: tuple[int, ...] = (12, 24, 36),
) -> tuple[AgeArm, ...]:
    target_year = int(target_period.split("-")[0]) if "-" in target_period else -1
    period_index(target_period)
    if target_year in DISCOVERY_YEARS:
        raise GateFailure("confirmatory training-age panels cannot target a 2022--2024 discovery year")
    if calendar_month(target_period) == 12:
        raise GateFailure("December is YEAR_END_UNCALIBRATED for primary age adjudication")
    if len(set(nominal_ages_months)) != len(nominal_ages_months):
        raise GateFailure("age arms must be unique")
    arms = tuple(build_age_arm(target_period, age) for age in sorted(nominal_ages_months))
    if len(arms) < 2:
        raise GateFailure("an age comparison requires at least two arms")
    if any(arm.target_period != target_period for arm in arms):
        raise GateFailure("age arms do not share the identical target")
    return arms


def paired_age_contrasts(arms: tuple[AgeArm, ...]) -> tuple[tuple[int, int], ...]:
    if len(arms) < 2 or len({arm.target_period for arm in arms}) != 1:
        raise GateFailure("paired contrasts require aligned arms for one target")
    return tuple(
        (younger.nominal_age_months, older.nominal_age_months)
        for younger, older in combinations(sorted(arms, key=lambda arm: arm.nominal_age_months), 2)
    )
