from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


class CustodyError(RuntimeError):
    """Raised when an immutable artifact or manifest fails validation."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_new(path: Path, value: Any) -> str:
    """Write canonical JSON once; never overwrite a frozen artifact."""
    if path.exists():
        raise CustodyError(f"immutable artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def manifest_entries(root: Path, excluded_names: Iterable[str] = ("MANIFEST_SHA256.txt",)) -> list[tuple[str, str]]:
    excluded = set(excluded_names)
    return [
        (sha256_file(path), path.relative_to(root).as_posix())
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in excluded
    ]


def write_manifest(root: Path) -> tuple[Path, str]:
    path = root / "MANIFEST_SHA256.txt"
    if path.exists():
        raise CustodyError(f"immutable manifest already exists: {path}")
    text = "".join(f"{digest}  {relative}\n" for digest, relative in manifest_entries(root))
    path.write_text(text, encoding="ascii", newline="\n")
    return path, sha256_file(path)


def verify_manifest(root: Path, manifest: Path | None = None) -> dict[str, Any]:
    manifest = manifest or root / "MANIFEST_SHA256.txt"
    failures: list[dict[str, str]] = []
    checked = 0
    for line_number, line in enumerate(manifest.read_text(encoding="ascii").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            failures.append({"line": str(line_number), "reason": "INVALID_MANIFEST_ROW"})
            continue
        expected, relative = parts
        candidate = (root / Path(relative)).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            failures.append({"path": relative, "reason": "PATH_ESCAPE"})
            continue
        if not candidate.is_file():
            failures.append({"path": relative, "reason": "MISSING"})
            continue
        checked += 1
        observed = sha256_file(candidate)
        if observed != expected:
            failures.append({"path": relative, "reason": "HASH_MISMATCH", "observed": observed})
    return {"status": "PASS" if not failures else "FAIL", "checked": checked, "failures": failures}
