from __future__ import annotations

import json
from pathlib import Path

import pytest

from bma.evidence import EvidenceRegistryError, load_and_validate, validate_registry


def test_repository_registry_is_valid() -> None:
    path = Path(__file__).parents[1] / "evidence" / "registry.json"
    result = load_and_validate(path)
    assert result["status"] == "PASS"
    assert result["entries"] >= 15


def test_registry_forbids_global_winner() -> None:
    path = Path(__file__).parents[1] / "evidence" / "registry.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["entries"][0]["global_winner"] = "BMA"
    with pytest.raises(EvidenceRegistryError):
        validate_registry(document)
