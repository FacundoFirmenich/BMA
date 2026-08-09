from __future__ import annotations

import json
from pathlib import Path

import pytest

from bma.custody import CustodyError, verify_manifest, write_json_new, write_manifest


def test_immutable_json_and_manifest(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.json"
    write_json_new(artifact, {"b": 2, "a": 1})
    assert json.loads(artifact.read_text(encoding="utf-8")) == {"a": 1, "b": 2}
    with pytest.raises(CustodyError):
        write_json_new(artifact, {"a": 3})
    write_manifest(tmp_path)
    assert verify_manifest(tmp_path)["status"] == "PASS"


def test_manifest_detects_tampering(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.json"
    write_json_new(artifact, {"state": "frozen"})
    write_manifest(tmp_path)
    artifact.write_text("tampered", encoding="utf-8")
    receipt = verify_manifest(tmp_path)
    assert receipt["status"] == "FAIL"
    assert receipt["failures"][0]["reason"] == "HASH_MISMATCH"
