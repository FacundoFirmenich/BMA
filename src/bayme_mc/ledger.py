from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .crypto import canonical_json, sha256_text
from .errors import IntegrityError


GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class LedgerRecord:
    index: int
    recorded_at: str
    kind: str
    payload: dict[str, Any]
    previous_hash: str
    record_hash: str


class AppendOnlyLedger:
    """Hash-chained JSONL ledger whose mutation is detectable from a trusted head."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def _iter_raw(self) -> Iterator[dict[str, Any]]:
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise IntegrityError(f"invalid JSON at ledger line {line_number}") from exc

    def records(self) -> list[LedgerRecord]:
        return [LedgerRecord(**item) for item in self._iter_raw()]

    def head_hash(self) -> str:
        records = self.records()
        return records[-1].record_hash if records else GENESIS_HASH

    def append(self, kind: str, payload: dict[str, Any]) -> LedgerRecord:
        existing = self.records()
        previous_hash = existing[-1].record_hash if existing else GENESIS_HASH
        index = len(existing)
        recorded_at = datetime.now(timezone.utc).isoformat()
        unsigned = {
            "index": index,
            "recorded_at": recorded_at,
            "kind": kind,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        record_hash = sha256_text(canonical_json(unsigned))
        record = {**unsigned, "record_hash": record_hash}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(record) + "\n")
        return LedgerRecord(**record)

    def verify(self, trusted_head: str | None = None) -> bool:
        previous = GENESIS_HASH
        last_hash = GENESIS_HASH
        for count, raw in enumerate(self._iter_raw(), start=1):
            expected_index = count - 1
            if raw.get("index") != expected_index:
                raise IntegrityError(f"non-contiguous index at {expected_index}")
            if raw.get("previous_hash") != previous:
                raise IntegrityError(f"broken previous hash at index {expected_index}")
            unsigned = {
                "index": raw["index"],
                "recorded_at": raw["recorded_at"],
                "kind": raw["kind"],
                "payload": raw["payload"],
                "previous_hash": raw["previous_hash"],
            }
            expected_hash = sha256_text(canonical_json(unsigned))
            if raw.get("record_hash") != expected_hash:
                raise IntegrityError(f"invalid record hash at index {expected_index}")
            previous = expected_hash
            last_hash = expected_hash
        if trusted_head is not None and last_hash != trusted_head:
            raise IntegrityError("ledger head does not match trusted head")
        return True
