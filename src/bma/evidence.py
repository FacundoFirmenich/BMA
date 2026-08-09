from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import EvidenceState


class EvidenceRegistryError(ValueError):
    pass


def validate_registry(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schema_version") != "bma.evidence-registry.v1":
        raise EvidenceRegistryError("unsupported evidence registry schema")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise EvidenceRegistryError("registry requires entries")
    seen: set[str] = set()
    for entry in entries:
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise EvidenceRegistryError("entry id is required")
        if identifier in seen:
            raise EvidenceRegistryError(f"duplicate entry id: {identifier}")
        seen.add(identifier)
        try:
            EvidenceState(entry.get("state"))
        except ValueError as exc:
            raise EvidenceRegistryError(f"invalid state for {identifier}") from exc
        jurisdiction = entry.get("jurisdiction")
        for required in ("market", "target", "time_scope", "claim_scope"):
            if not isinstance(jurisdiction, dict) or not jurisdiction.get(required):
                raise EvidenceRegistryError(f"{identifier} missing jurisdiction.{required}")
        if entry.get("global_winner") is not None:
            raise EvidenceRegistryError(f"{identifier} illegally declares a global winner")
        if not isinstance(entry.get("evidence_boundary"), str) or not entry["evidence_boundary"]:
            raise EvidenceRegistryError(f"{identifier} missing evidence boundary")
    return {"status": "PASS", "entries": len(entries), "ids": sorted(seen)}


def load_and_validate(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return validate_registry(document)
