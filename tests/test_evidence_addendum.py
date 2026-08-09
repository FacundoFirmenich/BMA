from pathlib import Path

from bma.evidence import load_and_validate


def test_execution_addendum_is_valid() -> None:
    path = Path(__file__).parents[1] / "evidence" / "registry_addendum_20260809.json"
    result = load_and_validate(path)
    assert result == {
        "status": "PASS",
        "entries": 2,
        "ids": ["MB-FLOR-V041-ORIGIN-CONTROL", "MB-FLOR-V050-FULL-JULY"],
    }
