import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "preregistrations" / "HBP_PORT_TED_PROSPECTIVE_OBSERVER_CHAIN_V0.1.json"
ADJUDICATION = (
    ROOT
    / "evidence"
    / "runs"
    / "hbp-port-ted-prospective-observer-chain-v0.1"
    / "observer_adjudication.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_preregistration_precedes_future_acquisition_and_bars_premature_model_use() -> None:
    prereg = _load(PREREG)
    assert prereg["status"] == "PREREGISTERED_BEFORE_ANY_FUTURE_RELEASE_ACQUISITION"
    assert prereg["coral_rule"]["automatic_M2_or_M3_entry"] is False
    assert prereg["coral_rule"]["cross_source_pooling"] is False
    assert prereg["coral_rule"]["global_winner"] is None
    assert prereg["puertos_chain"]["model_candidacy_gate"]["minimum_prospectively_paired_months"] == 12
    assert prereg["ted_chain"]["model_candidacy_gate"]["minimum_prospectively_paired_months"] == 12


def test_anchor_hashes_and_no_execution_claims() -> None:
    adjudication = _load(ADJUDICATION)
    assert adjudication["preregistration"]["sha256"] == _sha256(PREREG)
    assert adjudication["puertos"]["raw"]["sha256"] == _sha256(
        ROOT / adjudication["puertos"]["raw"]["path"]
    )
    assert adjudication["ted"]["raw"]["sha256"] == _sha256(
        ROOT / adjudication["ted"]["raw"]["path"]
    )
    invariants = adjudication["invariants"]
    for field in (
        "fit_performed",
        "forecast_performed",
        "score_performed",
        "posterior_updated",
        "Z_post_updated",
        "historical_freeze_reconstructed",
        "cross_source_likelihood_pooling",
        "automatic_promotion",
    ):
        assert invariants[field] is False
    assert invariants["global_winner"] is None


def test_puertos_support_and_monthly_nature_limit_are_preserved() -> None:
    puertos = _load(ADJUDICATION)["puertos"]
    assert puertos["workbook"]["sheet_count"] == 45
    assert puertos["national_physical_activity"]["total_traffic"]["june_2026_tonnes"] == 47026235.533
    wood = puertos["selected_non_energy_natures"]["wood_and_cork"]
    assert wood["solid_bulk"]["january_to_june_2026_tonnes"] == 163148
    assert wood["general_cargo"]["january_to_june_2026_tonnes"] == 2839117
    assert puertos["historic_monthly_presentation_schema"]["years_exposed"] == [2019, 2020, 2021, 2022]
    assert puertos["historic_monthly_presentation_schema"]["current_2026_monthly_by_nature_exposed"] is False
    assert puertos["nature_monthly_status"] == "NOT_ESTIMABLE_NO_CURRENT_MONTHLY_NATURE_CELL"
    assert puertos["cumulative_difference_status"].startswith("FORBIDDEN_REVISION_MIXED_INCREMENT")


def test_ted_support_is_event_count_only() -> None:
    ted = _load(ADJUDICATION)["ted"]
    coverage = ted["response"]["field_coverage"]
    assert ted["response"]["reported_total_notice_count"] == 3132
    assert ted["response"]["sampled_notices"] == 10
    assert ted["response"]["unique_publication_numbers"] == 10
    assert coverage["publication_number"] == coverage["publication_date"] == 10
    assert coverage["cpv"] == coverage["place"] == 10
    assert coverage["award_value"] == 4
    assert coverage["currency"] == 5
    assert coverage["quantity_fields"] == 0
    assert ted["authority"] == "INSTITUTIONAL_DEMAND_EVENT_COUNT_OBSERVER_ONLY"
    assert ted["value_status"] == "NOT_ESTIMABLE_INCOMPLETE_VALUE_AND_CURRENCY"
    assert ted["quantity_status"] == "NOT_ESTIMABLE_NO_QUANTITY_FIELD"


def test_coral_layer_abstains_without_causal_alignment() -> None:
    coral = _load(ADJUDICATION)["coral_adjudication"]
    assert coral["direct_product_monthly_role"] == "NOT_ESTIMABLE"
    assert coral["M2_status"] == "ABSTAIN_UNTIL_TARGET_SPECIFIC_FREEZE_AND_SUPPORT_GATE"
    assert coral["M3_status"] == "ABSTAIN_NO_CAUSALLY_ALIGNED_MULTI_SOURCE_LIKELIHOOD"
