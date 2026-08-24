import pytest

from bma.experiments import training_age_causal_chains_v0_6_6 as age


def test_aligned_panel_uses_same_phase_and_every_intermediate_month():
    arms = age.build_aligned_panel("2025-06")
    assert [arm.nominal_age_months for arm in arms] == [12, 24, 36]
    assert [arm.seed_period for arm in arms] == ["2024-06", "2023-06", "2022-06"]
    for arm in arms:
        assert len(arm.steps) == arm.nominal_age_months
        assert arm.steps[0].training_period == arm.seed_period
        assert arm.steps[-1].target_period == "2025-06"
        assert arm.final_training_period == "2025-05"
        for previous, following in zip(arm.steps, arm.steps[1:]):
            assert previous.target_period == following.training_period
        assert all(step.events == (
            "FREEZE_BEFORE_TARGET_OPEN",
            "OPEN_SEALED_TARGET",
            "ADJUDICATE",
            "WRITE_PRIOR_AND_Z_POST",
        ) for step in arm.steps)


def test_age_panel_produces_all_pairwise_local_contrasts():
    arms = age.build_aligned_panel("2025-03")
    assert age.paired_age_contrasts(arms) == ((12, 24), (12, 36), (24, 36))


def test_nonannual_or_duplicate_ages_fail_closed():
    with pytest.raises(age.GateFailure, match="positive multiples"):
        age.build_age_arm("2025-06", 18)
    with pytest.raises(age.GateFailure, match="unique"):
        age.build_aligned_panel("2025-06", (12, 12, 24))


def test_discovery_year_and_december_cannot_be_primary_targets():
    with pytest.raises(age.GateFailure, match="discovery year"):
        age.build_aligned_panel("2024-06")
    with pytest.raises(age.GateFailure, match="YEAR_END_UNCALIBRATED"):
        age.build_aligned_panel("2025-12")


def test_malformed_period_and_single_arm_fail_closed():
    with pytest.raises(age.GateFailure, match="invalid monthly period"):
        age.build_aligned_panel("2025-13")
    with pytest.raises(age.GateFailure, match="at least two"):
        age.build_aligned_panel("2025-06", (12,))
