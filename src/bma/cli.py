from __future__ import annotations

import argparse
import json
from pathlib import Path

from .custody import verify_manifest
from .evidence import load_and_validate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bma", description="Bayesian Markets App")
    commands = parser.add_subparsers(dest="command", required=True)

    evidence = commands.add_parser("evidence", help="validate an evidence registry")
    evidence.add_argument("action", choices=["validate"])
    evidence.add_argument("path", type=Path)

    custody = commands.add_parser("custody", help="verify an artifact manifest")
    custody.add_argument("action", choices=["verify"])
    custody.add_argument("root", type=Path)

    flor = commands.add_parser("flor-replay", help="run corrected Mercabarna Flor retrospective replay")
    flor.add_argument("--source-v01", type=Path, required=True)
    flor.add_argument("--source-v02", type=Path, required=True)
    flor.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "evidence":
        result = load_and_validate(args.path)
    elif args.command == "custody":
        result = verify_manifest(args.root)
    else:
        from .experiments.mercabarna_flor_v0_4_1 import run

        result = run([args.source_v01, args.source_v02], args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") in {"PASS", "EXECUTED_RETROSPECTIVE_DEVELOPMENT_REPLAY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
