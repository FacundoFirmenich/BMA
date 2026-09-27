from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import yaml


def main(root: str) -> int:
    base = Path(root)
    errors: list[str] = []

    for path in sorted((base / "schemas").glob("*.schema.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator.check_schema(schema)
        except Exception as exc:
            errors.append(f"schema {path.name}: {exc}")

    for folder in ("constitution", "config", "experiments"):
        for path in sorted((base / folder).glob("*.yaml")):
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"yaml {path.relative_to(base)}: {exc}")

    if errors:
        print("FAIL")
        for error in errors:
            print(" -", error)
        return 1
    print("PASS repository contracts parse and validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
