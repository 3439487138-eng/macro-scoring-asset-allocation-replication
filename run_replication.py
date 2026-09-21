#!/usr/bin/env python3
"""Repository-independent command-line entrypoint for the strategy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dotenv import load_dotenv

from macro_allocation.config import (
    load_config,
    resolve_input_paths,
    runtime_configuration_errors,
    validate_structure,
)
from macro_allocation.data import load_sources
from macro_allocation.errors import ProjectError
from macro_allocation.pipeline import run_pipeline
from macro_allocation.validation import audit_source_tables, assert_no_nested_git


def _config_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or run the strict macro-scoring asset-allocation replication."
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="config/base.yml", help="repository-relative YAML config")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-config", parents=[common])
    validate.add_argument(
        "--structure-only",
        action="store_true",
        help="validate schema and safety rules without resolving known strategy blockers",
    )
    subparsers.add_parser("audit-inputs", parents=[common])
    subparsers.add_parser("run", parents=[common])
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    args = build_parser().parse_args(argv)
    try:
        assert_no_nested_git(PROJECT_ROOT)
        config_path = _config_path(args.config)
        config = load_config(config_path)
        if args.command == "validate-config":
            errors = validate_structure(config)
            if not args.structure_only:
                errors = runtime_configuration_errors(config)
            if errors:
                print("ERROR: " + "; ".join(errors), file=sys.stderr)
                return 2
            print("Configuration validation passed.")
            return 0

        if args.command == "audit-inputs":
            paths = resolve_input_paths(config, PROJECT_ROOT)
            sources = load_sources(paths)
            errors = audit_source_tables(sources, config)
            if errors:
                print("ERROR: " + "; ".join(errors), file=sys.stderr)
                return 2
            print("Input audit passed.")
            return 0

        published = run_pipeline(config, PROJECT_ROOT, config_path.relative_to(PROJECT_ROOT))
        print("Replication completed from current real inputs.")
        for path in published:
            print(path.relative_to(PROJECT_ROOT).as_posix())
        return 0
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("ERROR: interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # Last-resort redaction: never leak paths or credentials.
        print(f"ERROR: unexpected failure ({type(exc).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

