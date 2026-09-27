from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> str:
    """Stable JSON serialization used for hashing and audit manifests."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pseudonymize_identifier(identifier: str, secret: bytes, namespace: str = "mc") -> str:
    """Return a purpose-separated HMAC token without persisting direct identifiers."""
    if not identifier or not secret:
        raise ValueError("identifier and secret are required")
    message = f"{namespace}:{identifier}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()
