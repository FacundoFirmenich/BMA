import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "evidence" / "runs" / "bpm-luke-roundwood-public-probe-v0.1"


def load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_preregistration_and_amendment_precede_data_values() -> None:
    prereg = json.loads(
        (ROOT / "preregistrations" / "BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_V0.1.json").read_text(encoding="utf-8")
    )
    amendment = json.loads(
        (ROOT / "preregistrations" / "BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_AMENDMENT_A1.json").read_text(encoding="utf-8")
    )
    manifest = load("capture_manifest.json")
    assert prereg["status"] == "PREREGISTERED_BEFORE_SCHEMA_OR_DATA_BYTE_ACQUISITION"
    assert amendment["status"] == "FROZEN_AFTER_METADATA_ONLY_BEFORE_ANY_DATA_VALUE"
    assert amendment["observed_metadata_only"]["data_values_opened"] is False
    assert manifest["preregistration"]["sha256"] == sha(
        ROOT / "preregistrations" / "BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_V0.1.json"
    )
    assert manifest["amendment"]["sha256"] == sha(
        ROOT / "preregistrations" / "BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_AMENDMENT_A1.json"
    )


def test_exact_product_market_cell_has_price_and_volume() -> None:
    adjudication = load("probe_adjudication.json")
    assert adjudication["status"] == "PASS_SINGLE_PRODUCT_PRICE_VOLUME_SUPPORT"
    assert adjudication["jurisdiction"]["country"] == "Finland"
    assert adjudication["jurisdiction"]["reference_month"] == "2026-07"
    assert adjudication["jurisdiction"]["sale_type"] == "Standing sales"
    assert adjudication["jurisdiction"]["product"] == "Spruce logs"
    assert adjudication["observation"]["volume_source_value_thousand_m3"] == 429
    assert adjudication["observation"]["volume_m3"] == 429000
    assert adjudication["observation"]["price_eur_per_m3"] == 83.14


def test_support_is_long_enough_but_vintages_are_not_reconstructed() -> None:
    adjudication = load("probe_adjudication.json")
    support = adjudication["support"]
    boundaries = adjudication["quality_boundaries"]
    assert support["metadata_month_count"] == 79
    assert support["metadata_first_month"] == "2020M01"
    assert support["metadata_last_month"] == "2026M07"
    assert support["at_least_36_months"] is True
    assert boundaries["post_release_observation"] is True
    assert boundaries["first_release_vintages_preserved"] is False
    assert boundaries["revision_notes_present"] is True
    assert boundaries["response_extension_official_statistics_flag"] is False


def test_probe_has_no_model_or_cross_jurisdiction_authority() -> None:
    authority = load("probe_adjudication.json")["authority"]
    assert authority["candidate"].startswith("PROMOTE_TO_SEPARATELY_PREREGISTERED")
    for field in (
        "model_fit",
        "forecast",
        "score",
        "posterior_update",
        "Z_post_update",
        "historical_freeze_reconstruction",
        "cross_source_pooling",
        "automatic_promotion",
    ):
        assert authority[field] is False
    assert authority["global_winner"] is None

