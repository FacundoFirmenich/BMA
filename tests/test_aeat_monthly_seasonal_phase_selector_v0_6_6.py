import pytest

from bma.experiments import aeat_monthly_seasonal_phase_selector_v0_6_6 as selector


def test_participation_dispatches_harmonic_summer_and_hierarchy_autumn():
    expected = {
        1: "M0", 2: "M0", 3: "M0", 4: "M0", 5: "M0",
        6: "M1", 7: "M1", 8: "M1", 9: "M1",
        10: "M2", 11: "M2", 12: "M0",
    }
    observed = {
        month: selector.select("participation", f"2025-{month:02d}").model_id
        for month in range(1, 13)
    }
    assert observed == expected


def test_quantity_and_unit_value_windows_are_strictly_local():
    quantity = [selector.select("quantity", f"2025-{month:02d}").model_id for month in range(1, 13)]
    unit_value = [selector.select("unit_value", f"2025-{month:02d}").model_id for month in range(1, 13)]
    assert quantity == ["M0"] * 8 + ["M2"] + ["M0"] * 3
    assert unit_value == ["M0", "M0", "M1"] + ["M0"] * 9


def test_december_abstains_but_keeps_an_update_model_for_every_variable():
    for variable in selector.VARIABLES:
        decision = selector.select(variable, "2025-12")
        assert decision.model_id == "M0"
        assert decision.primary_status == "ABSTAIN_YEAR_END_UNCALIBRATED"


def test_confirmatory_gate_rejects_discovery_years_and_accepts_unused_year():
    for year in selector.DISCOVERY_YEARS:
        with pytest.raises(Exception, match="cannot reuse"):
            selector.require_unused_validation_target(f"{year}-06")
    selector.require_unused_validation_target("2025-06")


def test_unknown_variable_and_malformed_period_fail_closed():
    with pytest.raises(Exception, match="unknown selector variable"):
        selector.select("price", "2025-03")
    with pytest.raises(Exception, match="invalid monthly period"):
        selector.select("participation", "2025-13")
