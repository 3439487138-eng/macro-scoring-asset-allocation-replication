#!/usr/bin/env python3
"""Run the real-data practical adaptation or validate its configuration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dotenv import load_dotenv

from macro_allocation.config import load_config, require_valid_config
from macro_allocation.errors import ProjectError
from macro_allocation.production_pipeline import run_pipeline
from macro_allocation.validation import assert_no_nested_git


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the real-data macro-scoring asset-allocation practical adaptation."
    )
    parser.add_argument("--config", default="config/base.yml", help="repository-relative YAML config")
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="validate configuration only; do not download data or run the backtest",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    args = build_parser().parse_args(argv)
    try:
        assert_no_nested_git(PROJECT_ROOT)
        config_path = Path(args.config)
        if config_path.is_absolute() or ".." in config_path.parts:
            raise ProjectError("configuration path must be repository-relative")
        resolved = (PROJECT_ROOT / config_path).resolve()
        config = load_config(resolved)
        require_valid_config(config)
        if args.validate_config:
            print("Configuration validation passed.")
            return 0
        published = run_pipeline(config, PROJECT_ROOT, config_path)
        print("Practical-adaptation backtest completed from current real provider observations.")
        for path in published:
            print(path.relative_to(PROJECT_ROOT).as_posix())
        return 0
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("ERROR: interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERROR: unexpected failure ({type(exc).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
